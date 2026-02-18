"""
Reconciliation engine — matches discovered objects against NetBox,
computes diffs, and applies approved results.
"""
import logging

from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.utils.text import slugify

from dcim.models import Device, DeviceRole, DeviceType, Interface, Manufacturer, Site
from ipam.models import IPAddress, VLAN, VLANGroup

from .choices import ResultActionChoices, ResultStatusChoices
from .models import DiscoveryMapping, DiscoveryResult

logger = logging.getLogger('nb_udm_plugin.reconciliation')


def reconcile(source, scan_job, discovered_objects):
    """
    Compare discovered objects against NetBox and create DiscoveryResult records.

    Returns list of DiscoveryResult instances (not yet saved).
    """
    results = []
    seen_keys = set()

    for obj in discovered_objects:
        result = _reconcile_one(source, scan_job, obj)
        if result:
            results.append(result)
        seen_keys.add(obj.identity_key)

    # Mark orphans
    DiscoveryMapping.objects.filter(
        source=source,
    ).exclude(
        identity_key__in=seen_keys,
    ).update(is_orphan=True)

    # Clear orphan flag for seen keys
    DiscoveryMapping.objects.filter(
        source=source,
        identity_key__in=seen_keys,
    ).update(is_orphan=False, last_seen=timezone.now())

    return results


def _reconcile_one(source, scan_job, discovered):
    """Reconcile a single discovered object."""
    existing = _find_match(source, discovered)

    if existing:
        diff = _compute_diff(existing, discovered)
        if not diff:
            # No changes — skip
            return None
        return DiscoveryResult(
            scan_job=scan_job,
            source=source,
            discovered_type=discovered.object_type,
            discovered_data=discovered.raw_data,
            proposed_data=discovered.data,
            matched_object_type=ContentType.objects.get_for_model(existing),
            matched_object_id=existing.pk,
            diff=diff,
            status=ResultStatusChoices.STATUS_PENDING,
            action=ResultActionChoices.ACTION_UPDATE,
            identity_key=discovered.identity_key,
        )
    else:
        return DiscoveryResult(
            scan_job=scan_job,
            source=source,
            discovered_type=discovered.object_type,
            discovered_data=discovered.raw_data,
            proposed_data=discovered.data,
            diff={},
            status=ResultStatusChoices.STATUS_PENDING,
            action=ResultActionChoices.ACTION_CREATE,
            identity_key=discovered.identity_key,
        )


def _find_match(source, discovered):
    """
    Try to find an existing NetBox object matching the discovered data.

    Priority:
    1. Existing DiscoveryMapping (we created this before)
    2. Serial number match (devices)
    3. MAC address match (devices)
    4. Name + site match (devices)
    5. VID + site match (VLANs)
    6. IP address match (IP addresses)
    """
    # 1. Existing mapping
    mapping = DiscoveryMapping.objects.filter(
        source=source,
        identity_key=discovered.identity_key,
    ).first()
    if mapping:
        try:
            return mapping.netbox_object
        except Exception:
            pass

    data = discovered.data

    if discovered.object_type == 'device':
        # 2. Serial match
        serial = data.get('serial')
        if serial:
            device = Device.objects.filter(serial=serial).first()
            if device:
                return device

        # 3. MAC match on interface
        mac = data.get('mac')
        if mac:
            iface = Interface.objects.filter(mac_address=mac).first()
            if iface and iface.device:
                return iface.device

        # 4. Name + site
        name = data.get('name')
        site_name = data.get('site_name')
        if name:
            qs = Device.objects.filter(name=name)
            if site_name:
                qs = qs.filter(site__name=site_name)
            device = qs.first()
            if device:
                return device

    elif discovered.object_type == 'vlan':
        vid = data.get('vid')
        site_name = data.get('site_name')
        if vid:
            qs = VLAN.objects.filter(vid=vid)
            if site_name:
                qs = qs.filter(site__name=site_name)
            vlan = qs.first()
            if vlan:
                return vlan

    elif discovered.object_type == 'ip_address':
        ip = data.get('ip')
        prefix_len = data.get('prefix_length', 24)
        if ip:
            ip_obj = IPAddress.objects.filter(
                address=f'{ip}/{prefix_len}',
            ).first()
            if ip_obj:
                return ip_obj

    return None


