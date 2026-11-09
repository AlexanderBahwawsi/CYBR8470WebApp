from rest_framework import viewsets

from . import audit
from .models import AuditEvent, Engagement, Finding
from .permissions import FindingAPIPermission
from .serializers import EngagementSerializer, FindingSerializer


class EngagementViewSet(viewsets.ModelViewSet):
    queryset = Engagement.objects.all()
    serializer_class = EngagementSerializer
    permission_classes = [FindingAPIPermission]
    http_method_names = ["get", "post", "put", "patch", "head", "options"]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class FindingViewSet(viewsets.ModelViewSet):
    serializer_class = FindingSerializer
    permission_classes = [FindingAPIPermission]
    # Findings are closed, never deleted, so the history stays intact.
    http_method_names = ["get", "post", "put", "patch", "head", "options"]

    def get_queryset(self):
        qs = Finding.objects.select_related("engagement", "owner")
        params = self.request.query_params
        if params.get("status") in Finding.Status.values:
            qs = qs.filter(status=params["status"])
        if params.get("severity", "").isdigit():
            qs = qs.filter(severity=int(params["severity"]))
        return qs

    def perform_create(self, serializer):
        finding = serializer.save(created_by=self.request.user)
        audit.record(self.request.user, AuditEvent.Action.CREATED, finding, "via API")

    def perform_update(self, serializer):
        finding = serializer.save()
        audit.record(self.request.user, AuditEvent.Action.UPDATED, finding, "via API")
