"""
UniFi scanner — discovers devices, clients, and VLANs from a UniFi controller
and produces normalized DiscoveredObject records for reconciliation.

Field mappings ported from ~/unifi2netbox/main.py.
"""
import logging
from dataclasses import dataclass, field

from .unifi_client import UnifiClient

logger = logging.getLogger('nb_udm_plugin.scanner')


@dataclass
class DiscoveredObject:
    """Normalized discovery output for reconciliation."""
    object_type: str        # 'device', 'ip_address', 'vlan'
    identity_key: str       # Unique within source (serial, MAC, vid)
    data: dict              # Normalized fields for NetBox
    raw_data: dict = field(default_factory=dict)


def determine_device_role(device, config):
    """Determine NetBox device role based on device model/type."""
    roles = config.get('roles', {})
    model = (device.get('model') or '').upper()
    device_type = (device.get('type') or '').lower()
    is_ap = device.get('is_access_point', False) or device.get('type') == 'uap'

    if is_ap or 'UAP' in model or 'U6' in model or 'U7' in model:
        return roles.get('wireless', 'Wireless AP')
    elif 'UDM' in model or 'USG' in model or 'UXG' in model or 'gateway' in device_type:
        return roles.get('router', 'Router')
    else:
        return roles.get('lan', 'Network Switch')


def scan_source(source):
    """
    Run a full discovery scan against a DiscoverySource.

    Returns a list of DiscoveredObject records.
    """
    config = source.config
    discovered = []

    client = UnifiClient(
        base_url=f"https://{config.get('host', '')}:{config.get('port', 443)}",
        api_mode=config.get('api_mode', 'token'),
        site=config.get('site', 'default'),
        verify_ssl=config.get('verify_ssl', False),
        token=source.token,
    )
    client.connect()

    site_mappings = config.get('site_mappings', {})
    manufacturer = config.get('manufacturer', 'Ubiquiti')

    for unifi_site_name in client.sites:
        netbox_site_name = site_mappings.get(unifi_site_name, unifi_site_name)
        logger.info(f'Scanning site: {unifi_site_name} -> {netbox_site_name}')

        if source.sync_devices:
            devices = client.get_devices(unifi_site_name)
            for device in devices:
                obj = _map_device(device, config, manufacturer, netbox_site_name)
                if obj:
                    discovered.append(obj)

        if source.sync_vlans:
            networks = client.get_networks(unifi_site_name)
            for network in networks:
                obj = _map_vlan(network, netbox_site_name)
                if obj:
                    discovered.append(obj)

        if source.sync_clients:
            clients = client.get_clients(unifi_site_name)
            for cli in clients:
                obj = _map_client(cli, config)
                if obj:
                    discovered.append(obj)

    client.disconnect()
    return discovered


def _map_device(device, config, manufacturer, site_name):
    """Map a UniFi device to a DiscoveredObject."""
    # Serial: prefer actual serial, fallback to MAC
    serial = (
        device.get('serial')
        or (device.get('mac') or '').replace(':', '').upper()
        or (device.get('macAddress') or '').replace(':', '').upper()
    )
    if not serial:
        return None

    name = device.get('name') or device.get('hostname') or f'UniFi-{serial[-6:]}'
    model = device.get('model', 'Unknown')
    mac = device.get('mac') or device.get('macAddress', '')
    ip = device.get('ip') or device.get('ipAddress', '')
    role_name = determine_device_role(device, config)

    return DiscoveredObject(
        object_type='device',
        identity_key=serial,
        data={
            'name': name,
            'serial': serial,
            'model': model,
            'manufacturer': manufacturer,
            'role': role_name,
            'mac': mac,
            'ip': ip,
            'site_name': site_name,
        },
        raw_data=device,
    )


def _map_vlan(network, site_name):
    """Map a UniFi network to a VLAN DiscoveredObject."""
    vlan_id = network.get('vlanId')
    name = network.get('name', f'VLAN-{vlan_id}')

    if not vlan_id:
        return None

    return DiscoveredObject(
        object_type='vlan',
        identity_key=f'vlan:{vlan_id}',
        data={
            'vid': vlan_id,
            'name': name,
            'site_name': site_name,
        },
        raw_data=network,
    )


def _map_client(client, config):
    """Map a UniFi client to an IP address DiscoveredObject."""
    ip = client.get('ip') or client.get('ipAddress')
    mac = client.get('mac') or client.get('macAddress', '')
    name = client.get('name') or client.get('hostname') or f"Client-{mac[-5:].replace(':', '')}"
    client_type = client.get('type', 'unknown')
    hostname = client.get('hostname', '')

    if not ip:
        return None

    prefix_len = config.get('client_prefix_length', 24)
    desc_format = config.get(
        'client_description_format',
        '{hostname} [{mac}] ({type})',
    )
    description = desc_format.format(
        hostname=name,
        mac=mac,
        type=client_type,
    )

    return DiscoveredObject(
        object_type='ip_address',
        identity_key=mac or ip,
        data={
            'ip': ip,
            'prefix_length': prefix_len,
            'description': description,
            'dns_name': hostname.lower().replace(' ', '-') if hostname else '',
            'mac': mac,
            'site_name': '',
        },
        raw_data=client,
    )
