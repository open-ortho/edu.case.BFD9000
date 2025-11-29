from rest_framework import serializers
from .models import (
    Coding, Identifier, Address, Collection, Subject, 
    Encounter, Location, ImagingStudy, Record
)

class CodingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coding
        fields = '__all__'

class IdentifierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Identifier
        fields = '__all__'

class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = '__all__'

class LocationSerializer(serializers.ModelSerializer):
    address = AddressSerializer(read_only=True)
    
    class Meta:
        model = Location
        fields = '__all__'

class CollectionSerializer(serializers.ModelSerializer):
    address = AddressSerializer(read_only=True)
    
    class Meta:
        model = Collection
        fields = '__all__'

class SubjectSerializer(serializers.ModelSerializer):
    address = AddressSerializer(read_only=True)
    identifiers = IdentifierSerializer(many=True, read_only=True)
    ethnicity = CodingSerializer(read_only=True)
    skeletal_pattern = CodingSerializer(read_only=True)
    palatal_cleft = CodingSerializer(read_only=True)
    
    class Meta:
        model = Subject
        fields = '__all__'

class EncounterSerializer(serializers.ModelSerializer):
    diagnosis = CodingSerializer(read_only=True)
    procedure_code = CodingSerializer(read_only=True)
    
    class Meta:
        model = Encounter
        fields = '__all__'

class ImagingStudySerializer(serializers.ModelSerializer):
    identifiers = IdentifierSerializer(many=True, read_only=True)
    record_type = CodingSerializer(read_only=True)
    view = CodingSerializer(read_only=True)
    body_site = CodingSerializer(read_only=True)
    laterality = CodingSerializer(read_only=True)
    series_modality = CodingSerializer(read_only=True)
    scan_location = LocationSerializer(read_only=True)
    
    class Meta:
        model = ImagingStudy
        fields = '__all__'

class RecordSerializer(serializers.ModelSerializer):
    identifiers = IdentifierSerializer(many=True, read_only=True)
    record_type = CodingSerializer(read_only=True)
    physical_location = AddressSerializer(read_only=True)
    
    class Meta:
        model = Record
        fields = '__all__'
