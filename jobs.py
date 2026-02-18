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
            logger.error('Expected DiscoverySource, got %s', type(source))
            return

        scan_job = ScanJob.objects.create(
            source=source,
            status=ScanJobStatusChoices.STATUS_RUNNING,
            started_at=timezone.now(),
        )

        try:
            logger.info('Starting scan for source: %s', source.name)

            # Run the scanner
            discovered = scan_source(source)
            scan_job.discovered_count = len(discovered)
            logger.info('Discovered %d objects from %s', len(discovered), source.name)

            # Reconcile against NetBox
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

            logger.info(
                'Scan complete for %s: %d discovered, %d to create, %d to update',
                source.name, scan_job.discovered_count,
                scan_job.created_count, scan_job.updated_count,
            )

        except Exception as e:
            logger.error('Scan failed for %s: %s', source.name, e)
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
            logger.warning('Marked %d stale scan job(s) as failed (>%dmin)', count, self.MAX_RUNTIME_MINUTES)
        else:
            logger.debug('Stale job reaper: no stale jobs found')
