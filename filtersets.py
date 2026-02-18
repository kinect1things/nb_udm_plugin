import django_filters

from netbox.filtersets import NetBoxModelFilterSet

from .choices import (
    DiscoveredTypeChoices,
    ResultActionChoices,
    ResultStatusChoices,
    ScanJobStatusChoices,
    SourceStatusChoices,
)
from .models import DiscoveryMapping, DiscoveryResult, DiscoverySource, ScanJob


class DiscoverySourceFilterSet(NetBoxModelFilterSet):
    status = django_filters.ChoiceFilter(choices=SourceStatusChoices)

    class Meta:
        model = DiscoverySource
        fields = ('id', 'name', 'status', 'site_id')


class ScanJobFilterSet(NetBoxModelFilterSet):
    status = django_filters.ChoiceFilter(choices=ScanJobStatusChoices)

    class Meta:
        model = ScanJob
        fields = ('id', 'source_id', 'status', 'dry_run')


class DiscoveryResultFilterSet(NetBoxModelFilterSet):
    status = django_filters.ChoiceFilter(choices=ResultStatusChoices)
    action = django_filters.ChoiceFilter(choices=ResultActionChoices)
    discovered_type = django_filters.ChoiceFilter(choices=DiscoveredTypeChoices)

    class Meta:
        model = DiscoveryResult
        fields = ('id', 'source_id', 'scan_job_id', 'status', 'action', 'discovered_type')


class DiscoveryMappingFilterSet(NetBoxModelFilterSet):
    is_orphan = django_filters.BooleanFilter()

    class Meta:
        model = DiscoveryMapping
        fields = ('id', 'source_id', 'is_orphan')
