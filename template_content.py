"""
Template extensions — inject discovery info into NetBox Device detail views.
"""
from netbox.plugins import PluginTemplateExtension

from .models import DiscoveryMapping


class DeviceDiscoveryInfo(PluginTemplateExtension):
    model = 'dcim.device'

    def right_page(self):
        obj = self.context['object']
        mappings = DiscoveryMapping.objects.filter(
            netbox_object_type__model='device',
            netbox_object_id=obj.pk,
        ).select_related('source')

        if not mappings.exists():
            return ''

        rows = []
        for m in mappings:
            orphan = '<span class="badge bg-danger">Orphan</span>' if m.is_orphan else ''
            rows.append(
                f'<tr>'
                f'<td><a href="{m.source.get_absolute_url()}">{m.source.name}</a></td>'
                f'<td>{m.identity_key}</td>'
                f'<td>{m.last_seen.strftime("%Y-%m-%d %H:%M")}</td>'
                f'<td>{orphan}</td>'
                f'</tr>'
            )

        return (
            '<div class="card">'
            '<h5 class="card-header">UniFi Discovery</h5>'
            '<div class="card-body"><table class="table table-sm">'
            '<thead><tr><th>Source</th><th>Identity</th><th>Last Seen</th><th></th></tr></thead>'
            '<tbody>' + ''.join(rows) + '</tbody>'
            '</table></div></div>'
        )


template_extensions = [DeviceDiscoveryInfo]
