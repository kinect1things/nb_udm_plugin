from django.urls import path

from . import views

urlpatterns = [
    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),

    # DiscoverySource
    path('sources/', views.DiscoverySourceListView.as_view(), name='discoverysource_list'),
    path('sources/add/', views.DiscoverySourceAddView.as_view(), name='discoverysource_add'),
    path('sources/<int:pk>/', views.DiscoverySourceView.as_view(), name='discoverysource'),
    path('sources/<int:pk>/edit/', views.DiscoverySourceEditView.as_view(), name='discoverysource_edit'),
    path('sources/<int:pk>/delete/', views.DiscoverySourceDeleteView.as_view(), name='discoverysource_delete'),
    path('sources/<int:pk>/test/', views.DiscoverySourceTestView.as_view(), name='discoverysource_test'),
    path('sources/<int:pk>/scan/', views.DiscoverySourceScanView.as_view(), name='discoverysource_scan'),
    path('sources/<int:pk>/changelog/', views.DiscoverySourceChangeLogView.as_view(), name='discoverysource_changelog'),
    path('sources/<int:pk>/jobs/', views.DiscoverySourceJobsView.as_view(), name='discoverysource_jobs'),

    # ScanJob
    path('scan-jobs/', views.ScanJobListView.as_view(), name='scanjob_list'),
    path('scan-jobs/<int:pk>/', views.ScanJobView.as_view(), name='scanjob'),
    path('scan-jobs/<int:pk>/changelog/', views.ScanJobChangeLogView.as_view(), name='scanjob_changelog'),

    # DiscoveryResult
    path('results/', views.DiscoveryResultListView.as_view(), name='discoveryresult_list'),
    path('results/<int:pk>/', views.DiscoveryResultView.as_view(), name='discoveryresult'),
    path('results/<int:pk>/approve/', views.DiscoveryResultApproveView.as_view(), name='discoveryresult_approve'),
    path('results/<int:pk>/reject/', views.DiscoveryResultRejectView.as_view(), name='discoveryresult_reject'),
    path('results/bulk-approve/', views.DiscoveryResultBulkApproveView.as_view(), name='discoveryresult_bulk_approve'),
    path('results/bulk-reject/', views.DiscoveryResultBulkRejectView.as_view(), name='discoveryresult_bulk_reject'),
    path('results/<int:pk>/changelog/', views.DiscoveryResultChangeLogView.as_view(), name='discoveryresult_changelog'),

    # DiscoveryMapping
    path('mappings/', views.DiscoveryMappingListView.as_view(), name='discoverymapping_list'),
    path('mappings/<int:pk>/', views.DiscoveryMappingView.as_view(), name='discoverymapping'),
    path('mappings/<int:pk>/changelog/', views.DiscoveryMappingChangeLogView.as_view(), name='discoverymapping_changelog'),
]
