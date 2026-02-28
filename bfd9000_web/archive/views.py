"""
Views for the archive app.

This module defines the ViewSets for the API, handling CRUD operations
for subjects, encounters, records, and related medical entities.
It also includes custom actions for file serving and valueset retrieval.
"""
import io
import os
from typing import Any, Dict, List, Optional, Type

from PIL import Image
from rest_framework import viewsets, serializers
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Count, QuerySet
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from .models import (
    Coding, Identifier, Address, Collection, Subject,
    Encounter, Location, ImagingStudy, Record, ValueSet
)
from .serializers import (
    CodingSerializer, IdentifierSerializer, AddressSerializer,
    CollectionSerializer, SubjectSerializer, EncounterSerializer,
    LocationSerializer, ImagingStudySerializer, RecordSerializer,
    RecordUploadSerializer
)
from .constants import (
    SYSTEM_IDENTIFIER_BOLTON_SUBJECT,
    SYSTEM_IDENTIFIER_LANCASTER_SUBJECT,
)

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
    """
    ViewSet for Subject model.

    Manages patient/subject information including demographics.
    """
    queryset = Subject.objects.prefetch_related(
        'identifiers'
    ).annotate(
        encounter_count=Count('encounters', distinct=True),
        record_count=Count('encounters__records', distinct=True)
    ).all()
    serializer_class = SubjectSerializer
    filterset_fields = {
        'identifiers__value',
        'gender',
        'ethnicity__code',
        'skeletal_pattern__code',
        'palatal_cleft__code',
        'collection__short_name',
    }
    search_fields = ['identifiers__value', 'pk',
                     'humanname_family', 'humanname_given']


class EncounterViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Encounter model.

    Manages clinical encounters or visits.
    """
    queryset = Encounter.objects.select_related(
        'subject'
    ).prefetch_related(
        'subject__identifiers'
    ).annotate(
        record_count=Count('records', distinct=True)
    ).order_by('-actual_period_start', '-id')
    serializer_class = EncounterSerializer
    filterset_fields = ['subject', 'actual_period_start']
    search_fields = ['subject__identifiers__value']

    def perform_create(self, serializer: serializers.ModelSerializer) -> None:
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
    queryset = ImagingStudy.objects.all()
    serializer_class = ImagingStudySerializer
    filterset_fields = ['encounter', 'collection', 'scan_datetime']


class RecordViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Record model.

    Manages the high-level record entries that link encounters to imaging studies.
    Supports file uploads via a specialized serializer.
    """
    queryset = Record.objects.select_related(
        'encounter', 'encounter__subject'
    ).prefetch_related(
        'encounter__subject__identifiers'
    )
    serializer_class = RecordSerializer
    filterset_fields = [
        'encounter__id',
        'encounter__subject',
        'encounter__subject__collection',
        'encounter__subject__collection__short_name',
        'encounter',
    ]
    search_fields = ['id', 'encounter__id', 'encounter__subject__id']

    def get_serializer_class(self) -> Type[serializers.Serializer]:
        """Return the appropriate serializer class based on the action."""
        if self.action == 'create':
            return RecordUploadSerializer
        return RecordSerializer

    def get_serializer_context(self) -> Dict[str, Any]:
        """Add extra context to the serializer."""
        context = super().get_serializer_context()
        if self.action == 'create':
            # If nested, get encounter
            encounter_pk = self.kwargs.get('encounter_pk')
            if encounter_pk:
                encounter = get_object_or_404(Encounter, pk=encounter_pk)
                context['encounter'] = encounter
        return context

    def get_queryset(self) -> QuerySet:
        """Filter queryset based on nested routes."""
        qs = super().get_queryset()
        # Filter by nested encounter if present
        encounter_pk = self.kwargs.get('encounter_pk')
        if encounter_pk:
            qs = qs.filter(encounter__id=encounter_pk)

        # Filter by nested subject if present
        subject_pk = self.kwargs.get('subject_pk')
        if subject_pk:
            qs = qs.filter(encounter__subject__id=subject_pk)

        return qs

    @extend_schema(
        responses={
            (200, 'application/octet-stream'): OpenApiTypes.BINARY
        }
    )
    @action(detail=True, methods=['get'])
    def image(self, request: Request, pk: Optional[int] = None, **kwargs: Any) -> Response:
        """Serve the raw image file associated with the record."""
        # DRF action signature requires request/pk/kwargs.
        del request, pk, kwargs
        record = self.get_object()
        if not record.imaging_study or not record.imaging_study.source_file:
            return Response({"error": "No image file available"}, status=404)

        source_file = record.imaging_study.source_file
        ext = os.path.splitext(source_file.name)[1].lower()
        transform_ops = record.image_transform_ops or []
        if ext in {'.tif', '.tiff'}:
            try:
                source_file.open('rb')
                png_bytes = _convert_tiff_to_png_bytes(source_file)
                if transform_ops:
                    with Image.open(io.BytesIO(png_bytes)) as img:
                        transformed = _apply_transform_ops(img, transform_ops)
                        out = io.BytesIO()
                        transformed.save(out, format='PNG', optimize=True)
                        png_bytes = out.getvalue()
                return HttpResponse(png_bytes, content_type='image/png')
            except Exception as e:  # pylint: disable=broad-exception-caught
                return Response({"error": f"Error converting TIFF: {e}"}, status=500)
            finally:
                source_file.close()

        if transform_ops and ext != '.stl':
            try:
                source_file.open('rb')
                with Image.open(source_file) as img:
                    transformed = _apply_transform_ops(img, transform_ops)
                    out = io.BytesIO()
                    transformed.save(out, format='PNG', optimize=True)
                    return HttpResponse(out.getvalue(), content_type='image/png')
            except Exception as e:  # pylint: disable=broad-exception-caught
                return Response({"error": f"Error transforming image: {e}"}, status=500)
            finally:
                source_file.close()

        return FileResponse(source_file)

    @extend_schema(
        responses={
            (200, 'image/jpeg'): OpenApiTypes.BINARY
        }
    )
    @action(detail=True, methods=['get'])
    def thumbnail(self, request: Request, pk: Optional[int] = None, **kwargs: Any) -> Response:
        """Generate and serve a thumbnail for the record's image."""
        # DRF action signature requires request/pk/kwargs.
        del request, pk, kwargs
        record = self.get_object()

        if not record.imaging_study or not record.imaging_study.source_file:
            return Response({"error": "No image file available"}, status=404)

        source_file = record.imaging_study.source_file
        # Check if file exists
        if not os.path.exists(source_file.path):
            return Response({"error": "File not found on server"}, status=404)

        ext = os.path.splitext(source_file.name)[1].lower()

        if ext == '.stl':
            # Return placeholder for STL
            img = Image.new('RGB', (100, 100), color=(73, 109, 137))
            buf = io.BytesIO()
            img.save(buf, format='JPEG')
            buf.seek(0)
            return HttpResponse(buf, content_type='image/jpeg')

        try:
            if ext in {'.tif', '.tiff'}:
                source_file.open('rb')
                png_bytes = _convert_tiff_to_png_bytes(source_file)
                source_file.close()
                image_stream = io.BytesIO(png_bytes)
            else:
                image_stream = source_file

            # Open image using a context manager
            with Image.open(image_stream) as img:
                # Use a separate variable for any processed version of the image
                processed_img = img

                if record.image_transform_ops:
                    processed_img = _apply_transform_ops(processed_img, record.image_transform_ops)

                # Convert to RGB if RGBA (PNG) or LA
                if processed_img.mode in ('RGBA', 'LA'):
                    background = Image.new(
                        processed_img.mode[:-1], processed_img.size, (255, 255, 255))
                    background.paste(processed_img, processed_img.split()[-1])
                    processed_img = background

                if processed_img.mode not in ('RGB', 'RGBA', 'LA', 'L'):
                    processed_img = processed_img.convert('RGB')

                processed_img.thumbnail((300, 300))

                buf = io.BytesIO()
                processed_img.save(buf, format='JPEG')
                buf.seek(0)

                return HttpResponse(buf, content_type='image/jpeg')
        except Exception as e:  # pylint: disable=broad-exception-caught
            return Response({"error": f"Error generating thumbnail: {e}"}, status=500)

    @action(detail=True, methods=['get'])
    def dicom(self, request: Request, pk: Optional[int] = None, **kwargs: Any) -> Response:
        """Serve the DICOM file (Not Implemented)."""
        # DRF action signature requires request/pk/kwargs.
        del request, pk, kwargs
        # Not implemented yet
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


