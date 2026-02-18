import logging
import warnings

from netbox.plugins import PluginConfig

logger = logging.getLogger('nb_udm_plugin')


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
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', message='.*database during app initialization.*')
            self._cleanup_stale_jobs()
            self._schedule_reaper()

    @staticmethod
    def _cleanup_stale_jobs():
        """Mark any 'running' scan jobs as failed on startup."""
        from django.db import OperationalError, ProgrammingError
        try:
            from .models import ScanJob
            from django.utils import timezone
            stale = ScanJob.objects.filter(status='running').update(
                status='failed',
                completed_at=timezone.now(),
            )
            if stale:
                logger.warning('Marked %d stale scan job(s) as failed on startup', stale)
        except (OperationalError, ProgrammingError):
            pass  # Table doesn't exist yet (fresh install before migrations)

    @staticmethod
    def _schedule_reaper():
        """Schedule the stale job reaper to run every 15 minutes."""
        from django.db import OperationalError, ProgrammingError
        try:
            from .jobs import StaleJobReaper
            StaleJobReaper.enqueue_once(interval=15)
        except (OperationalError, ProgrammingError):
            pass  # Table doesn't exist yet


config = NbUdmPluginConfig
