from django.urls import path

from . import views

app_name = "archive"

urlpatterns = [
    path("", views.index, name="index"),
    path("subjects/", views.subjects, name="subjects"),
    path("subjects/create/", views.subject_create, name="subject_create"),
    path("encounters/", views.encounters, name="encounters"),
    path("records/", views.records, name="records"),
    path("records/<str:record_id>/", views.record_detail, name="record_detail"),
]
