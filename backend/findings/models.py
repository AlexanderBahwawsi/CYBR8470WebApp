from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


class Engagement(models.Model):
    """An assessment (e.g. "2026 AWS architecture review") that findings belong to."""

    name = models.CharField(max_length=150, unique=True)
    organization = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="engagements"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class Finding(models.Model):
    class Severity(models.IntegerChoices):
        LOW = 1, "Low"
        MEDIUM = 2, "Medium"
        HIGH = 3, "High"
        CRITICAL = 4, "Critical"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In progress"
        REMEDIATED = "remediated", "Remediated"
        ACCEPTED = "accepted", "Risk accepted"
        FALSE_POSITIVE = "false_positive", "False positive"

    class Framework(models.TextChoices):
        NONE = "", "None"
        CIS = "cis", "CIS Benchmark"
        NIST_CSF = "nist_csf", "NIST CSF"
        ATTACK = "attack", "MITRE ATT&CK"
        OWASP = "owasp", "OWASP Top Ten"

    CLOSED_STATUSES = (Status.REMEDIATED, Status.ACCEPTED, Status.FALSE_POSITIVE)

    engagement = models.ForeignKey(
        Engagement, on_delete=models.CASCADE, related_name="findings"
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    affected_asset = models.CharField(max_length=200, blank=True)
    severity = models.IntegerField(choices=Severity.choices, default=Severity.MEDIUM)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OPEN
    )
    framework = models.CharField(
        max_length=20, choices=Framework.choices, blank=True, default=""
    )
    control_ref = models.CharField(
        "control / technique reference",
        max_length=60,
        blank=True,
        help_text="e.g. CIS 1.4, PR.AC-4, T1078, A01:2021",
    )
    remediation = models.TextField("recommended remediation", blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_findings",
        help_text="Person responsible for fixing this finding",
    )
    due_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="reported_findings"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-severity", "due_date", "-created_at"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("finding-detail", args=[self.pk])

    @property
    def is_closed(self):
        return self.status in self.CLOSED_STATUSES

    @property
    def is_overdue(self):
        return (
            self.due_date is not None
            and not self.is_closed
            and self.due_date < timezone.localdate()
        )


class AuditEvent(models.Model):
    """Append-only record of who changed what. Never edited through the app."""

    class Action(models.TextChoices):
        CREATED = "created", "Created"
        UPDATED = "updated", "Updated"
        STATUS = "status", "Status changed"
        EXPORTED = "exported", "Exported"

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="audit_events"
    )
    finding = models.ForeignKey(
        Finding, on_delete=models.SET_NULL, null=True, blank=True, related_name="events"
    )
    action = models.CharField(max_length=20, choices=Action.choices)
    detail = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.actor} {self.action} {self.finding_id or ''}".strip()
