"""Create the role groups, three demo accounts and a handful of sample findings."""
import os
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.utils import timezone

from findings.models import Engagement, Finding
from findings.permissions import ANALYST, OWNER, ROLES

SAMPLES = [
    ("Root account has no MFA", 4, "open", "cis", "CIS 1.5", "AWS root account", -5),
    ("IAM users with AdministratorAccess", 3, "in_progress", "nist_csf", "PR.AC-4", "IAM", 10),
    ("S3 bucket allows public read", 3, "open", "owasp", "A01:2021", "s3://reports-archive", -2),
    ("Security group open to 0.0.0.0/0 on 22", 3, "remediated", "attack", "T1133", "sg-web-01", 3),
    ("CloudTrail not enabled in all regions", 2, "open", "cis", "CIS 3.1", "CloudTrail", 20),
    ("Access keys older than 90 days", 2, "in_progress", "cis", "CIS 1.14", "IAM", 14),
    ("Missing Content-Security-Policy header", 1, "accepted", "owasp", "A05:2021", "portal.example.gov", None),
    ("Verbose server banner", 1, "open", "owasp", "A05:2021", "api.example.gov", 30),
]


class Command(BaseCommand):
    help = "Seed role groups, demo users and sample findings (development only)."

    def handle(self, *args, **options):
        password = os.environ.get("DEMO_PASSWORD", "ChangeMe-demo-123")
        User = get_user_model()
        users = {}
        for role in ROLES:
            group, _ = Group.objects.get_or_create(name=role)
            user, created = User.objects.get_or_create(username=role.lower())
            if created:
                user.set_password(password)
                user.save()
            user.groups.add(group)
            users[role] = user

        engagement, _ = Engagement.objects.get_or_create(
            name="Sample cloud security assessment",
            defaults={
                "organization": "City of Exampleville",
                "description": "Demo data created by seed_demo.",
                "created_by": users[ANALYST],
            },
        )
        today = timezone.localdate()
        for title, severity, status, framework, ref, asset, due in SAMPLES:
            Finding.objects.get_or_create(
                engagement=engagement,
                title=title,
                defaults={
                    "description": f"Demo finding: {title}.",
                    "severity": severity,
                    "status": status,
                    "framework": framework,
                    "control_ref": ref,
                    "affected_asset": asset,
                    "owner": users[OWNER],
                    "due_date": today + timedelta(days=due) if due is not None else None,
                    "created_by": users[ANALYST],
                },
            )
        self.stdout.write(
            self.style.SUCCESS(
                "Seeded demo users: analyst, owner, manager "
                "(password from DEMO_PASSWORD)."
            )
        )
