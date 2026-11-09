from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("findings/", views.FindingListView.as_view(), name="finding-list"),
    path("findings/new/", views.FindingCreateView.as_view(), name="finding-create"),
    path("findings/export.csv", views.export_csv, name="finding-export"),
    path("findings/<int:pk>/", views.FindingDetailView.as_view(), name="finding-detail"),
    path("findings/<int:pk>/edit/", views.FindingUpdateView.as_view(), name="finding-update"),
    path("findings/<int:pk>/status/", views.change_status, name="finding-status"),
    path("engagements/", views.EngagementListView.as_view(), name="engagement-list"),
    path("engagements/new/", views.EngagementCreateView.as_view(), name="engagement-create"),
]
