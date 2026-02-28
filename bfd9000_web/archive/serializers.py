"""
Serializers for the archive app.

This module defines the serializers for converting complex data types (models)
to and from native Python datatypes that can then be easily rendered into JSON, XML, or other content types.
It includes specialized logic for file uploads and validation.
"""
import datetime
import os
import importlib
import json
from typing import Any, Dict, Optional, cast
from io import BytesIO
from django.core.files.base import ContentFile
from PIL import Image
try:
    magic = importlib.import_module('magic')
except ImportError:
    magic = None
from django.db import transaction
from rest_framework import serializers
from .models import (
    Coding,
    Identifier,
    Address,
    Collection,
    Subject,
    Encounter,
    Location,
    ImagingStudy,
    Series,
    Record,
)
from .constants import (
    SYSTEM_ORIENTATION,
    SYSTEM_MODALITY,
    SYSTEM_RECORD_TYPE,
    SYSTEM_IDENTIFIER_BOLTON_SUBJECT,
    SYSTEM_IDENTIFIER_IMAGE_TYPE,
)


RECORD_TYPE_CODES = (
    '201456002',
    '268425006',
    '39714003',
    '1597004',
    '302189007',
)

LATERAL_IMAGE_TYPE_CODE = 'L'


def _encode_patient_orientation(value: Optional[list[str]]) -> str:
    if not value:
        return ''
    return '\\'.join(value)


def _decode_patient_orientation(value: str) -> list[str]:
    if not value:
        return []
    return [part for part in value.split('\\') if part]


def _get_preferred_identifier(identifiers) -> Optional[str]:
    official_identifier: Optional[str] = None
    bolton_identifier: Optional[str] = None
    first_identifier: Optional[str] = None

    for identifier in identifiers:
        if first_identifier is None:
            first_identifier = identifier.value
        if official_identifier is None and identifier.use == 'official':
            official_identifier = identifier.value
        if bolton_identifier is None and identifier.system == SYSTEM_IDENTIFIER_BOLTON_SUBJECT:
            bolton_identifier = identifier.value

    return official_identifier or bolton_identifier or first_identifier

class CodingSerializer(serializers.ModelSerializer):
    """Serializer for Coding model."""
    class Meta:
        """Serializer metadata."""
        model = Coding
        fields = '__all__'

class IdentifierSerializer(serializers.ModelSerializer):
    """Serializer for Identifier model."""
    class Meta:
        """Serializer metadata."""
        model = Identifier
        fields = '__all__'

class AddressSerializer(serializers.ModelSerializer):
    """Serializer for Address model."""
    class Meta:
        """Serializer metadata."""
        model = Address
        fields = '__all__'

class LocationSerializer(serializers.ModelSerializer):
    """Serializer for Location model."""
    address = AddressSerializer(read_only=True)

    class Meta:
        """Serializer metadata."""
        model = Location
        fields = '__all__'

class CollectionSerializer(serializers.ModelSerializer):
    """Serializer for Collection model."""
    address = AddressSerializer(read_only=True)

    class Meta:
        """Serializer metadata."""
        model = Collection
        fields = '__all__'


class SeriesSerializer(serializers.ModelSerializer):
    """Serializer for Series model."""
    record_type = CodingSerializer(read_only=True)
    modality = CodingSerializer(read_only=True)
    acquisition_location = LocationSerializer(read_only=True)

    class Meta:
        model = Series
        fields = '__all__'

class SubjectSerializer(serializers.ModelSerializer):
    """Serializer for Subject model."""
    address = AddressSerializer(read_only=True)
    identifiers = IdentifierSerializer(many=True, read_only=True)
    ethnicity = CodingSerializer(read_only=True)
    skeletal_pattern = CodingSerializer(read_only=True)
    palatal_cleft = CodingSerializer(read_only=True)
    subject_identifier = serializers.SerializerMethodField()
    identifier_value = serializers.CharField(write_only=True, required=False, allow_blank=True)
    identifier_system = serializers.CharField(write_only=True, required=False, allow_blank=True)
    collection = serializers.SlugRelatedField(
        slug_field='short_name',
        queryset=Collection.objects.all(),
        allow_null=True,
        required=False
    )

    encounter_count = serializers.IntegerField(read_only=True)
    record_count = serializers.IntegerField(read_only=True)

    class Meta:
        """Serializer metadata."""
        model = Subject
        fields = '__all__'

    def get_subject_identifier(self, obj: Subject) -> Optional[str]:
        """Return the preferred identifier for subject display."""
        return _get_preferred_identifier(obj.identifiers.all())

    def create(self, validated_data: Dict[str, Any]) -> Subject:
        identifier_value = validated_data.pop('identifier_value', '').strip()
        identifier_system = validated_data.pop('identifier_system', '').strip()

        if identifier_value and not identifier_system:
            raise serializers.ValidationError({
                'identifier_system': 'identifier_system is required when identifier_value is provided.'
            })

        subject = super().create(validated_data)

        if identifier_value:
            identifier, _ = Identifier.objects.get_or_create(
                system=identifier_system,
                value=identifier_value,
                defaults={'use': 'official'},
            )
            subject.identifiers.add(identifier)

        return subject

