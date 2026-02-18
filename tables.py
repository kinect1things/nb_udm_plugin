import django_tables2 as tables

from netbox.tables import NetBoxTable, columns

from .models import DiscoveryMapping, DiscoveryResult, DiscoverySource, ScanJob


class DiscoverySourceTable(NetBoxTable):
    name = tables.Column(linkify=True)
    status = columns.ChoiceFieldColumn()
    site = tables.Column(linkify=True)
    scan_interval = tables.Column(verbose_name='Interval (min)')
    last_scan = tables.DateTimeColumn()
    last_scan_success = columns.BooleanColumn(verbose_name='Last OK')
    sync_devices = columns.BooleanColumn()
    sync_clients = columns.BooleanColumn()
    sync_vlans = columns.BooleanColumn()

    class Meta(NetBoxTable.Meta):
        model = DiscoverySource
        fields = (
            'pk', 'id', 'name', 'status', 'site', 'scan_interval',
            'last_scan', 'last_scan_success',
            'sync_devices', 'sync_clients', 'sync_vlans',
        )
        default_columns = (
            'name', 'status', 'site', 'scan_interval',
            'last_scan', 'last_scan_success',
        )


class ScanJobTable(NetBoxTable):
    source = tables.Column(linkify=True)
    status = columns.ChoiceFieldColumn()
    started_at = tables.DateTimeColumn()
    completed_at = tables.DateTimeColumn()
    dry_run = columns.BooleanColumn()
    discovered_count = tables.Column(verbose_name='Discovered')
    created_count = tables.Column(verbose_name='Created')
    updated_count = tables.Column(verbose_name='Updated')
    error_count = tables.Column(verbose_name='Errors')

    class Meta(NetBoxTable.Meta):
        model = ScanJob
        fields = (
            'pk', 'id', 'source', 'status', 'started_at', 'completed_at',
            'dry_run', 'discovered_count', 'created_count',
            'updated_count', 'error_count',
        )
        default_columns = (
            'pk', 'source', 'status', 'started_at',
            'discovered_count', 'created_count', 'updated_count', 'error_count',
        )
        actions = ()


class DiscoveryResultTable(NetBoxTable):
    identity_key = tables.Column(linkify=True)
    source = tables.Column(linkify=True)
    discovered_type = columns.ChoiceFieldColumn()
    action = columns.ChoiceFieldColumn()
    status = columns.ChoiceFieldColumn()
    scan_job = tables.Column(linkify=True, verbose_name='Scan')

    class Meta(NetBoxTable.Meta):
        model = DiscoveryResult
        fields = (
            'pk', 'id', 'identity_key', 'source', 'scan_job',
            'discovered_type', 'action', 'status',
        )
        default_columns = (
            'pk', 'identity_key', 'source', 'discovered_type', 'action', 'status',
        )
        actions = ()


class DiscoveryMappingTable(NetBoxTable):
    source = tables.Column(linkify=True)
    identity_key = tables.Column(linkify=True)
    first_seen = tables.DateTimeColumn()
    last_seen = tables.DateTimeColumn()
    is_orphan = columns.BooleanColumn()

    class Meta(NetBoxTable.Meta):
        model = DiscoveryMapping
        fields = (
            'pk', 'id', 'source', 'identity_key',
            'first_seen', 'last_seen', 'is_orphan',
        )
        default_columns = (
            'source', 'identity_key', 'last_seen', 'is_orphan',
        )
        actions = ()
