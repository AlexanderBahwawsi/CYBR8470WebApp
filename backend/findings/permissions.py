"""Role checks shared by the HTML views and the REST API.

Roles are Django groups:
  * Analyst  - records and edits findings and engagements
  * Owner    - updates the status of findings assigned to them
  * Manager  - read-only access to everything, plus CSV export
Superusers can do everything.
"""
from rest_framework import permissions

ANALYST = "Analyst"
OWNER = "Owner"
MANAGER = "Manager"
ROLES = (ANALYST, OWNER, MANAGER)


def _in_group(user, name):
    return user.is_authenticated and user.groups.filter(name=name).exists()


def is_analyst(user):
    return user.is_authenticated and (user.is_superuser or _in_group(user, ANALYST))


def is_manager(user):
    return user.is_authenticated and (user.is_superuser or _in_group(user, MANAGER))


def can_edit_finding(user, finding=None):
    return is_analyst(user)


def can_change_status(user, finding):
    return is_analyst(user) or (
        user.is_authenticated and finding.owner_id == user.id
    )


def can_export(user):
    return is_analyst(user) or is_manager(user)


def role_flags(request):
    """Template context processor."""
    user = request.user
    return {"is_analyst": is_analyst(user), "can_export": can_export(user)}


class FindingAPIPermission(permissions.BasePermission):
    """Everyone signed in may read; only analysts may write through the API."""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return is_analyst(request.user)
