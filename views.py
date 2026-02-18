from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from netbox.views import generic
from utilities.views import register_model_view

from . import filtersets, forms, models, tables


# --- Dashboard ---

class DashboardView(View):
    def get(self, request):
        return render(request, 'nb_udm_plugin/dashboard.html', {
            'source_count': models.DiscoverySource.objects.count(),
            'pending_count': models.DiscoveryResult.objects.filter(
                status='pending',
            ).count(),
            'recent_jobs': models.ScanJob.objects.order_by('-created')[:10],
            'orphan_count': models.DiscoveryMapping.objects.filter(
                is_orphan=True,
            ).count(),
            'sources': models.DiscoverySource.objects.all(),
        })


# --- DiscoverySource ---

@register_model_view(models.DiscoverySource)
class DiscoverySourceView(generic.ObjectView):
    queryset = models.DiscoverySource.objects.all()


@register_model_view(models.DiscoverySource, 'list', detail=False)
class DiscoverySourceListView(generic.ObjectListView):
    queryset = models.DiscoverySource.objects.all()
    table = tables.DiscoverySourceTable
    filterset = filtersets.DiscoverySourceFilterSet
    filterset_form = forms.DiscoverySourceFilterForm


@register_model_view(models.DiscoverySource, 'add', detail=False)
class DiscoverySourceAddView(generic.ObjectEditView):
    queryset = models.DiscoverySource.objects.all()
    form = forms.DiscoverySourceForm


@register_model_view(models.DiscoverySource, 'edit')
class DiscoverySourceEditView(generic.ObjectEditView):
    queryset = models.DiscoverySource.objects.all()
    form = forms.DiscoverySourceForm


@register_model_view(models.DiscoverySource, 'delete')
class DiscoverySourceDeleteView(generic.ObjectDeleteView):
    queryset = models.DiscoverySource.objects.all()


# --- Source Actions ---

class DiscoverySourceTestView(View):
    def post(self, request, pk):
        source = get_object_or_404(models.DiscoverySource, pk=pk)
        from .unifi_client import UnifiClient
        try:
            config = source.config
            client = UnifiClient(
                base_url=f"https://{config.get('host', '')}:{config.get('port', 443)}",
                api_mode=config.get('api_mode', 'token'),
                site=config.get('site', 'default'),
                verify_ssl=config.get('verify_ssl', False),
            )
            client.connect()
            site_count = len(client.sites)
            client.disconnect()
            messages.success(request, f'Connection to {source.name} successful. Found {site_count} site(s).')
        except Exception as e:
            messages.error(request, f'Connection to {source.name} failed: {e}')
        return redirect(source.get_absolute_url())


class DiscoverySourceScanView(View):
    def post(self, request, pk):
        source = get_object_or_404(models.DiscoverySource, pk=pk)
        dry_run = 'dry_run' in request.POST
        from .jobs import DiscoveryScanJob
        DiscoveryScanJob.enqueue(instance=source, user=request.user)
        messages.info(request, f'Scan queued for {source.name}.')
        return redirect(source.get_absolute_url())


# --- ScanJob ---

@register_model_view(models.ScanJob)
class ScanJobView(generic.ObjectView):
    queryset = models.ScanJob.objects.all()


@register_model_view(models.ScanJob, 'list', detail=False)
class ScanJobListView(generic.ObjectListView):
    queryset = models.ScanJob.objects.all()
    table = tables.ScanJobTable
    filterset = filtersets.ScanJobFilterSet
    filterset_form = forms.ScanJobFilterForm


# --- DiscoveryResult ---

@register_model_view(models.DiscoveryResult)
class DiscoveryResultView(generic.ObjectView):
    queryset = models.DiscoveryResult.objects.all()


@register_model_view(models.DiscoveryResult, 'list', detail=False)
class DiscoveryResultListView(generic.ObjectListView):
    queryset = models.DiscoveryResult.objects.all()
    table = tables.DiscoveryResultTable
    filterset = filtersets.DiscoveryResultFilterSet
    filterset_form = forms.DiscoveryResultFilterForm


class DiscoveryResultApproveView(View):
    def post(self, request, pk):
        result = get_object_or_404(models.DiscoveryResult, pk=pk)
        if result.status != 'pending':
            messages.warning(request, f'Result is already {result.get_status_display()}.')
            return redirect(result.get_absolute_url())
        from .reconciliation import apply_result
        try:
            obj = apply_result(result)
            result.status = 'approved'
            result.reviewed_by = request.user
            result.reviewed_at = timezone.now()
            result.save()
            messages.success(request, f'Approved: {obj}')
        except Exception as e:
            messages.error(request, f'Failed to apply: {e}')
        return redirect(result.get_absolute_url())


class DiscoveryResultRejectView(View):
    def post(self, request, pk):
        result = get_object_or_404(models.DiscoveryResult, pk=pk)
        result.status = 'rejected'
        result.reviewed_by = request.user
        result.reviewed_at = timezone.now()
        result.save()
        messages.info(request, f'Rejected: {result.identity_key}')
        return redirect(result.get_absolute_url())


class DiscoveryResultBulkApproveView(View):
    def post(self, request):
        pk_list = request.POST.getlist('pk')
        results = models.DiscoveryResult.objects.filter(pk__in=pk_list, status='pending')
        from .reconciliation import apply_result
        success = 0
        for result in results:
            try:
                apply_result(result)
                result.status = 'approved'
                result.reviewed_by = request.user
                result.reviewed_at = timezone.now()
                result.save()
                success += 1
            except Exception as e:
                messages.error(request, f'Failed to apply {result.identity_key}: {e}')
        messages.success(request, f'Approved {success} result(s).')
        return redirect('plugins:nb_udm_plugin:discoveryresult_list')


class DiscoveryResultBulkRejectView(View):
    def post(self, request):
        pk_list = request.POST.getlist('pk')
        count = models.DiscoveryResult.objects.filter(
            pk__in=pk_list, status='pending',
        ).update(
            status='rejected',
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
        )
        messages.info(request, f'Rejected {count} result(s).')
        return redirect('plugins:nb_udm_plugin:discoveryresult_list')


# --- DiscoveryMapping ---

@register_model_view(models.DiscoveryMapping)
class DiscoveryMappingView(generic.ObjectView):
    queryset = models.DiscoveryMapping.objects.all()


@register_model_view(models.DiscoveryMapping, 'list', detail=False)
class DiscoveryMappingListView(generic.ObjectListView):
    queryset = models.DiscoveryMapping.objects.all()
    table = tables.DiscoveryMappingTable
    filterset = filtersets.DiscoveryMappingFilterSet
    filterset_form = forms.DiscoveryMappingFilterForm