class EncounterSerializer(serializers.ModelSerializer):
    """Serializer for Encounter model."""
    diagnosis = CodingSerializer(read_only=True)
    procedure_code = serializers.PrimaryKeyRelatedField(queryset=Coding.objects.all())
    age_at_encounter = serializers.FloatField(required=False)
    subject = serializers.PrimaryKeyRelatedField(queryset=Subject.objects.all(), required=False)
    subject_identifier = serializers.SerializerMethodField()

    record_count = serializers.IntegerField(read_only=True)

    class Meta:
        """Serializer metadata."""
        model = Encounter
        fields = '__all__'
        extra_kwargs = {
            'procedure_occurrence_age': {'write_only': True}
        }

    def get_subject_identifier(self, obj: Encounter) -> Optional[str]:
        """Return the preferred identifier for the encounter subject."""
        subject = getattr(obj, 'subject', None)
        if not subject:
            return None
        return _get_preferred_identifier(subject.identifiers.all())

    def to_representation(self, instance: Encounter) -> Dict[str, Any]:
        """Convert instance to dictionary representation."""
        ret = super().to_representation(instance)
        subject = getattr(instance, 'subject', None)
        birth_date = getattr(subject, 'birth_date', None)
        if instance.procedure_occurrence_age:
            # Convert duration to years (approx)
            days = instance.procedure_occurrence_age.days
            ret['age_at_encounter'] = round(days / 365.25, 2)
        elif instance.actual_period_start and birth_date:
            days = (instance.actual_period_start - birth_date).days
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
    # Expose nested series under this study for read-only listing
    series = serializers.SerializerMethodField()
    scan_operator_username = serializers.SerializerMethodField()
    scan_operator_display = serializers.SerializerMethodField()

    class Meta:
        """Serializer metadata."""
        model = ImagingStudy
        fields = '__all__'

    def get_series(self, obj: ImagingStudy):
        # Return list of series summaries
        qs = obj.series.all().select_related('record_type', 'modality')
        from .serializers import SeriesSerializer  # local import to avoid cycle
        return SeriesSerializer(qs, many=True, context=self.context).data

    def _latest_operator(self, obj: ImagingStudy):
        record = (
            Record.objects
            .filter(series__imaging_study=obj, scan_operator__isnull=False)
            .select_related('scan_operator')
            .order_by('-created_at')
            .first()
        )
        return getattr(record, 'scan_operator', None)

    def get_scan_operator_username(self, obj: ImagingStudy) -> Optional[str]:
        operator = self._latest_operator(obj)
        return getattr(operator, 'username', None)

    def get_scan_operator_display(self, obj: ImagingStudy) -> Optional[str]:
        operator = self._latest_operator(obj)
        if not operator:
            return None
        full_name = operator.get_full_name().strip()
        if full_name:
            return f"{full_name} ({operator.username})"
        return operator.username

