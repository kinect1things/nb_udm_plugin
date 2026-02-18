from netbox.plugins import PluginConfig


class NbUdmPluginConfig(PluginConfig):
    name = 'nb_udm_plugin'
    verbose_name = 'UniFi Discovery Manager'
    description = 'Discover and sync devices, VLANs, and clients from UniFi controllers'
    version = '0.1.0'
    author = 'Awen Labs'
    base_url = 'udm'
    min_version = '4.0.0'

    required_settings = []
    default_settings = {
        'auto_create_roles': True,
        'auto_create_manufacturers': True,
        'auto_create_device_types': True,
        'tag_discovered_objects': True,
        'orphan_grace_scans': 3,
        'default_site_slug': '',
    }

    queues = ['scanning']

    def ready(self):
        super().ready()
        from . import jobs  # noqa: F401


config = NbUdmPluginConfig
