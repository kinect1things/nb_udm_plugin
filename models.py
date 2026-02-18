from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse

from netbox.models import NetBoxModel
from netbox.models.features import JobsMixin

from .choices import (
    DiscoveredTypeChoices,
    ResultActionChoices,
    ResultStatusChoices,
    ScanJobStatusChoices,
    SourceStatusChoices,
)


class DiscoverySource(JobsMixin, NetBoxModel):
    """A configured UniFi controller connection."""

    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=200, blank=True)
    status = models.CharField(
        max_length=30,
        choices=SourceStatusChoices,
        default=SourceStatusChoices.STATUS_ACTIVE,
    )
    config = models.JSONField(
        default=dict,
        help_text='Connection config: host, port, api_mode, site, site_mappings, roles, etc.',
    )
    token = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text='API token for this source. Falls back to NB_UDM_UNIFI_TOKEN env var if blank.',
    )
    site = models.ForeignKey(
        to='dcim.Site',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text='Default NetBox site for discovered objects.',
    )
    scan_interval = models.PositiveIntegerField(
        default=0,
        help_text='Auto-scan interval in minutes. 0 = manual only.',
    )
    last_scan = models.DateTimeField(blank=True, null=True)
    last_scan_success = models.BooleanField(default=True)

    sync_devices = models.BooleanField(default=True)
    sync_clients = models.BooleanField(default=True)
    sync_vlans = models.BooleanField(default=True)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('plugins:nb_udm_plugin:discoverysource', args=[self.pk])


class ScanJob(NetBoxModel):
    """Record of a single scan execution."""

    source = models.ForeignKey(
        to='DiscoverySource',
        on_delete=models.CASCADE,
        related_name='scan_jobs',
    )
    status = models.CharField(
        max_length=30,
        choices=ScanJobStatusChoices,
        default=ScanJobStatusChoices.STATUS_PENDING,
    )
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    dry_run = models.BooleanField(default=False)
    discovered_count = models.PositiveIntegerField(default=0)
    created_count = models.PositiveIntegerField(default=0)
    updated_count = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)
    log = models.TextField(blank=True, default='')

    class Meta:
        ordering = ('-created',)

    def __str__(self):
        return f'Scan #{self.pk} ({self.source.name})'

    def get_absolute_url(self):
        return reverse('plugins:nb_udm_plugin:scanjob', args=[self.pk])

    @property
    def duration(self):
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None


class DiscoveryResult(NetBoxModel):
    """A single discovered object staged for review."""

    scan_job = models.ForeignKey(
        to='ScanJob',
        on_delete=models.CASCADE,
        related_name='results',
    )
    source = models.ForeignKey(
        to='DiscoverySource',
        on_delete=models.CASCADE,
        related_name='results',
    )
    discovered_type = models.CharField(
        max_length=50,
        choices=DiscoveredTypeChoices,
    )
    discovered_data = models.JSONField(default=dict)
    proposed_data = models.JSONField(default=dict)

    matched_object_type = models.ForeignKey(
        to=ContentType,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='+',
    )
    matched_object_id = models.PositiveBigIntegerField(blank=True, null=True)
    matched_object = GenericForeignKey('matched_object_type', 'matched_object_id')

    diff = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=30,
        choices=ResultStatusChoices,
        default=ResultStatusChoices.STATUS_PENDING,
    )
    action = models.CharField(
        max_length=30,
        choices=ResultActionChoices,
        default=ResultActionChoices.ACTION_CREATE,
    )
    identity_key = models.CharField(max_length=255, db_index=True)

    reviewed_by = models.ForeignKey(
        to='users.User',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='+',
    )
    reviewed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ('-created',)
        indexes = [
            models.Index(fields=['source', 'identity_key']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f'{self.get_discovered_type_display()}: {self.identity_key}'

    def get_absolute_url(self):
        return reverse('plugins:nb_udm_plugin:discoveryresult', args=[self.pk])


class DiscoveryMapping(NetBoxModel):
    """Persistent link: source identity <-> NetBox object."""

    source = models.ForeignKey(
        to='DiscoverySource',
        on_delete=models.CASCADE,
        related_name='mappings',
    )
    identity_key = models.CharField(max_length=255, db_index=True)

    netbox_object_type = models.ForeignKey(
        to=ContentType,
        on_delete=models.CASCADE,
        related_name='+',
    )
    netbox_object_id = models.PositiveBigIntegerField()
    netbox_object = GenericForeignKey('netbox_object_type', 'netbox_object_id')

    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)
    is_orphan = models.BooleanField(default=False)

    class Meta:
        ordering = ('source', 'identity_key')
        unique_together = ('source', 'identity_key')

    def __str__(self):
        return f'{self.source.name}: {self.identity_key}'

    def get_absolute_url(self):
        return reverse('plugins:nb_udm_plugin:discoverymapping', args=[self.pk])
