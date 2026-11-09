import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from . import audit, permissions
from .forms import EngagementForm, FindingFilterForm, FindingForm, StatusForm
from .models import AuditEvent, Engagement, Finding


def filtered_findings(params, user):
    """Apply the list filters. Shared by the list page and the CSV export."""
    qs = Finding.objects.select_related("engagement", "owner")
    form = FindingFilterForm(params)
    if form.is_valid():
        data = form.cleaned_data
        if data["q"]:
            qs = qs.filter(
                Q(title__icontains=data["q"])
                | Q(affected_asset__icontains=data["q"])
                | Q(control_ref__icontains=data["q"])
            )
        if data["severity"]:
            qs = qs.filter(severity=data["severity"])
        if data["status"]:
            qs = qs.filter(status=data["status"])
        if data["engagement"]:
            qs = qs.filter(engagement=data["engagement"])
        if data["mine"]:
            qs = qs.filter(owner=user)
    return qs, form


@login_required
def dashboard(request):
    findings = Finding.objects.all()
    open_findings = findings.exclude(status__in=Finding.CLOSED_STATUSES)
    by_severity = dict(
        open_findings.values_list("severity").annotate(n=Count("id")).order_by()
    )
    by_status = dict(findings.values_list("status").annotate(n=Count("id")).order_by())
    context = {
        "total": findings.count(),
        "open_total": open_findings.count(),
        "severity_rows": [
            (label, by_severity.get(value, 0), value)
            for value, label in reversed(Finding.Severity.choices)
        ],
        "status_rows": [
            (label, by_status.get(value, 0)) for value, label in Finding.Status.choices
        ],
        "overdue": open_findings.filter(due_date__lt=timezone.localdate())
        .select_related("owner")
        .order_by("due_date")[:10],
        "my_findings": open_findings.filter(owner=request.user)[:10],
        "recent_events": AuditEvent.objects.select_related("actor", "finding")[:8],
    }
    return render(request, "findings/dashboard.html", context)


class FindingListView(LoginRequiredMixin, ListView):
    template_name = "findings/finding_list.html"
    context_object_name = "findings"
    paginate_by = 25

    def get_queryset(self):
        qs, self.filter_form = filtered_findings(self.request.GET, self.request.user)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = self.filter_form
        params = self.request.GET.copy()
        params.pop("page", None)
        context["querystring"] = params.urlencode()
        return context


class FindingDetailView(LoginRequiredMixin, DetailView):
    model = Finding
    template_name = "findings/finding_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        finding = self.object
        context["can_edit"] = permissions.can_edit_finding(self.request.user, finding)
        context["can_change_status"] = permissions.can_change_status(
            self.request.user, finding
        )
        context["status_form"] = StatusForm(initial={"status": finding.status})
        context["events"] = finding.events.select_related("actor")[:20]
        return context


class AnalystRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    raise_exception = True

    def test_func(self):
        return permissions.is_analyst(self.request.user)


class FindingCreateView(AnalystRequiredMixin, CreateView):
    model = Finding
    form_class = FindingForm
    template_name = "findings/finding_form.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        audit.record(self.request.user, AuditEvent.Action.CREATED, self.object)
        messages.success(self.request, "Finding recorded.")
        return response


class FindingUpdateView(AnalystRequiredMixin, UpdateView):
    model = Finding
    form_class = FindingForm
    template_name = "findings/finding_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        audit.record(
            self.request.user,
            AuditEvent.Action.UPDATED,
            self.object,
            "Changed: " + ", ".join(form.changed_data) if form.changed_data else "",
        )
        messages.success(self.request, "Finding updated.")
        return response


@login_required
@require_POST
def change_status(request, pk):
    finding = get_object_or_404(Finding, pk=pk)
    if not permissions.can_change_status(request.user, finding):
        raise PermissionDenied
    form = StatusForm(request.POST)
    if form.is_valid():
        old = finding.get_status_display()
        finding.status = form.cleaned_data["status"]
        finding.save(update_fields=["status", "updated_at"])
        detail = f"{old} -> {finding.get_status_display()}"
        if form.cleaned_data["note"]:
            detail += f": {form.cleaned_data['note']}"
        audit.record(request.user, AuditEvent.Action.STATUS, finding, detail)
        messages.success(request, "Status updated.")
    else:
        messages.error(request, "That status is not valid.")
    return redirect(finding)


class EngagementListView(LoginRequiredMixin, ListView):
    template_name = "findings/engagement_list.html"
    context_object_name = "engagements"

    def get_queryset(self):
        return Engagement.objects.annotate(
            finding_count=Count("findings"),
            open_count=Count(
                "findings", filter=~Q(findings__status__in=Finding.CLOSED_STATUSES)
            ),
        )


class EngagementCreateView(AnalystRequiredMixin, CreateView):
    model = Engagement
    form_class = EngagementForm
    template_name = "findings/engagement_form.html"
    success_url = reverse_lazy("engagement-list")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


def csv_safe(value):
    """Neutralise spreadsheet formula injection (cells starting with = + - @)."""
    text = "" if value is None else str(value)
    if text and text[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + text
    return text


@login_required
def export_csv(request):
    if not permissions.can_export(request.user):
        raise PermissionDenied
    findings, _ = filtered_findings(request.GET, request.user)
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="vulnledger-findings.csv"'
    writer = csv.writer(response)
    writer.writerow(
        ["ID", "Engagement", "Title", "Severity", "Status", "Asset", "Framework",
         "Reference", "Owner", "Due date"]
    )
    count = 0
    for f in findings:
        writer.writerow(
            csv_safe(v)
            for v in [
                f.pk, f.engagement.name, f.title, f.get_severity_display(),
                f.get_status_display(), f.affected_asset, f.get_framework_display(),
                f.control_ref, f.owner.username if f.owner else "", f.due_date or "",
            ]
        )
        count += 1
    audit.record(request.user, AuditEvent.Action.EXPORTED, detail=f"{count} findings to CSV")
    return response
