from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from netbox.api.viewsets import NetBoxModelViewSet

from ..models import DiscoveryMapping, DiscoveryResult, DiscoverySource, ScanJob
from ..filtersets import (
    DiscoveryMappingFilterSet,
    DiscoveryResultFilterSet,
    DiscoverySourceFilterSet,
    ScanJobFilterSet,
)
from .serializers import (
    DiscoveryMappingSerializer,
    DiscoveryResultSerializer,
    DiscoverySourceSerializer,
    ScanJobSerializer,
)


class DiscoverySourceViewSet(NetBoxModelViewSet):
    queryset = DiscoverySource.objects.all()
    serializer_class = DiscoverySourceSerializer
    filterset_class = DiscoverySourceFilterSet

    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        source = self.get_object()
        from ..unifi_client import UnifiClient
        try:
            config = source.config
            client = UnifiClient(
                base_url=f"https://{config.get('host', '')}:{config.get('port', 443)}",
                api_mode=config.get('api_mode', 'token'),
                site=config.get('site', 'default'),
                verify_ssl=config.get('verify_ssl', False),
                token=source.token,
            )
            client.connect()
            site_count = len(client.sites)
            client.disconnect()
            return Response({'success': True, 'message': f'Connected. Found {site_count} site(s).'})
        except Exception as e:
            return Response({'success': False, 'message': str(e)})

    @action(detail=True, methods=['post'])
    def scan(self, request, pk=None):
        source = self.get_object()
        from ..jobs import DiscoveryScanJob
        DiscoveryScanJob.enqueue(instance=source, user=request.user)
        return Response({'status': 'queued'}, status=status.HTTP_202_ACCEPTED)


class ScanJobViewSet(NetBoxModelViewSet):
    queryset = ScanJob.objects.all()
    serializer_class = ScanJobSerializer
    filterset_class = ScanJobFilterSet


class DiscoveryResultViewSet(NetBoxModelViewSet):
    queryset = DiscoveryResult.objects.all()
    serializer_class = DiscoveryResultSerializer
    filterset_class = DiscoveryResultFilterSet

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        result = self.get_object()
        from ..reconciliation import apply_result
        from django.utils import timezone
        obj = apply_result(result)
        result.status = 'approved'
        result.reviewed_by = request.user
        result.reviewed_at = timezone.now()
        result.save()
        return Response({'status': 'approved', 'object': str(obj)})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        result = self.get_object()
        from django.utils import timezone
        result.status = 'rejected'
        result.reviewed_by = request.user
        result.reviewed_at = timezone.now()
        result.save()
        return Response({'status': 'rejected'})


class DiscoveryMappingViewSet(NetBoxModelViewSet):
    queryset = DiscoveryMapping.objects.all()
    serializer_class = DiscoveryMappingSerializer
    filterset_class = DiscoveryMappingFilterSet
