"""
Views for the archive app.

This module defines the ViewSets for the API, handling CRUD operations
for subjects, encounters, records, and related medical entities.
It also includes custom actions for file serving and valueset retrieval.
"""
import os
from typing import Any, Dict, List, Optional, Type

from PIL import Image
from rest_framework import viewsets, serializers, filters
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from .permissions import CuratorOrSuperuserEditPermission, RecordPermission
from rest_framework.request import Request
from rest_framework.response import Response
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Case, CharField, Count, OuterRef, QuerySet, Subquery, When, Prefetch
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from .models import (
    Coding, Identifier, Address, Collection, Subject,
    ArchiveLocation, Encounter, Endpoint, Location, ImagingStudy, Series,
    PhysicalLocation, PhysicalRecord, DigitalRecord, Device, ValueSet
)
from .serializers import (
    CodingSerializer, IdentifierSerializer, AddressSerializer,
    ArchiveLocationSerializer, CollectionSerializer, SubjectSerializer, EncounterSerializer,
    EndpointSerializer, LocationSerializer, ImagingStudySerializer, DigitalRecordSerializer,
    DigitalRecordUploadSerializer, DeviceSerializer, SeriesSerializer,
    PhysicalLocationSerializer, PhysicalRecordSerializer,
)
from .constants import (
    SYSTEM_IDENTIFIER_BOLTON_SUBJECT,
    SYSTEM_IDENTIFIER_LANCASTER_SUBJECT,
)
from .filters import DigitalRecordFilter
from .media_utils import convert_tiff_to_png_bytes

MAX_TIFF_PREVIEW_BYTES = 100 * 1024 * 1024
MAX_TIFF_PREVIEW_PIXELS = 100_000_000
Image.MAX_IMAGE_PIXELS = MAX_TIFF_PREVIEW_PIXELS


class ValuesetViewSet(viewsets.ViewSet):
    """
    API endpoint that allows valuesets to be viewed.

    Provides a read-only interface for retrieving standard codes and options
    used throughout the application (e.g., sex, modalities, orientations).
    """
    # NOTE: This viewset is read-only and not tied to a specific model/queryset,
    # so DjangoModelPermissions (the project-wide default) are not applicable.
    # We intentionally use IsAuthenticated here to require login but not model-level perms.
    permission_classes = [IsAuthenticated]

    def list(self, request: Request) -> Response:
        """
        List values for a specific valueset type.

        Args:
            request: The HTTP request containing the 'type' query parameter.

        Returns:
            Response: A list of dictionaries with 'id' and 'display' keys.
        """
        valueset_type = request.query_params.get('type')
        if not valueset_type:
            return Response({"error": "Missing 'type' parameter"}, status=400)

        data: List[Dict[str, Any]] = []

        if valueset_type == 'sex_options':
            data = [{'id': k, 'display': v} for k, v in Subject.GENDER_CHOICES]

        elif valueset_type == 'collections':
            colls = Collection.objects.all()
            data = [{'id': c.short_name, 'display': c.full_name}
                    for c in colls]

        else:
            valueset = ValueSet.objects.filter(slug=valueset_type).first()
            if valueset:
                codings = Coding.objects.filter(value_sets=valueset).order_by('code')
                data = [{'id': c.code, 'display': c.display} for c in codings]
                return Response(data)

            return Response({"error": f"Unknown valueset type: {valueset_type}"}, status=404)

        return Response(data)


class CodingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Coding model.

    Handles standard medical codes (SNOMED, DICOM, etc.).
    """
    queryset = Coding.objects.all()
    serializer_class = CodingSerializer
    filterset_fields = ['system', 'code']


class IdentifierViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Identifier model.

    Handles identifiers associated with subjects and other entities.
    """
    queryset = Identifier.objects.all()
    serializer_class = IdentifierSerializer
    filterset_fields = ['system', 'value', 'use']


class AddressViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Address model.
    """
    queryset = Address.objects.all()
    serializer_class = AddressSerializer


class LocationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Location model.

    Represents physical locations where encounters or scans occur.
    """
    queryset = Location.objects.all()
    serializer_class = LocationSerializer


class CollectionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Collection model.

    Manages collections of records (e.g., specific studies or datasets).
    """
    queryset = Collection.objects.all()
    serializer_class = CollectionSerializer
    filterset_fields = ['short_name']


class SubjectViewSet(viewsets.ModelViewSet):
    permission_classes = [CuratorOrSuperuserEditPermission]
    """
    ViewSet for Subject model.

    Manages patient/subject information including demographics.
    Subjects are ordered by their preferred display identifier (official →
    Bolton system → first), resolved at the database level via correlated
    subqueries to match the serializer's ``subject_identifier`` field.
    """
    queryset = Subject.objects.prefetch_related(
        'identifiers'
    ).annotate(
        encounter_count=Count('encounters', distinct=True),
        record_count=Count('encounters__imaging_study__series__digital_records', distinct=True),
        physical_record_count=Count('encounters__physical_records', distinct=True),
        official_identifier=Subquery(
            Identifier.objects.filter(
                subjects=OuterRef('pk'),
                use='official',
            ).order_by('pk').values('value')[:1],
            output_field=CharField(),
        ),
    ).order_by('official_identifier', 'id')
    serializer_class = SubjectSerializer
    filterset_fields = {
        'identifiers__value',
        'gender',
        'ethnicity__code',
        'skeletal_pattern__code',
        'palatal_cleft__code',
        'collection__short_name',
    }
    search_fields = ['^identifiers__value']


class EncounterViewSet(viewsets.ModelViewSet):
    permission_classes = [CuratorOrSuperuserEditPermission]
    """
    ViewSet for Encounter model.

    Manages clinical encounters or visits.
    """
    queryset = Encounter.objects.select_related(
        'subject'
    ).prefetch_related(
        'subject__identifiers'
    ).annotate(
        record_count=Count('imaging_study__series__digital_records', distinct=True)
    ).order_by('-actual_period_start', '-id')
    serializer_class = EncounterSerializer
    filterset_fields = ['subject', 'actual_period_start']
    search_fields = ['^subject__identifiers__value']

    def perform_create(self, serializer: serializers.BaseSerializer) -> None:
        """
        Custom creation logic to handle subject association and age calculation.
        """
        subject = serializer.validated_data.get('subject')

        # If not in body, check URL
        if not subject:
            subject_pk = self.kwargs.get('subject_pk')
            if subject_pk:
                subject = get_object_or_404(Subject, pk=subject_pk)
            else:
                raise serializers.ValidationError(
                    {"subject": "This field is required."})

        # Calculate age_at_encounter if not provided
        if 'age_at_encounter' not in serializer.validated_data:
            encounter_date = serializer.validated_data.get(
                'actual_period_start')

            if subject and subject.birth_date and encounter_date:
                # Calculate duration
                delta = encounter_date - subject.birth_date
                serializer.save(subject=subject,
                                procedure_occurrence_age=delta)
                return

        serializer.save(subject=subject)


class ImagingStudyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for ImagingStudy model.
    
    Manages the technical details of an imaging session.
    """
    queryset = ImagingStudy.objects.prefetch_related(
        Prefetch(
            'series__digital_records',
            queryset=DigitalRecord.objects.filter(operator__isnull=False).select_related('operator').order_by('-created_at'),
            to_attr='_operator_records',
        )
    )
    serializer_class = ImagingStudySerializer
    filterset_fields = ['encounter', 'collection']


class SeriesViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Series model.

    Exposes series grouped under imaging studies. Standard CRUD.
    Requires authentication to prevent unauthenticated enumeration of all series.
    """
    queryset = Series.objects.select_related('imaging_study', 'modality').prefetch_related('digital_records')
    serializer_class = SeriesSerializer
    permission_classes = [IsAuthenticated]


class EndpointViewSet(viewsets.ModelViewSet):
    """ViewSet for archive Endpoint definitions."""

    queryset = Endpoint.objects.all()
    serializer_class = EndpointSerializer
    filterset_fields = ['status', 'connection_type']
    search_fields = ['name', 'address']


class ArchiveLocationViewSet(viewsets.ModelViewSet):
    """ViewSet for archived storage locations of digital records."""

    queryset = ArchiveLocation.objects.select_related('digital_record', 'endpoint')
    serializer_class = ArchiveLocationSerializer
    filterset_fields = ['digital_record', 'endpoint', 'status', 'endpoint__connection_type']
    search_fields = ['assigned_id', 'digital_record__id', 'endpoint__name', 'endpoint__address']



class BoltonRecordSearchFilter(filters.SearchFilter):
    """SearchFilter subclass that applies .distinct() only when a search query is active.

    Prevents duplicate rows from the identifiers M2M JOIN on non-search requests,
    while ensuring correct results when searching via identifiers__value.
    """

    def filter_queryset(self, request, queryset, view):
        search_terms = self.get_search_terms(request)
        if search_terms:
            queryset = queryset.distinct()
        return super().filter_queryset(request, queryset, view)


class PhysicalLocationViewSet(viewsets.ModelViewSet):
    """ViewSet for PhysicalLocation — archive storage slots."""

    queryset = PhysicalLocation.objects.select_related('address')
    serializer_class = PhysicalLocationSerializer
    filterset_fields = ['cabinet', 'shelf']
    search_fields = ['cabinet', 'shelf', 'slot', 'raw']


class PhysicalRecordViewSet(viewsets.ModelViewSet):
    """ViewSet for PhysicalRecord model.

    Manages original physical artifacts (films, models, charts) linked to encounters.
    """

    queryset = PhysicalRecord.objects.select_related(
        'encounter__subject',
        'record_type',
        'device',
    ).prefetch_related(
        'encounter__subject__identifiers',
        'locations',
        'identifiers',
    )
    serializer_class = PhysicalRecordSerializer
    filterset_fields = ['encounter', 'record_type']
    filter_backends = [BoltonRecordSearchFilter, filters.OrderingFilter]
    search_fields = ['^identifiers__value']

    def get_queryset(self) -> QuerySet:
        qs = super().get_queryset()
        encounter_pk = self.kwargs.get('encounter_pk')
        if encounter_pk:
            qs = qs.filter(encounter__id=encounter_pk)
        subject_pk = self.kwargs.get('subject_pk')
        if subject_pk:
            qs = qs.filter(encounter__subject__id=subject_pk)
        return qs


class DigitalRecordViewSet(viewsets.ModelViewSet):
    permission_classes = [RecordPermission]
    """
    ViewSet for DigitalRecord model.

    Manages the high-level digital record entries that link encounters to imaging studies.
    Supports file uploads via a specialized serializer.
    """
    queryset = DigitalRecord.objects.select_related(
        'series__imaging_study__encounter',
        'series__modality',
        'record_type',
        'physical_record',
        'device',
    ).prefetch_related(
        'series__imaging_study__encounter__subject__identifiers',
        'archive_locations__endpoint',
        'identifiers'
    )
    serializer_class = DigitalRecordSerializer
    filterset_class = DigitalRecordFilter
    filter_backends = [BoltonRecordSearchFilter, filters.OrderingFilter]
    search_fields = ['^identifiers__value']

    def get_serializer_class(self) -> Type[serializers.Serializer]:
        if self.action == 'create':
            return DigitalRecordUploadSerializer
        return DigitalRecordSerializer

    def get_serializer_context(self) -> Dict[str, Any]:
        context = super().get_serializer_context()
        if self.action == 'create':
            # If nested, get encounter
            encounter_pk = self.kwargs.get('encounter_pk')
            if encounter_pk:
                encounter = get_object_or_404(Encounter, pk=encounter_pk)
                context['encounter'] = encounter
        return context

    def get_queryset(self) -> QuerySet:
        qs = super().get_queryset()
        # Filter by nested encounter if present (via series -> imaging_study)
        encounter_pk = self.kwargs.get('encounter_pk')
        if encounter_pk:
            qs = qs.filter(series__imaging_study__encounter__id=encounter_pk)

        # Filter by nested subject if present
        subject_pk = self.kwargs.get('subject_pk')
        if subject_pk:
            qs = qs.filter(series__imaging_study__encounter__subject__id=subject_pk)

        # Query param filter for record_type
        record_type = self.request.query_params.get('record_type')
        if record_type:
            qs = qs.filter(record_type__id=record_type)

        return qs

    @extend_schema(
        responses={
            (200, 'application/octet-stream'): OpenApiTypes.BINARY
        }
    )
    @action(detail=True, methods=['get'])
    def image(self, request: Request, pk: Optional[int] = None, **kwargs: Any) -> Any:
        del request, pk, kwargs
        digital_record = self.get_object()
        if not getattr(digital_record, 'source_file', None):
            return Response({"error": "No image file available"}, status=404)
        source_file = digital_record.source_file
        return FileResponse(source_file.open('rb'))

    @extend_schema(
        responses={
            (200, 'image/jpeg'): OpenApiTypes.BINARY
        }
    )
    @action(detail=True, methods=['get'])
    def thumbnail(self, request: Request, pk: Optional[int] = None, **kwargs: Any) -> Any:
        from django.contrib.staticfiles import finders
        del request, pk, kwargs
        digital_record = self.get_object()

        if getattr(digital_record, 'thumbnail', None):
            try:
                return FileResponse(digital_record.thumbnail.open('rb'), content_type='image/jpeg')
            except Exception:
                pass

        fallback_path = finders.find('archive/img/no-thumbnail.jpg')
        if fallback_path:
            with open(fallback_path, 'rb') as f:
                return HttpResponse(f.read(), content_type='image/jpeg')
        return JsonResponse({"error": "No thumbnail or fallback available."}, status=404)

    @action(detail=True, methods=['get'])
    def dicom(self, request: Request, pk: Optional[int] = None, **kwargs: Any) -> Any:
        del request, pk, kwargs
        return Response({"error": "DICOM download not implemented"}, status=404)


@login_required
def index(request):
    """Render the main archive dashboard."""
    return render(request, "archive/index.html")


@login_required
def subjects(request):
    """Render the subject list page."""
    return render(request, "archive/subjects.html")


@login_required
def subject_detail(request, subject_id):
    """Render the subject detail page."""
    return render(request, "archive/subject_detail.html", {"subject_id": subject_id})


@login_required
def subject_create(request):
    """Render the subject creation form."""
    return render(
        request,
        "archive/subject_create.html",
        {
            "bolton_identifier_system": SYSTEM_IDENTIFIER_BOLTON_SUBJECT,
            "lancaster_identifier_system": SYSTEM_IDENTIFIER_LANCASTER_SUBJECT,
        },
    )


@login_required
def encounters(request):
    """Render the encounter list page."""
    return render(request, "archive/encounters.html")


@login_required
def encounter_create(request):
    """Render the encounter creation form."""
    return render(request, "archive/encounter_create.html")


@login_required
def records(request):
    """Render the record list page."""
    return render(request, "archive/records.html")


@login_required
def physical_records(request):
    """Render the physical record list page."""
    return render(request, "archive/physical_records.html")


@login_required
def record_detail(request, record_id):
    """Render the record detail page."""
    return render(request, "archive/record_detail.html", {"record_id": record_id})

@login_required
def scan(request):
    """Render the scan workflow page."""
    full_name = request.user.get_full_name().strip()
    if full_name:
        operator_display = f"{full_name} ({request.user.username})"
    else:
        operator_display = request.user.username
    return render(
        request,
        "archive/scan.html",
        {
            "operator_display": operator_display,
            "scanner_api_base": settings.SCANNER_API_BASE,
            "scanner_device_id": settings.SCANNER_DEVICE_ID,
            "ai_base_url": settings.BFD9020_BASE_URL,
        },
    )


@login_required
@require_POST
def scan_tiff_preview(request):
    """Convert TIFF upload into a PNG preview for browser rendering and AI."""
    upload = request.FILES.get("file")
    if not upload:
        return JsonResponse({"error": "Missing file"}, status=400)

    if upload.size > MAX_TIFF_PREVIEW_BYTES:
        return JsonResponse({"error": "File too large"}, status=400)

    ext = os.path.splitext(upload.name)[1].lower()
    if ext not in {".tif", ".tiff"}:
        return JsonResponse({"error": "Only TIFF files are supported"}, status=400)

    try:
        png_bytes = convert_tiff_to_png_bytes(upload)
        return HttpResponse(png_bytes, content_type="image/png")
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return JsonResponse({"error": f"Failed to convert TIFF: {exc}"}, status=400)
