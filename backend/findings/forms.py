from django import forms

from .models import Engagement, Finding


class EngagementForm(forms.ModelForm):
    class Meta:
        model = Engagement
        fields = ["name", "organization", "description"]


class FindingForm(forms.ModelForm):
    class Meta:
        model = Finding
        fields = [
            "engagement",
            "title",
            "description",
            "affected_asset",
            "severity",
            "framework",
            "control_ref",
            "remediation",
            "owner",
            "due_date",
        ]
        widgets = {
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 5}),
            "remediation": forms.Textarea(attrs={"rows": 4}),
        }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("control_ref") and not cleaned.get("framework"):
            self.add_error("framework", "Choose the framework this reference belongs to.")
        return cleaned


class StatusForm(forms.Form):
    status = forms.ChoiceField(choices=Finding.Status.choices)
    note = forms.CharField(
        max_length=300,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "What changed? (optional)"}),
    )


class FindingFilterForm(forms.Form):
    q = forms.CharField(required=False, max_length=100, label="Search")
    severity = forms.ChoiceField(
        required=False, choices=[("", "Any severity")] + list(Finding.Severity.choices)
    )
    status = forms.ChoiceField(
        required=False, choices=[("", "Any status")] + list(Finding.Status.choices)
    )
    engagement = forms.ModelChoiceField(
        required=False, queryset=Engagement.objects.all(), empty_label="Any engagement"
    )
    mine = forms.BooleanField(required=False, label="Assigned to me")
