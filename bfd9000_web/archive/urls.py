"""
URL configuration for the archive app.

This module defines the API routes using DRF routers, including nested routes
for hierarchical resources (e.g., subjects -> encounters -> records).
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
subjects_router = routers.NestedDefaultRouter(router, r'subjects', lookup='subject')
subjects_router.register(r'encounters', views.EncounterViewSet, basename='subject-encounters')
subjects_router.register(r'records', views.RecordViewSet, basename='subject-records')

encounters_router = routers.NestedDefaultRouter(router, r'encounters', lookup='encounter')
encounters_router.register(r'records', views.RecordViewSet, basename='encounter-records')

app_name = 'archive'

urlpatterns = [
    path('', include(router.urls)),
    path('', include(subjects_router.urls)),
    path('', include(encounters_router.urls)),
]