class RecordSerializer(serializers.ModelSerializer):
    """Serializer for Record model."""
    identifiers = IdentifierSerializer(many=True, read_only=True)
    # Expose series and related summary fields
    series_id = serializers.IntegerField(source='series.id', read_only=True)
    record_type = CodingSerializer(source='series.record_type', read_only=True)
    series_record_type = CodingSerializer(source='series.record_type', read_only=True)
    series_modality = CodingSerializer(source='series.modality', read_only=True)
    physical_location = AddressSerializer(read_only=True)

    # Add nested encounter and subject data
    encounter_id = serializers.IntegerField(source='series.imaging_study.encounter.id', read_only=True)
    encounter = serializers.IntegerField(source='series.imaging_study.encounter.id', read_only=True)
    imaging_study = serializers.IntegerField(source='series.imaging_study.id', read_only=True)
    subject_id = serializers.IntegerField(source='series.imaging_study.encounter.subject.id', read_only=True)
    subject_identifier = serializers.SerializerMethodField()
    encounter_date = serializers.DateField(source='series.imaging_study.encounter.actual_period_start', read_only=True)
    actual_period_start_precision = serializers.CharField(source='series.imaging_study.encounter.actual_period_start_precision', read_only=True)
    actual_period_start_uncertain = serializers.BooleanField(source='series.imaging_study.encounter.actual_period_start_uncertain', read_only=True)
    age_at_encounter = serializers.SerializerMethodField()
    patient_orientation = serializers.SerializerMethodField()

    # Add imaging study fields for display
    acquisition_datetime = serializers.DateTimeField(read_only=True)
    acquisition_date = serializers.SerializerMethodField()
    file_size = serializers.SerializerMethodField()
    image_type = CodingSerializer(read_only=True)
    thumbnail_url = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()

    class Meta:
        """Serializer metadata."""
        model = Record
        fields = '__all__'

    def get_age_at_encounter(self, obj):
        """Get age at encounter in years."""
        encounter = getattr(obj.series.imaging_study, 'encounter', None)
        subject = getattr(encounter, 'subject', None)
        birth_date = getattr(subject, 'birth_date', None)

        if encounter and encounter.procedure_occurrence_age:
            days = encounter.procedure_occurrence_age.days
            return round(days / 365.25, 2)
        if encounter and encounter.actual_period_start and birth_date:
            days = (encounter.actual_period_start - birth_date).days
            return round(days / 365.25, 2)
        return None

    def get_subject_identifier(self, obj: Record) -> Optional[str]:
        """Return the preferred identifier for the record's subject."""
        encounter = getattr(obj.series.imaging_study, 'encounter', None)
        subject = getattr(encounter, 'subject', None)
        if not subject:
            return None
        return _get_preferred_identifier(subject.identifiers.all())

    def get_acquisition_date(self, obj):
        # acquisition datetime now stored on Record itself
        acquisition_datetime = getattr(obj, 'acquisition_datetime', None)
        if not acquisition_datetime:
            return None
        return acquisition_datetime.date()

    def get_file_size(self, obj: Record) -> Optional[int]:
        if getattr(obj, 'source_file', None):
            try:
                return obj.source_file.size
            except Exception:
                return None
        return None

    def get_patient_orientation(self, obj: Record) -> list[str]:
        return _decode_patient_orientation(str(getattr(obj, 'patient_orientation', '') or ''))

    def get_thumbnail_url(self, obj: Record) -> Optional[str]:
        if getattr(obj, 'thumbnail', None):
            try:
                return obj.thumbnail.url
            except Exception:
                return None
        return None

    def get_image_url(self, obj: Record) -> Optional[str]:
        if getattr(obj, 'source_file', None):
            try:
                return obj.source_file.url
            except Exception:
                return None
        return getattr(obj, 'endpoint', None)

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
        queryset=Coding.objects.filter(system=SYSTEM_RECORD_TYPE, code__in=RECORD_TYPE_CODES),
        write_only=True
    )
    modality = serializers.SlugRelatedField(
        slug_field='code',
        queryset=Coding.objects.filter(system=SYSTEM_MODALITY),
        write_only=True
    )

    acquisition_date = serializers.DateField(required=False, write_only=True)
    image_type = serializers.SlugRelatedField(
        slug_field='code',
        queryset=Coding.objects.filter(system=SYSTEM_IDENTIFIER_IMAGE_TYPE),
        required=False,
        allow_null=True,
        write_only=True,
    )
    patient_orientation = serializers.ListField(
        child=serializers.CharField(max_length=1),
        min_length=2,
        max_length=2,
        required=False,
        write_only=True,
    )
    image_transform_ops = serializers.JSONField(required=False, write_only=True)

    # Allow encounter to be passed in body (for flat endpoint) or context (for nested)
    encounter = serializers.PrimaryKeyRelatedField(
        queryset=Encounter.objects.all(),
        required=False,
        write_only=True
    )

    class Meta:
        """Serializer metadata."""
        model = Record
        fields = [
            'id',
            'file',
            'record_type',
            'modality',
            'acquisition_date',
            'encounter',
            'image_type',
            'patient_orientation',
            'image_transform_ops',
        ]

    def validate_patient_orientation(self, value: Any) -> Any:
        valid = {'A', 'P', 'R', 'L', 'H', 'F'}
        upper = [str(v).upper() for v in value]
        if any(v not in valid for v in upper):
            raise serializers.ValidationError('patient_orientation values must be one of A, P, R, L, H, F')
        return upper

    def validate_image_transform_ops(self, value: Any) -> Any:
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError as exc:
                raise serializers.ValidationError('image_transform_ops must be valid JSON') from exc

        if not isinstance(value, list):
            raise serializers.ValidationError('image_transform_ops must be a list')

        normalized = []
        for op in value:
            if not isinstance(op, dict):
                raise serializers.ValidationError('each transform op must be an object')

            try:
                rotation = int(op.get('rotation', 0))
            except (TypeError, ValueError) as exc:
                raise serializers.ValidationError('rotation must be a number') from exc
            rotation = rotation % 360
            if rotation not in {0, 90, 180, 270}:
                raise serializers.ValidationError('rotation must be one of 0, 90, 180, 270')
            flip = bool(op.get('flip', False))
            normalized.append({'rotation': rotation, 'flip': flip})

        return normalized

    def to_representation(self, instance: Record) -> Dict[str, Any]:
        """Use standard RecordSerializer for response."""
        return cast(Dict[str, Any], RecordSerializer(instance, context=self.context).data)

    def validate_file(self, value: Any) -> Any:
        """Validate uploaded file size, extension, and MIME type."""
        if value.size > 100 * 1024 * 1024:
            raise serializers.ValidationError("File too large (max 100MB)")

        initial_pos = value.tell()
        value.seek(0)

        # Validate file extension
        ext = value.name.split('.')[-1].lower()
        if ext not in ['png', 'stl', 'tif', 'tiff']:
            raise serializers.ValidationError("Only PNG, TIFF, and STL files are allowed")

        # Validate MIME type if python-magic is available
        if magic:
            try:
                mime = magic.from_buffer(value.read(2048), mime=True)

                # Validate MIME type matches extension
                if ext == 'png' and mime != 'image/png':
                    raise serializers.ValidationError(f"Invalid MIME type for PNG: {mime}")
                if ext in ['tif', 'tiff'] and mime != 'image/tiff':
                    raise serializers.ValidationError(f"Invalid MIME type for TIFF: {mime}")
                if ext == 'stl' and mime not in ['application/octet-stream', 'model/stl', 'text/plain']:
                    # STL can be binary (octet-stream/model/stl) or ASCII (text/plain)
                    raise serializers.ValidationError(f"Invalid MIME type for STL: {mime}")

            except Exception as e:  # pylint: disable=broad-exception-caught
                # python-magic emits varied errors; fall back to extension-only validation.
                # If validation fails explicitly, re-raise
                if isinstance(e, serializers.ValidationError):
                    raise e
                # Otherwise ignore magic errors and trust extension
                pass
            finally:
                # Always reset file position after MIME inspection
                value.seek(initial_pos)
        else:
            # If magic is not available, reset position before returning
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
        mod_coding = validated_data.pop('modality')

        acquisition_date = validated_data.pop('acquisition_date', None)
        image_type = validated_data.pop('image_type', None)
        patient_orientation = validated_data.pop('patient_orientation', None)
        transform_ops = validated_data.pop('image_transform_ops', [])

        # Resolve encounter: check body first, then context
        encounter = validated_data.pop('encounter', None)
        if not encounter:
            encounter = self.context.get('encounter')

        if not encounter:
            raise serializers.ValidationError({"encounter": "This field is required (either in URL or body)."})

        # Try to get user from request
        request = self.context.get('request')
        scan_operator = None
        if request and getattr(request, 'user', None) and request.user.is_authenticated:
            scan_operator = request.user

        if patient_orientation is None and image_type and getattr(image_type, 'code', None) == LATERAL_IMAGE_TYPE_CODE:
            patient_orientation = ['A', 'F']

        with transaction.atomic():
            subject = encounter.subject
            collection = getattr(subject, 'collection', None)
            if not collection:
                raise serializers.ValidationError({
                    "collection": f"Subject {subject.id} must be assigned to a collection before uploading records."
                })

            # Get or create ImagingStudy for this encounter
            study, _ = ImagingStudy.objects.get_or_create(
                encounter=encounter,
                defaults={'collection': collection}
            )

            # Get or create Series within the study
            series, _ = Series.objects.get_or_create(
                imaging_study=study,
                record_type=rt_coding,
                modality=mod_coding,
            )

            # Create record instance first (without file fields)
            record = Record.objects.create(
                series=series,
                acquisition_datetime=(datetime.datetime.combine(acquisition_date, datetime.time.min, tzinfo=datetime.timezone.utc) if acquisition_date else None),
                scan_operator=scan_operator,
                image_type=image_type,
                patient_orientation=_encode_patient_orientation(patient_orientation),
                image_transform_ops=transform_ops,
            )

            # Save uploaded file to source_file
            # Use a stable filename
            ext = os.path.splitext(file_obj.name)[1].lower()
            filename = f"{record.id}{ext}"
            record.source_file.save(filename, file_obj, save=False)

            # Generate thumbnail (JPEG) from source file when possible
            try:
                file_stream = record.source_file.open('rb')
                try:
                    with Image.open(file_stream) as img:
                        # Convert tiff/large images to RGB preview
                        if img.mode not in ('RGB', 'RGBA'):
                            img = img.convert('RGB')
                        img.thumbnail((300, 300))
                        thumb_io = BytesIO()
                        img.save(thumb_io, format='JPEG', quality=85)
                        thumb_content = ContentFile(thumb_io.getvalue())
                        thumb_name = f"{record.id}.jpg"
                        record.thumbnail.save(thumb_name, thumb_content, save=False)
                finally:
                    file_stream.close()
            except Exception:
                # On failure, skip thumbnail generation
                pass

            record.save()

            return record
