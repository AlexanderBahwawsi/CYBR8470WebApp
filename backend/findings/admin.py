from django.contrib import admin

from .models import AuditEvent, Engagement, Finding


@admin.register(Engagement)
class EngagementAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "created_by", "created_at")
    search_fields = ("name", "organization")


@admin.register(Finding)
class FindingAdmin(admin.ModelAdmin):
    list_display = ("title", "engagement", "severity", "status", "owner", "due_date")
    list_filter = ("severity", "status", "framework", "engagement")
    search_fields = ("title", "affected_asset", "control_ref")


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    """Read-only: the audit trail cannot be edited or deleted from the admin."""

    list_display = ("created_at", "actor", "action", "finding", "detail")
    list_filter = ("action",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
