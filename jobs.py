"""
Background jobs for discovery scanning.
"""
import logging
import traceback
from datetime import timedelta

from django.utils import timezone

from netbox.jobs import JobRunner

from .choices import ScanJobStatusChoices
from .models import DiscoveryResult, DiscoverySource, ScanJob
from .reconciliation import reconcile
from .scanner import scan_source

logger = logging.getLogger('nb_udm_plugin')


class DiscoveryScanJob(JobRunner):
    """Execute a discovery scan for a single UniFi source."""

    class Meta:
        name = 'Discovery Scan'

    def run(self, *args, **kwargs):
        source = self.job.object
        if not isinstance(source, DiscoverySource):
            self.log_failure(f'Expected DiscoverySource, got {type(source)}')
            return

        scan_job = ScanJob.objects.create(
            source=source,
            status=ScanJobStatusChoices.STATUS_RUNNING,
            started_at=timezone.now(),
        )

        try:
            self.log_info(f'Starting scan for source: {source.name}')

            # Run the scanner
            discovered = scan_source(source)
            scan_job.discovered_count = len(discovered)
            self.log_info(f'Discovered {len(discovered)} objects')

            # Reconcile against NetBox
            self.log_info('Running reconciliation...')
            results = reconcile(source, scan_job, discovered)

            # Bulk create results
            DiscoveryResult.objects.bulk_create(results, batch_size=100)

            # Update stats
            scan_job.created_count = sum(
                1 for r in results if r.action == 'create'
            )
            scan_job.updated_count = sum(
                1 for r in results if r.action == 'update'
            )
            scan_job.status = ScanJobStatusChoices.STATUS_COMPLETED
            scan_job.completed_at = timezone.now()
            scan_job.save()

            source.last_scan = timezone.now()
            source.last_scan_success = True
            source.save()

            self.log_success(
                f'Scan complete: {scan_job.discovered_count} discovered, '
                f'{scan_job.created_count} to create, '
                f'{scan_job.updated_count} to update'
            )

        except Exception as e:
            self.log_failure(f'Scan failed: {e}')
            scan_job.status = ScanJobStatusChoices.STATUS_FAILED
            scan_job.error_count += 1
            scan_job.log = traceback.format_exc()
            scan_job.completed_at = timezone.now()
            scan_job.save()
            source.last_scan = timezone.now()
            source.last_scan_success = False
            source.save()


class StaleJobReaper(JobRunner):
    """Mark scan jobs that have been running too long as failed."""

    class Meta:
        name = 'Stale Job Reaper'

    MAX_RUNTIME_MINUTES = 30

    def run(self, *args, **kwargs):
        cutoff = timezone.now() - timedelta(minutes=self.MAX_RUNTIME_MINUTES)
        stale_jobs = ScanJob.objects.filter(
            status=ScanJobStatusChoices.STATUS_RUNNING,
            started_at__lt=cutoff,
        )
        count = stale_jobs.count()
        if count:
            stale_jobs.update(
                status=ScanJobStatusChoices.STATUS_FAILED,
                completed_at=timezone.now(),
            )
            self.log_warning(f'Marked {count} stale scan job(s) as failed (>{self.MAX_RUNTIME_MINUTES}min)')
        else:
            self.log_info('No stale jobs found')
