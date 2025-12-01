import datetime
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
    
    encounter_count = serializers.IntegerField(read_only=True)
    record_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Subject
        fields = '__all__'

class EncounterSerializer(serializers.ModelSerializer):
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

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if instance.procedure_occurrence_age:
            # Convert duration to years (approx)
            days = instance.procedure_occurrence_age.days
            ret['age_at_encounter'] = round(days / 365.25, 2)
        else:
            ret['age_at_encounter'] = None
        return ret

    def create(self, validated_data):
        age = validated_data.pop('age_at_encounter', None)
        if age is not None:
            validated_data['procedure_occurrence_age'] = datetime.timedelta(days=age * 365.25)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        age = validated_data.pop('age_at_encounter', None)
        if age is not None:
            validated_data['procedure_occurrence_age'] = datetime.timedelta(days=age * 365.25)
        return super().update(instance, validated_data)

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

class RecordUploadSerializer(serializers.ModelSerializer):
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
    
    operator = serializers.CharField(required=False, write_only=True)
    acquisition_date = serializers.DateField(required=False, write_only=True)
    notes = serializers.CharField(required=False, write_only=True)
    
    class Meta:
        model = Record
        fields = ['id', 'file', 'record_type', 'orientation', 'modality', 'operator', 'acquisition_date', 'notes']

    def to_representation(self, instance):
        return RecordSerializer(instance, context=self.context).data

    def validate_file(self, value):
        if value.size > 100 * 1024 * 1024:
            raise serializers.ValidationError("File too large (max 100MB)")
        
        initial_pos = value.tell()
        value.seek(0)
        
        if magic:
            try:
                mime = magic.from_buffer(value.read(2048), mime=True)
            except Exception:
                # Fallback if magic fails
                mime = 'application/octet-stream'
        else:
            mime = 'application/octet-stream'
            
        value.seek(initial_pos)
        
        ext = value.name.split('.')[-1].lower()
        if ext not in ['png', 'stl']:
            raise serializers.ValidationError("Only PNG and STL files are allowed")
        
        return value

    def create(self, validated_data):
        file_obj = validated_data.pop('file')
        
        # These are now Coding objects, not strings!
        rt_coding = validated_data.pop('record_type')
        view_coding = validated_data.pop('orientation') # Maps to 'view'
        mod_coding = validated_data.pop('modality')     # Maps to 'series_modality'
        
        operator_name = validated_data.pop('operator', None)
        acquisition_date = validated_data.pop('acquisition_date', datetime.date.today())
        notes = validated_data.pop('notes', '')
        
        encounter = self.context['encounter']
        
        # Try to get user from request
        request = self.context.get('request')
        scan_operator = None
        if request and request.user.is_authenticated:
            scan_operator = request.user
        
        with transaction.atomic():
            # Determine collection (fallback to first available or create default)
            collection = Collection.objects.first()
            if not collection:
                # Should not happen if initialized, but handle it
                raise serializers.ValidationError("No collection available")

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
                collection=collection,
                record_type=rt_coding,
                imaging_study=study
            )
            
            return record
