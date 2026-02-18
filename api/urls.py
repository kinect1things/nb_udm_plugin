from netbox.api.routers import NetBoxRouter

from . import views

router = NetBoxRouter()
router.register('sources', views.DiscoverySourceViewSet)
router.register('scan-jobs', views.ScanJobViewSet)
router.register('results', views.DiscoveryResultViewSet)
router.register('mappings', views.DiscoveryMappingViewSet)

urlpatterns = router.urls
