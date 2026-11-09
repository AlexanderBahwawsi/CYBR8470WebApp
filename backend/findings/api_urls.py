from rest_framework.routers import DefaultRouter

from .api import EngagementViewSet, FindingViewSet

router = DefaultRouter()
router.register("engagements", EngagementViewSet, basename="api-engagement")
router.register("findings", FindingViewSet, basename="api-finding")

urlpatterns = router.urls
