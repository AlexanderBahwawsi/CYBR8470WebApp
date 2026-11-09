from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from .models import AuditEvent, Engagement, Finding
from .permissions import ANALYST, MANAGER, OWNER
from .views import csv_safe


class BaseCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.users = {}
        for role in (ANALYST, OWNER, MANAGER):
            user = User.objects.create_user(role.lower(), password="pw-for-tests-123")
            user.groups.add(Group.objects.create(name=role))
            cls.users[role] = user
        cls.other_owner = User.objects.create_user("other", password="pw-for-tests-123")
        cls.engagement = Engagement.objects.create(
            name="E1", organization="Org", created_by=cls.users[ANALYST]
        )
        cls.finding = Finding.objects.create(
            engagement=cls.engagement,
            title="=cmd|' /C calc'!A0",
            description="d",
            owner=cls.users[OWNER],
            created_by=cls.users[ANALYST],
        )

    def login(self, role):
        self.client.force_login(self.users[role])


class AccessControlTests(BaseCase):
    def test_pages_require_login(self):
        for name in ("dashboard", "finding-list", "finding-export", "engagement-list"):
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 302)
            self.assertIn("/login/", response["Location"])

    def test_api_requires_login(self):
        self.assertEqual(self.client.get("/api/findings/").status_code, 403)

    def test_owner_cannot_create_or_edit(self):
        self.login(OWNER)
        self.assertEqual(self.client.get(reverse("finding-create")).status_code, 403)
        url = reverse("finding-update", args=[self.finding.pk])
        self.assertEqual(self.client.post(url, {"title": "x"}).status_code, 403)

    def test_owner_can_change_status_of_own_finding(self):
        self.login(OWNER)
        url = reverse("finding-status", args=[self.finding.pk])
        self.client.post(url, {"status": "remediated", "note": "patched"})
        self.finding.refresh_from_db()
        self.assertEqual(self.finding.status, "remediated")
        self.assertTrue(
            AuditEvent.objects.filter(finding=self.finding, action="status").exists()
        )

    def test_other_user_cannot_change_status(self):
        self.client.force_login(self.other_owner)
        url = reverse("finding-status", args=[self.finding.pk])
        self.assertEqual(self.client.post(url, {"status": "remediated"}).status_code, 403)
        self.finding.refresh_from_db()
        self.assertEqual(self.finding.status, "open")

    def test_status_change_rejects_get(self):
        self.login(ANALYST)
        url = reverse("finding-status", args=[self.finding.pk])
        self.assertEqual(self.client.get(url).status_code, 405)

    def test_api_write_is_analyst_only(self):
        self.login(MANAGER)
        payload = {"engagement": self.engagement.pk, "title": "t", "description": "d"}
        self.assertEqual(self.client.post("/api/findings/", payload).status_code, 403)
        self.login(ANALYST)
        self.assertEqual(self.client.post("/api/findings/", payload).status_code, 201)

    def test_api_cannot_delete(self):
        self.login(ANALYST)
        response = self.client.delete(f"/api/findings/{self.finding.pk}/")
        self.assertEqual(response.status_code, 405)


class FindingFlowTests(BaseCase):
    def test_analyst_creates_finding(self):
        self.login(ANALYST)
        response = self.client.post(
            reverse("finding-create"),
            {
                "engagement": self.engagement.pk,
                "title": "Open bucket",
                "description": "Public read",
                "severity": 3,
                "framework": "owasp",
                "control_ref": "A01:2021",
            },
        )
        finding = Finding.objects.get(title="Open bucket")
        self.assertRedirects(response, finding.get_absolute_url())
        self.assertEqual(finding.created_by, self.users[ANALYST])

    def test_reference_requires_framework(self):
        self.login(ANALYST)
        response = self.client.post(
            reverse("finding-create"),
            {
                "engagement": self.engagement.pk, "title": "x", "description": "y",
                "severity": 1, "framework": "", "control_ref": "CIS 1.1",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Finding.objects.filter(title="x").exists())

    def test_title_is_escaped_in_html(self):
        Finding.objects.create(
            engagement=self.engagement, title="<script>alert(1)</script>",
            description="d", created_by=self.users[ANALYST],
        )
        self.login(MANAGER)
        response = self.client.get(reverse("finding-list"))
        self.assertNotContains(response, "<script>alert(1)</script>")
        self.assertContains(response, "&lt;script&gt;alert(1)&lt;/script&gt;")

    def test_filter_by_severity(self):
        self.login(MANAGER)
        response = self.client.get(reverse("finding-list"), {"severity": 4})
        self.assertEqual(len(response.context["findings"]), 0)


class ExportTests(BaseCase):
    def test_csv_safe(self):
        self.assertEqual(csv_safe("=1+1"), "'=1+1")
        self.assertEqual(csv_safe("@SUM(A1)"), "'@SUM(A1)")
        self.assertEqual(csv_safe("normal"), "normal")
        self.assertEqual(csv_safe(None), "")

    def test_export_neutralises_formulas_and_is_audited(self):
        self.login(MANAGER)
        response = self.client.get(reverse("finding-export"))
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("'=cmd", response.content.decode())
        self.assertTrue(AuditEvent.objects.filter(action="exported").exists())

    def test_owner_cannot_export(self):
        self.login(OWNER)
        self.assertEqual(self.client.get(reverse("finding-export")).status_code, 403)


class CsrfTests(BaseCase):
    def test_status_change_without_csrf_token_is_refused(self):
        from django.test import Client

        client = Client(enforce_csrf_checks=True)
        client.force_login(self.users[ANALYST])
        url = reverse("finding-status", args=[self.finding.pk])
        self.assertEqual(client.post(url, {"status": "remediated"}).status_code, 403)
        self.finding.refresh_from_db()
        self.assertEqual(self.finding.status, "open")
