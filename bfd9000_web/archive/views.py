from rest_framework import viewsets
from .models import (
    Coding, Identifier, Address, Collection, Subject, 
    Encounter, Location, ImagingStudy, Record
)
from .serializers import (
    CodingSerializer, IdentifierSerializer, AddressSerializer, 
    CollectionSerializer, SubjectSerializer, EncounterSerializer, 
    LocationSerializer, ImagingStudySerializer, RecordSerializer
)

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
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    filterset_fields = ['humanname_family', 'gender', 'birth_date']
    search_fields = ['humanname_family', 'humanname_given']

class EncounterViewSet(viewsets.ModelViewSet):
    queryset = Encounter.objects.all()
    serializer_class = EncounterSerializer
    filterset_fields = ['subject', 'actual_period_start']

class ImagingStudyViewSet(viewsets.ModelViewSet):
    queryset = ImagingStudy.objects.all()
    serializer_class = ImagingStudySerializer
    filterset_fields = ['encounter', 'collection', 'scan_datetime']

class RecordViewSet(viewsets.ModelViewSet):
    queryset = Record.objects.all()
    serializer_class = RecordSerializer
    filterset_fields = ['encounter', 'collection']
