from rest_framework import serializers

from netbox.api.serializers import NetBoxModelSerializer

from ..models import DiscoveryMapping, DiscoveryResult, DiscoverySource, ScanJob


class DiscoverySourceSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='plugins-api:nb_udm_plugin-api:discoverysource-detail',
    )
    token = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = DiscoverySource
        fields = (
            'id', 'url', 'display', 'name', 'description', 'status',
            'config', 'token', 'site', 'scan_interval', 'last_scan',
            'last_scan_success', 'sync_devices', 'sync_clients',
            'sync_vlans', 'tags', 'created', 'last_updated',
        )
        brief_fields = ('id', 'url', 'display', 'name', 'status')


class ScanJobSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='plugins-api:nb_udm_plugin-api:scanjob-detail',
    )

    class Meta:
        model = ScanJob
        fields = (
            'id', 'url', 'display', 'source', 'status',
            'started_at', 'completed_at', 'dry_run',
            'discovered_count', 'created_count', 'updated_count',
            'error_count', 'log', 'tags', 'created', 'last_updated',
        )
        brief_fields = ('id', 'url', 'display', 'source', 'status')


class DiscoveryResultSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='plugins-api:nb_udm_plugin-api:discoveryresult-detail',
    )

    class Meta:
        model = DiscoveryResult
        fields = (
            'id', 'url', 'display', 'scan_job', 'source',
            'discovered_type', 'discovered_data', 'proposed_data',
            'diff', 'status', 'action', 'identity_key',
            'reviewed_by', 'reviewed_at',
            'tags', 'created', 'last_updated',
        )
        brief_fields = ('id', 'url', 'display', 'identity_key', 'status', 'action')


class DiscoveryMappingSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='plugins-api:nb_udm_plugin-api:discoverymapping-detail',
    )

    class Meta:
        model = DiscoveryMapping
        fields = (
            'id', 'url', 'display', 'source', 'identity_key',
            'first_seen', 'last_seen', 'is_orphan',
            'tags', 'created', 'last_updated',
        )
        brief_fields = ('id', 'url', 'display', 'identity_key', 'is_orphan')
