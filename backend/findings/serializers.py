from rest_framework import serializers

from .models import Engagement, Finding


class EngagementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Engagement
        fields = ["id", "name", "organization", "description", "created_at"]
        read_only_fields = ["created_at"]


class FindingSerializer(serializers.ModelSerializer):
    severity_label = serializers.CharField(source="get_severity_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = Finding
        fields = [
            "id", "engagement", "title", "description", "affected_asset",
            "severity", "severity_label", "status", "status_label",
            "framework", "control_ref", "remediation", "owner", "due_date",
            "is_overdue", "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