def _compute_diff(existing, discovered):
    """Compute field-level diff between existing NetBox object and discovered data."""
    diff = {}
    data = discovered.data

    if discovered.object_type == 'device':
        if data.get('name') and existing.name != data['name']:
            diff['name'] = {'current': existing.name, 'proposed': data['name']}
        if data.get('ip'):
            current_ip = str(existing.primary_ip4).split('/')[0] if existing.primary_ip4 else ''
            if current_ip != data['ip']:
                diff['primary_ip4'] = {'current': current_ip, 'proposed': data['ip']}

    elif discovered.object_type == 'vlan':
        if data.get('name') and existing.name != data['name']:
            diff['name'] = {'current': existing.name, 'proposed': data['name']}

    elif discovered.object_type == 'ip_address':
        if data.get('description') and existing.description != data['description']:
            diff['description'] = {'current': existing.description, 'proposed': data['description']}
        dns = data.get('dns_name', '')
        if dns and existing.dns_name != dns:
            diff['dns_name'] = {'current': existing.dns_name, 'proposed': dns}

    return diff


def apply_result(result):
    """
    Apply an approved DiscoveryResult to NetBox.

    Creates or updates the appropriate NetBox object and establishes
    a DiscoveryMapping for future reconciliation.

    Returns the created/updated NetBox object.
    """
    data = result.proposed_data

    if result.action == ResultActionChoices.ACTION_CREATE:
        obj = _create_object(result.discovered_type, data, result.source)
    elif result.action == ResultActionChoices.ACTION_UPDATE:
        obj = _update_object(result.matched_object, result.discovered_type, data, result.diff)
    else:
        return None

    if obj is None:
        return None

    # Create or update mapping
    ct = ContentType.objects.get_for_model(obj)
    DiscoveryMapping.objects.update_or_create(
        source=result.source,
        identity_key=result.identity_key,
        defaults={
            'netbox_object_type': ct,
            'netbox_object_id': obj.pk,
            'is_orphan': False,
        },
    )

    # Tag the object
    from extras.models import Tag
    tag_name = result.source.config.get('discovery_tag', 'udm-discovered')
    tag, _ = Tag.objects.get_or_create(
        slug=slugify(tag_name),
        defaults={'name': tag_name},
    )
    obj.tags.add(tag)

    return obj


def _create_object(object_type, data, source):
    """Create a new NetBox object from discovered data."""
    if object_type == 'device':
        return _create_device(data, source)
    elif object_type == 'vlan':
        return _create_vlan(data, source)
    elif object_type == 'ip_address':
        return _create_ip_address(data, source)
    return None


def _create_device(data, source):
    """Create a Device with its management interface and IP."""
    site = _resolve_site(data.get('site_name'), source)
    manufacturer = _ensure_manufacturer(data.get('manufacturer', 'Ubiquiti'))
    device_type = _ensure_device_type(manufacturer, data.get('model', 'Unknown'))
    role = _ensure_device_role(data.get('role', 'Network Switch'))

    tenant = _resolve_tenant(source.config.get('tenant', ''))

    device_data = {
        'name': data['name'],
        'device_type': device_type,
        'role': role,
        'serial': data.get('serial', ''),
        'status': 'active',
    }
    if site:
        device_data['site'] = site
    if tenant:
        device_data['tenant'] = tenant

    device = Device(**device_data)
    device.save()
    logger.info(f'Created device: {device.name}')

    # Create mgmt interface and IP
    ip = data.get('ip')
    mac = data.get('mac')
    if ip:
        _assign_device_ip(device, ip, mac)

    return device


def _create_vlan(data, source):
    """Create a VLAN in NetBox."""
    site = _resolve_site(data.get('site_name'), source)
    vlan_group = None
    if site:
        pattern = source.config.get('vlan_group_pattern', '{site_slug}-vlans')
        group_slug = pattern.format(site_slug=site.slug)
        vlan_group, _ = VLANGroup.objects.get_or_create(
            slug=group_slug,
            defaults={
                'name': f'{site.name} VLANs',
                'scope_type': ContentType.objects.get_for_model(Site),
                'scope_id': site.id,
            },
        )

    tenant = _resolve_tenant(source.config.get('tenant', ''))

    vlan_data = {
        'vid': data['vid'],
        'name': data['name'],
        'status': 'active',
    }
    if site:
        vlan_data['site'] = site
    if vlan_group:
        vlan_data['group'] = vlan_group
    if tenant:
        vlan_data['tenant'] = tenant

    vlan = VLAN(**vlan_data)
    vlan.save()
    logger.info(f"Created VLAN: {data['name']} (VID {data['vid']})")
    return vlan


