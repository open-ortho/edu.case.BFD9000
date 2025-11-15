from django.urls import path

from . import views

app_name = "archive"

urlpatterns = [
    path("", views.SubjectListView.as_view(), name="home"),
    path("subjects/", views.SubjectListView.as_view(), name="subjects"),
    path("subjects/<int:pk>/", views.SubjectDetailView.as_view(), name="subject-detail"),
    path(
        "subjects/<int:subject_pk>/records/add/",
        views.RecordCreateView.as_view(),
        name="record-add",
    ),
    path("reports/", views.ReportsTodoView.as_view(), name="reports"),
]
