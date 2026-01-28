"""
Serializers for the archive app.

This module defines the serializers for converting complex data types (models)
to and from native Python datatypes that can then be easily rendered into JSON, XML, or other content types.
It includes specialized logic for file uploads and validation.
"""
import datetime
from typing import Any, Dict, Optional
try:
    import magic
except ImportError:
    magic = None
from django.db import transaction
from rest_framework import serializers
from .models import (
    Coding, Identifier, Address, Collection, Subject, 
    Encounter, Location, ImagingStudy, Record
)
from .constants import (
    SYSTEM_RECORD_TYPE, SYSTEM_ORIENTATION, SYSTEM_MODALITY
)

class CodingSerializer(serializers.ModelSerializer):
    """Serializer for Coding model."""
    class Meta:
        model = Coding
        fields = '__all__'

class IdentifierSerializer(serializers.ModelSerializer):
    """Serializer for Identifier model."""
    class Meta:
        model = Identifier
        fields = '__all__'

class AddressSerializer(serializers.ModelSerializer):
    """Serializer for Address model."""
    class Meta:
        model = Address
        fields = '__all__'

class LocationSerializer(serializers.ModelSerializer):
    """Serializer for Location model."""
    address = AddressSerializer(read_only=True)
    
    class Meta:
        model = Location
        fields = '__all__'

class CollectionSerializer(serializers.ModelSerializer):
    """Serializer for Collection model."""
    address = AddressSerializer(read_only=True)
    
    class Meta:
        model = Collection
        fields = '__all__'

class SubjectSerializer(serializers.ModelSerializer):
    """Serializer for Subject model."""
    address = AddressSerializer(read_only=True)
    identifiers = IdentifierSerializer(many=True, read_only=True)
    ethnicity = CodingSerializer(read_only=True)
    skeletal_pattern = CodingSerializer(read_only=True)
    palatal_cleft = CodingSerializer(read_only=True)
    collection = serializers.SlugRelatedField(
        slug_field='short_name',
        queryset=Collection.objects.all(),
        allow_null=True,
        required=False
    )
    
    encounter_count = serializers.IntegerField(read_only=True)
    record_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Subject
        fields = '__all__'

class EncounterSerializer(serializers.ModelSerializer):
    """Serializer for Encounter model."""
    diagnosis = CodingSerializer(read_only=True)
    procedure_code = serializers.PrimaryKeyRelatedField(queryset=Coding.objects.all())
    age_at_encounter = serializers.FloatField(required=False)
    subject = serializers.PrimaryKeyRelatedField(queryset=Subject.objects.all(), required=False)
    
    class Meta:
        model = Encounter
        fields = '__all__'
        extra_kwargs = {
            'procedure_occurrence_age': {'write_only': True}
        }

    def to_representation(self, instance: Encounter) -> Dict[str, Any]:
        """Convert instance to dictionary representation."""
        ret = super().to_representation(instance)
        if instance.procedure_occurrence_age:
            # Convert duration to years (approx)
            days = instance.procedure_occurrence_age.days
            ret['age_at_encounter'] = round(days / 365.25, 2)
        else:
            ret['age_at_encounter'] = None
        return ret

    def create(self, validated_data: Dict[str, Any]) -> Encounter:
        """Create a new Encounter instance."""
        age = validated_data.pop('age_at_encounter', None)
        if age is not None:
            validated_data['procedure_occurrence_age'] = datetime.timedelta(days=age * 365.25)
        return super().create(validated_data)

    def update(self, instance: Encounter, validated_data: Dict[str, Any]) -> Encounter:
        """Update an existing Encounter instance."""
        age = validated_data.pop('age_at_encounter', None)
        if age is not None:
            validated_data['procedure_occurrence_age'] = datetime.timedelta(days=age * 365.25)
        return super().update(instance, validated_data)

class ImagingStudySerializer(serializers.ModelSerializer):
    """Serializer for ImagingStudy model."""
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
    """Serializer for Record model."""
    identifiers = IdentifierSerializer(many=True, read_only=True)
    record_type = CodingSerializer(read_only=True)
    physical_location = AddressSerializer(read_only=True)
    
    class Meta:
        model = Record
        fields = '__all__'

