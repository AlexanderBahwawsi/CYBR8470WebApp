from .models import AuditEvent


def record(actor, action, finding=None, detail=""):
    return AuditEvent.objects.create(
        actor=actor, action=action, finding=finding, detail=detail[:500]
    )
