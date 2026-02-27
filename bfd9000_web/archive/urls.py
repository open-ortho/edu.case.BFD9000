"""
URL configuration for the archive app.

This module defines both template routes for HTML pages and API routes using DRF routers,
including nested routes for hierarchical resources (e.g., subjects -> encounters -> records).
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers
from . import views

router = DefaultRouter()
router.register(r'codings', views.CodingViewSet)
router.register(r'identifiers', views.IdentifierViewSet)
router.register(r'addresses', views.AddressViewSet)
router.register(r'locations', views.LocationViewSet)
router.register(r'collections', views.CollectionViewSet)
router.register(r'subjects', views.SubjectViewSet)
router.register(r'encounters', views.EncounterViewSet)
router.register(r'imaging-studies', views.ImagingStudyViewSet)
router.register(r'records', views.RecordViewSet)
router.register(r'valuesets', views.ValuesetViewSet, basename='valuesets')

# Nested routers
subjects_router = routers.NestedDefaultRouter(
    router, r'subjects', lookup='subject')
subjects_router.register(
    r'encounters', views.EncounterViewSet, basename='subject-encounters')
subjects_router.register(r'records', views.RecordViewSet,
                         basename='subject-records')

encounters_router = routers.NestedDefaultRouter(
    router, r'encounters', lookup='encounter')
encounters_router.register(
    r'records', views.RecordViewSet, basename='encounter-records')

# Django expects `app_name` for namespacing URLs.
# pylint: disable=invalid-name
app_name = 'archive'

urlpatterns = [
    # Template views for HTML pages
    path('', views.index, name='index'),
    path('subjects/', views.subjects, name='subjects'),
    path('subjects/create/', views.subject_create, name='subject_create'),
    path('encounters/', views.encounters, name='encounters'),
    path('encounters/create/', views.encounter_create, name='encounter_create'),
    path('records/', views.records, name='records'),
    path('records/<str:record_id>/', views.record_detail, name='record_detail'),
    path('scan/', views.scan, name='scan'),
    path('api/scan/tiff-preview/', views.scan_tiff_preview, name='scan_tiff_preview'),
    # API routes
    path('api/', include(router.urls)),
    path('api/', include(subjects_router.urls)),
    path('api/', include(encounters_router.urls)),
]
