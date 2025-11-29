from django.urls import path, include
from rest_framework.routers import DefaultRouter
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

app_name = 'archive'

urlpatterns = [
    path('', include(router.urls)),
]