class RecordUploadSerializer(serializers.ModelSerializer):
    """
    Serializer for uploading records with files.
    
    Handles file validation, metadata extraction, and creation of related
    ImagingStudy and Record objects within a transaction.
    """
    file = serializers.FileField(write_only=True)
    
    # Use SlugRelatedField for idiomatic lookup by 'code'
    record_type = serializers.SlugRelatedField(
        slug_field='code',
        queryset=Coding.objects.filter(system=SYSTEM_RECORD_TYPE),
        write_only=True
    )
    orientation = serializers.SlugRelatedField(
        slug_field='code',
        queryset=Coding.objects.filter(system=SYSTEM_ORIENTATION),
        write_only=True
    )
    modality = serializers.SlugRelatedField(
        slug_field='code',
        queryset=Coding.objects.filter(system=SYSTEM_MODALITY),
        write_only=True
    )
    
    acquisition_date = serializers.DateField(required=False, write_only=True)
    
    # Allow encounter to be passed in body (for flat endpoint) or context (for nested)
    encounter = serializers.PrimaryKeyRelatedField(
        queryset=Encounter.objects.all(),
        required=False,
        write_only=True
    )
    
    class Meta:
        model = Record
        fields = ['id', 'file', 'record_type', 'orientation', 'modality', 'acquisition_date', 'encounter']

    def to_representation(self, instance: Record) -> Dict[str, Any]:
        """Use standard RecordSerializer for response."""
        return RecordSerializer(instance, context=self.context).data

    def validate_file(self, value: Any) -> Any:
        """Validate uploaded file size, extension, and MIME type."""
        if value.size > 100 * 1024 * 1024:
            raise serializers.ValidationError("File too large (max 100MB)")
        
        initial_pos = value.tell()
        value.seek(0)
        
        # Validate file extension
        ext = value.name.split('.')[-1].lower()
        if ext not in ['png', 'stl']:
            raise serializers.ValidationError("Only PNG and STL files are allowed")
        
        # Validate MIME type if python-magic is available
        if magic:
            try:
                mime = magic.from_buffer(value.read(2048), mime=True)
                
                # Validate MIME type matches extension
                if ext == 'png' and mime != 'image/png':
                    raise serializers.ValidationError(f"Invalid MIME type for PNG: {mime}")
                if ext == 'stl' and mime not in ['application/octet-stream', 'model/stl', 'text/plain']:
                    # STL can be binary (octet-stream/model/stl) or ASCII (text/plain)
                    raise serializers.ValidationError(f"Invalid MIME type for STL: {mime}")
                    
            except Exception as e:
                # If validation fails explicitly, re-raise
                if isinstance(e, serializers.ValidationError):
                    raise e
                # Otherwise ignore magic errors and trust extension
                pass
            
        value.seek(initial_pos)
        return value

    def create(self, validated_data: Dict[str, Any]) -> Record:
        """
        Create Record and associated ImagingStudy.
        
        Wraps creation in a transaction to ensure data integrity.
        """
        file_obj = validated_data.pop('file')
        
        # These are now Coding objects, not strings!
        rt_coding = validated_data.pop('record_type')
        view_coding = validated_data.pop('orientation') # Maps to 'view'
        mod_coding = validated_data.pop('modality')     # Maps to 'series_modality'
        
        acquisition_date = validated_data.pop('acquisition_date', datetime.date.today())
        
        # Resolve encounter: check body first, then context
        encounter = validated_data.pop('encounter', None)
        if not encounter:
            encounter = self.context.get('encounter')
            
        if not encounter:
            raise serializers.ValidationError({"encounter": "This field is required (either in URL or body)."})
        
        # Try to get user from request
        request = self.context.get('request')
        scan_operator = None
        if request and request.user.is_authenticated:
            scan_operator = request.user
        
        with transaction.atomic():
            subject = encounter.subject
            collection = getattr(subject, 'collection', None)
            if not collection:
                raise serializers.ValidationError({
                    "collection": f"Subject {subject.id} must be assigned to a collection before uploading records."
                })

            study = ImagingStudy.objects.create(
                encounter=encounter,
                collection=collection,
                record_type=rt_coding,
                view=view_coding,
                series_modality=mod_coding,
                scan_datetime=datetime.datetime.combine(acquisition_date, datetime.time.min),
                source_file=file_obj,
                scan_operator=scan_operator
            )
            
            record = Record.objects.create(
                encounter=encounter,
                record_type=rt_coding,
                imaging_study=study
            )
            
            return record