def _create_ip_address(data, source):
    """Create an IP address in NetBox."""
    prefix_len = data.get('prefix_length', 24)
    ip_addr = f"{data['ip']}/{prefix_len}"

    tenant = _resolve_tenant(source.config.get('tenant', ''))

    ip_data = {
        'address': ip_addr,
        'status': 'active',
        'description': data.get('description', ''),
        'dns_name': data.get('dns_name', ''),
    }
    if tenant:
        ip_data['tenant'] = tenant

    ip_obj = IPAddress(**ip_data)
    ip_obj.save()
    logger.info(f"Created IP: {ip_addr}")
    return ip_obj


def _update_object(existing, object_type, data, diff):
    """Update an existing NetBox object with changed fields."""
    if existing is None:
        return None

    if object_type == 'device':
        if 'name' in diff:
            existing.name = data['name']
        if 'primary_ip4' in diff and data.get('ip'):
            _assign_device_ip(existing, data['ip'], data.get('mac'))
        existing.save()

    elif object_type == 'vlan':
        if 'name' in diff:
            existing.name = data['name']
        existing.save()

    elif object_type == 'ip_address':
        if 'description' in diff:
            existing.description = data['description']
        if 'dns_name' in diff:
            existing.dns_name = data.get('dns_name', '')
        existing.save()

    logger.info(f'Updated {object_type}: {existing}')
    return existing


# --- Helper functions ---

def _resolve_site(site_name, source):
    """Resolve a site name to a NetBox Site object."""
    if site_name:
        site = Site.objects.filter(name=site_name).first()
        if site:
            return site
    if source.site:
        return source.site
    return None


def _resolve_tenant(tenant_name):
    """Resolve a tenant name to a NetBox Tenant object."""
    if not tenant_name:
        return None
    from tenancy.models import Tenant
    return Tenant.objects.filter(name=tenant_name).first()


def _ensure_manufacturer(name):
    """Get or create a Manufacturer by name."""
    slug = slugify(name)
    mfr, _ = Manufacturer.objects.get_or_create(
        slug=slug,
        defaults={'name': name},
    )
    return mfr


def _ensure_device_type(manufacturer, model):
    """Get or create a DeviceType."""
    device_type = DeviceType.objects.filter(
        manufacturer=manufacturer, model=model,
    ).first()
    if device_type:
        return device_type

    slug = slugify(f'{manufacturer.slug}-{model}')
    device_type, _ = DeviceType.objects.get_or_create(
        slug=slug,
        defaults={'manufacturer': manufacturer, 'model': model},
    )
    return device_type


def _ensure_device_role(name):
    """Get or create a DeviceRole by name."""
    slug = slugify(name)
    role, _ = DeviceRole.objects.get_or_create(
        slug=slug,
        defaults={'name': name, 'color': '9e9e9e'},
    )
    return role


def _assign_device_ip(device, ip, mac=None):
    """Create or find a management interface and assign an IP to a device."""
    interfaces = Interface.objects.filter(device=device, name='mgmt')
    if interfaces.exists():
        interface = interfaces.first()
    else:
        interface = Interface(
            device=device,
            name='mgmt',
            type='virtual',
        )
        if mac:
            interface.mac_address = mac
        interface.save()

    ip_with_prefix = f'{ip}/24'
    existing_ip = IPAddress.objects.filter(address=ip_with_prefix).first()

    if existing_ip:
        if existing_ip.assigned_object_id == interface.id:
            # Already assigned correctly
            if not device.primary_ip4 or device.primary_ip4.id != existing_ip.id:
                device.primary_ip4 = existing_ip
                device.save()
        else:
            logger.warning(f'IP {ip} assigned elsewhere, skipping for {device.name}')
    else:
        ct = ContentType.objects.get_for_model(Interface)
        new_ip = IPAddress(
            address=ip_with_prefix,
            assigned_object_type=ct,
            assigned_object_id=interface.id,
            status='active',
        )
        new_ip.save()
        device.primary_ip4 = new_ip
        device.save()
        logger.info(f'Assigned IP {ip} to {device.name}')
