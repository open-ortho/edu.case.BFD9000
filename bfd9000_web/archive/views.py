from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes
from django.http import FileResponse, HttpResponse
from django.db.models import Count
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
    SYSTEM_RECORD_TYPE, SYSTEM_ORIENTATION, SYSTEM_MODALITY
)

class ValuesetViewSet(viewsets.ViewSet):
    """
    API endpoint that allows valuesets to be viewed.
    """
    def list(self, request):
        valueset_type = request.query_params.get('type')
        if not valueset_type:
            return Response({"error": "Missing 'type' parameter"}, status=400)
        
        data = []
        
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
             
        else:
            return Response({"error": f"Unknown valueset type: {valueset_type}"}, status=404)
            
        return Response(data)

class CodingViewSet(viewsets.ModelViewSet):
    queryset = Coding.objects.all()
    serializer_class = CodingSerializer
    filterset_fields = ['system', 'code']

class IdentifierViewSet(viewsets.ModelViewSet):
    queryset = Identifier.objects.all()
    serializer_class = IdentifierSerializer
    filterset_fields = ['system', 'value', 'use']

class AddressViewSet(viewsets.ModelViewSet):
    queryset = Address.objects.all()
    serializer_class = AddressSerializer

class LocationViewSet(viewsets.ModelViewSet):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer

class CollectionViewSet(viewsets.ModelViewSet):
    queryset = Collection.objects.all()
    serializer_class = CollectionSerializer
    filterset_fields = ['short_name']

class SubjectViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.annotate(
        encounter_count=Count('encounters', distinct=True),
        record_count=Count('encounters__records', distinct=True)
    ).all()
    serializer_class = SubjectSerializer
    filterset_fields = {
        'identifiers__value': ['exact', 'icontains'],
        'humanname_family': ['exact', 'icontains'],
        'gender': ['exact'],
        'birth_date': ['exact'],
    }
    search_fields = ['humanname_family', 'humanname_given', 'identifiers__value']

class EncounterViewSet(viewsets.ModelViewSet):
    queryset = Encounter.objects.all()
    serializer_class = EncounterSerializer
    filterset_fields = ['subject', 'actual_period_start']

    def perform_create(self, serializer):
        subject = serializer.validated_data.get('subject')
        
        # If not in body, check URL
        if not subject:
            subject_pk = self.kwargs.get('subject_pk')
            if subject_pk:
                subject = Subject.objects.get(pk=subject_pk)
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
    queryset = ImagingStudy.objects.all()
    serializer_class = ImagingStudySerializer
    filterset_fields = ['encounter', 'collection', 'scan_datetime']

class RecordViewSet(viewsets.ModelViewSet):
    queryset = Record.objects.all()
    serializer_class = RecordSerializer
    filterset_fields = ['encounter', 'collection']

    def get_serializer_class(self):
        if self.action == 'create':
            return RecordUploadSerializer
        return RecordSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.action == 'create':
            # If nested, get encounter
            encounter_pk = self.kwargs.get('encounter_pk')
            if encounter_pk:
                try:
                    encounter = Encounter.objects.get(pk=encounter_pk)
                    context['encounter'] = encounter
                except Encounter.DoesNotExist:
                    raise NotFound("Encounter not found")
        return context
        
    def get_queryset(self):
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
    def image(self, request, pk=None, **kwargs):
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
    def thumbnail(self, request, pk=None, **kwargs):
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
                # Convert to RGB if RGBA (PNG)
                if img.mode in ('RGBA', 'LA'):
                    background = Image.new(img.mode[:-1], img.size, (255, 255, 255))
                    background.paste(img, img.split()[-1])
                    img = background
                
                img.thumbnail((300, 300))
                
                buf = io.BytesIO()
                img.save(buf, format='JPEG')
                buf.seek(0)
                
                return HttpResponse(buf, content_type='image/jpeg')
        except Exception as e:
            return Response({"error": f"Error generating thumbnail: {e}"}, status=500)

    @action(detail=True, methods=['get'])
    def dicom(self, request, pk=None, **kwargs):
        # Not implemented yet
        return Response({"error": "DICOM download not implemented"}, status=404)
