"""
Views for the archive app.

This module defines the ViewSets for the API, handling CRUD operations
for subjects, encounters, records, and related medical entities.
It also includes custom actions for file serving and valueset retrieval.
"""
from typing import Any, Dict, List, Optional, Type
from rest_framework import viewsets, serializers
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes
from django.http import FileResponse, HttpResponse
from django.db.models import Count, QuerySet
import io
import os
from PIL import Image
from .models import (
    Coding, Identifier, Address, Collection, Subject,
    Encounter, Location, ImagingStudy, Record
)
from .serializers import (
    CodingSerializer, IdentifierSerializer, AddressSerializer,
    CollectionSerializer, SubjectSerializer, EncounterSerializer,
    LocationSerializer, ImagingStudySerializer, RecordSerializer,
    RecordUploadSerializer
)
from .constants import (
    SYSTEM_RECORD_TYPE, SYSTEM_ORIENTATION, SYSTEM_MODALITY, SYSTEM_PROCEDURE
)

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
            data = [{'id': c.short_name, 'display': c.full_name} for c in colls]

        elif valueset_type == 'record_types':
            codings = Coding.objects.filter(system=SYSTEM_RECORD_TYPE)
            data = [{'id': c.code, 'display': c.display} for c in codings]

        elif valueset_type == 'orientations':
            codings = Coding.objects.filter(system=SYSTEM_ORIENTATION)
            data = [{'id': c.code, 'display': c.display} for c in codings]

        elif valueset_type == 'modalities':
            codings = Coding.objects.filter(system=SYSTEM_MODALITY)
            data = [{'id': c.code, 'display': c.display} for c in codings]

        elif valueset_type == 'procedures':
            codings = Coding.objects.filter(system=SYSTEM_PROCEDURE)
            data = [{'id': c.code, 'display': c.display} for c in codings]

        else:
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
    queryset = Subject.objects.annotate(
        encounter_count=Count('encounters', distinct=True),
        record_count=Count('encounters__records', distinct=True)
    ).all()
    serializer_class = SubjectSerializer
    filterset_fields = {
        'identifiers__value': ['exact', 'icontains'],
        'gender': ['exact'],
        'ethnicity__code': ['exact'],
        'skeletal_pattern__code': ['exact'],
        'palatal_cleft__code': ['exact'],
        'collection__short_name': ['exact'],
    }
    search_fields = ['identifiers__value', 'humanname_family', 'humanname_given']

class EncounterViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Encounter model.

    Manages clinical encounters or visits.
    """
    queryset = Encounter.objects.all()
    serializer_class = EncounterSerializer
    filterset_fields = ['subject', 'actual_period_start']

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
                raise serializers.ValidationError({"subject": "This field is required."})

        # Calculate age_at_encounter if not provided
        if 'age_at_encounter' not in serializer.validated_data:
            encounter_date = serializer.validated_data.get('actual_period_start')

            if subject and subject.birth_date and encounter_date:
                # Calculate duration
                delta = encounter_date - subject.birth_date
                serializer.save(subject=subject, procedure_occurrence_age=delta)
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
    queryset = Record.objects.all()
    serializer_class = RecordSerializer
    filterset_fields = ['encounter', 'encounter__subject__collection', 'encounter__subject__collection__short_name']

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
        record = self.get_object()
        if not record.imaging_study or not record.imaging_study.source_file:
            return Response({"error": "No image file available"}, status=404)

        return FileResponse(record.imaging_study.source_file)

    @extend_schema(
        responses={
            (200, 'image/jpeg'): OpenApiTypes.BINARY
        }
    )
    @action(detail=True, methods=['get'])
    def thumbnail(self, request: Request, pk: Optional[int] = None, **kwargs: Any) -> Response:
        """Generate and serve a thumbnail for the record's image."""
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
            img = Image.new('RGB', (100, 100), color = (73, 109, 137))
            buf = io.BytesIO()
            img.save(buf, format='JPEG')
            buf.seek(0)
            return HttpResponse(buf, content_type='image/jpeg')

        try:
            # Open image using a context manager
            with Image.open(source_file) as img:
                # Use a separate variable for any processed version of the image
                processed_img = img

                # Convert to RGB if RGBA (PNG) or LA
                if img.mode in ('RGBA', 'LA'):
                    background = Image.new(img.mode[:-1], img.size, (255, 255, 255))
                    background.paste(img, img.split()[-1])
                    processed_img = background

                processed_img.thumbnail((300, 300))

                buf = io.BytesIO()
                processed_img.save(buf, format='JPEG')
                buf.seek(0)

                return HttpResponse(buf, content_type='image/jpeg')
        except Exception as e:
            return Response({"error": f"Error generating thumbnail: {e}"}, status=500)

    @action(detail=True, methods=['get'])
    def dicom(self, request: Request, pk: Optional[int] = None, **kwargs: Any) -> Response:
        """Serve the DICOM file (Not Implemented)."""
        # Not implemented yet
        return Response({"error": "DICOM download not implemented"}, status=404)
