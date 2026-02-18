from django import forms

from dcim.models import Site
from netbox.forms import NetBoxModelForm, NetBoxModelFilterSetForm
from utilities.forms.fields import DynamicModelChoiceField
from utilities.forms.utils import add_blank_choice

from .choices import (
    DiscoveredTypeChoices,
    ResultActionChoices,
    ResultStatusChoices,
    ScanJobStatusChoices,
    SourceStatusChoices,
)
from .models import DiscoveryMapping, DiscoveryResult, DiscoverySource, ScanJob


# --- Model Forms ---

class DiscoverySourceForm(NetBoxModelForm):
    site = DynamicModelChoiceField(
        queryset=Site.objects.all(),
        required=False,
    )

    token = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'placeholder': 'Leave blank to use NB_UDM_UNIFI_TOKEN env var'}),
        help_text='API token for this source. Stored in the database.',
    )

    class Meta:
        model = DiscoverySource
        fields = (
            'name', 'description', 'status', 'config', 'token', 'site',
            'scan_interval', 'sync_devices', 'sync_clients', 'sync_vlans',
            'tags',
        )
        widgets = {
            'config': forms.Textarea(attrs={'class': 'font-monospace', 'rows': 12}),
        }


# --- Filter Forms ---

class DiscoverySourceFilterForm(NetBoxModelFilterSetForm):
    model = DiscoverySource
    status = forms.ChoiceField(
        choices=add_blank_choice(SourceStatusChoices),
        required=False,
    )
    site_id = DynamicModelChoiceField(
        queryset=Site.objects.all(),
        required=False,
        label='Site',
    )


class ScanJobFilterForm(NetBoxModelFilterSetForm):
    model = ScanJob
    status = forms.ChoiceField(
        choices=add_blank_choice(ScanJobStatusChoices),
        required=False,
    )
    source_id = DynamicModelChoiceField(
        queryset=DiscoverySource.objects.all(),
        required=False,
        label='Source',
    )


class DiscoveryResultFilterForm(NetBoxModelFilterSetForm):
    model = DiscoveryResult
    status = forms.ChoiceField(
        choices=add_blank_choice(ResultStatusChoices),
        required=False,
    )
    action = forms.ChoiceField(
        choices=add_blank_choice(ResultActionChoices),
        required=False,
    )
    discovered_type = forms.ChoiceField(
        choices=add_blank_choice(DiscoveredTypeChoices),
        required=False,
    )
    source_id = DynamicModelChoiceField(
        queryset=DiscoverySource.objects.all(),
        required=False,
        label='Source',
    )


class DiscoveryMappingFilterForm(NetBoxModelFilterSetForm):
    model = DiscoveryMapping
    is_orphan = forms.NullBooleanField(required=False, label='Orphan')
    source_id = DynamicModelChoiceField(
        queryset=DiscoverySource.objects.all(),
        required=False,
        label='Source',
    )