def _get_bits_per_sample(img: Image.Image) -> Optional[int]:
    """Best-effort extraction of TIFF bits-per-sample."""
    tag_v2 = getattr(img, "tag_v2", None)
    if tag_v2 is None:
        return None

    bits = tag_v2.get(258)
    if bits is None:
        return None
    if isinstance(bits, tuple):
        return int(max(bits))
    return int(bits)


def _resize_image_for_preview(img: Image.Image, max_dim: int = 1024) -> Image.Image:
    """Resize while preserving aspect ratio for display/AI preview."""
    width, height = img.size
    largest = max(width, height)
    if largest <= max_dim:
        return img

    scale = max_dim / float(largest)
    new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
    resample = Image.Resampling.NEAREST if img.mode.startswith("I;16") else Image.Resampling.LANCZOS
    return img.resize(new_size, resample)


def _apply_transform_ops(img: Image.Image, ops: List[Dict[str, Any]]) -> Image.Image:
    """Apply ordered rotate/flip operations stored on Record."""
    transformed = img.copy()
    for op in ops:
        degrees = int(op.get('rotation', 0)) % 360
        if degrees:
            transformed = transformed.rotate(-degrees, expand=True)
        if bool(op.get('flip', False)):
            transformed = transformed.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    return transformed


def _convert_tiff_to_png_bytes(upload) -> bytes:
    """Convert TIFF to PNG, preserving 16-bit grayscale when needed."""
    with Image.open(upload) as img:
        bits_per_sample = _get_bits_per_sample(img)
        high_bit_gray = bits_per_sample in {12, 16} or img.mode in {"I;16", "I;16L", "I;16B"}

        if high_bit_gray:
            gray = img
            if gray.mode == "I;16B":
                gray = gray.convert("I")
            elif gray.mode not in {"I;16", "I;16L", "I"}:
                gray = gray.convert("I")

            if bits_per_sample == 12:
                if gray.mode != "I":
                    gray = gray.convert("I")

            png_image = gray.convert("I;16")
            png_image = _resize_image_for_preview(png_image)
        else:
            png_image = _resize_image_for_preview(img.convert("RGB"))

        buf = io.BytesIO()
        png_image.save(buf, format="PNG", optimize=True)
        return buf.getvalue()


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
        png_bytes = _convert_tiff_to_png_bytes(upload)
        return HttpResponse(png_bytes, content_type="image/png")
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return JsonResponse({"error": f"Failed to convert TIFF: {exc}"}, status=400)
