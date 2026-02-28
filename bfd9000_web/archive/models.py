"""
Data models for the archive app.

This module defines the database schema for the BFD9000 system, including
core entities like Subject, Encounter, ImagingStudy, and Record, as well as
supporting entities like Coding, Identifier, and Collection.
"""
import os
from datetime import datetime
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError


def record_upload_path(instance, filename: str) -> str:
    """
    Generate a structured upload path for Record files.

    Format: uploads/{collection}/{subject_id}/{encounter_id}/YYYYMMDD_HHMMSS_{record_type}.{ext}

    Args:
        instance: Record instance
        filename: Original filename

    Returns:
        Structured path string
    """
    ext = os.path.splitext(filename)[1].lower()
    # Try to resolve collection/subject/encounter via the series -> imaging_study -> encounter chain
    collection_name = 'unknown'
    subject_id = 'unknown'
    encounter_id = 'unknown'
    record_type_code = 'unknown'

    try:
        study = instance.series.imaging_study
        collection_name = study.collection.short_name if study.collection else 'unknown'
        encounter = study.encounter
        if encounter:
            subject_id = getattr(encounter.subject, 'id', 'unknown')
            encounter_id = getattr(encounter, 'id', 'unknown')
        record_type_code = instance.series.record_type.code if instance.series and instance.series.record_type else 'unknown'
    except Exception:
        # Fall back to unknowns if the instance is not fully linked yet
        pass

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    new_filename = f"{timestamp}_{record_type_code}{ext}"
    return os.path.join('uploads', collection_name, str(subject_id), str(encounter_id), new_filename)


def imaging_study_upload_path(instance, filename: str) -> str:
    """
    Legacy upload path helper kept for historical migrations.

    Old migrations reference this symbol directly via archive.models.
    """
    ext = os.path.splitext(filename)[1].lower()
    collection_name = 'unknown'
    subject_id = 'unknown'
    encounter_id = 'unknown'
    try:
        collection_name = instance.collection.short_name if instance.collection else 'unknown'
        encounter = getattr(instance, 'encounter', None)
        if encounter:
            subject_id = getattr(encounter.subject, 'id', 'unknown')
            encounter_id = getattr(encounter, 'id', 'unknown')
    except Exception:
        pass

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    new_filename = f"{timestamp}_study{ext}"
    return os.path.join('uploads', collection_name, str(subject_id), str(encounter_id), new_filename)


def record_thumbnail_path(instance, filename: str) -> str:
    """
    Generate a structured path for generated thumbnails.

    Mirrors the same layout as record_upload_path but under 'thumbnails/'.
    """
    ext = os.path.splitext(filename)[1].lower() or '.jpg'
    ext = '.jpg'
    collection_name = 'unknown'
    subject_id = 'unknown'
    encounter_id = 'unknown'
    record_type_code = 'unknown'
    try:
        study = instance.series.imaging_study
        collection_name = study.collection.short_name if study.collection else 'unknown'
        encounter = study.encounter
        if encounter:
            subject_id = getattr(encounter.subject, 'id', 'unknown')
            encounter_id = getattr(encounter, 'id', 'unknown')
        record_type_code = instance.series.record_type.code if instance.series and instance.series.record_type else 'unknown'
    except Exception:
        pass
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    new_filename = f"{timestamp}_{record_type_code}{ext}"
    return os.path.join('thumbnails', collection_name, str(subject_id), str(encounter_id), new_filename)


class TimestampedModel(models.Model):
    """Abstract base class with timestamps and user tracking"""
    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp when this record was created")
    updated_at = models.DateTimeField(auto_now=True, help_text="Timestamp when this record was last updated")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_created',
        help_text="User who created this record"
    )
    modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_modified',
        help_text="User who last modified this record"
    )

    class Meta:
        """Model metadata."""
        abstract = True


class Coding(TimestampedModel):
    """Normalized coding table, FHIR-style"""
    system = models.URLField(max_length=255, help_text="Code system URL")
    version = models.CharField(max_length=64, blank=True, help_text="Code system version")
    code = models.CharField(max_length=128, help_text="Code value in the code system")
    display = models.CharField(max_length=255, blank=True, help_text="Human-readable label for this code")
    meaning = models.TextField(blank=True, help_text="Extended description")

    class Meta:
        """Model metadata."""
        constraints = [
            models.UniqueConstraint(
                fields=['system', 'version', 'code'],
                name='unique_coding_system_version_code'
            )
        ]
        indexes = [
            models.Index(fields=['system', 'code']),
        ]
        ordering = ['system', 'code']

    def __str__(self):
        return f"{self.system}#{self.code}" if self.code else self.system


class ValueSet(TimestampedModel):
    """FHIR-style value set grouping a curated list of codes."""
    slug = models.SlugField(max_length=128, unique=True, help_text="Internal stable key used by API queries")
    url = models.URLField(max_length=255, unique=True,
                          help_text="Canonical URL")
    name = models.CharField(max_length=255, help_text="Computable ValueSet name")
    title = models.CharField(max_length=255, blank=True, help_text="Human-readable ValueSet title")
    description = models.TextField(blank=True, help_text="Narrative description of this ValueSet")
    version = models.CharField(max_length=64, blank=True, help_text="Version string for this ValueSet")
    status = models.CharField(max_length=32, blank=True, help_text="Publication status (e.g., active, draft)")
    publisher = models.CharField(max_length=255, blank=True, help_text="Organization that publishes this ValueSet")
    publication_url = models.URLField(max_length=255, blank=True, help_text="Documentation URL for this ValueSet")
    code_system_url = models.URLField(max_length=255, blank=True, help_text="Canonical URL for the related code system")
    code_system_publication_url = models.URLField(max_length=255, blank=True, help_text="Documentation URL for the code system")
    code_system_status = models.CharField(max_length=32, blank=True, help_text="Status of the underlying code system")

    # NOTE: We use an explicit through model (ValueSetConcept) so we can
    # capture timestamps and enforce uniqueness at the join level. This means
    # Django will not auto-create join rows unless we insert them ourselves
    # (e.g., in migrations or via ValueSetConcept.objects.create()).
    codings = models.ManyToManyField(
        Coding,
        through='ValueSetConcept',
        related_name='value_sets',
        blank=True,
        help_text="Codes included in this ValueSet via ValueSetConcept links",
    )

    class Meta:
        """Model metadata."""
        ordering = ['slug']
        indexes = [
            models.Index(fields=['slug']),
        ]

    def __str__(self):
        return str(self.slug)


class ValueSetConcept(TimestampedModel):
    """Join table connecting ValueSets to Codings."""
    valueset = models.ForeignKey(ValueSet, on_delete=models.CASCADE)
    coding = models.ForeignKey(Coding, on_delete=models.CASCADE)

    class Meta:
        """Model metadata."""
        constraints = [
            models.UniqueConstraint(
                fields=['valueset', 'coding'],
                name='unique_valueset_coding'
            )
        ]
        indexes = [
            models.Index(fields=['valueset', 'coding']),
        ]

    def __str__(self):
        return f"{self.valueset.slug}: {self.coding}"


class Identifier(TimestampedModel):
    """Reusable identifiers for multiple resources"""

    USE_CHOICES = [
        ('usual', 'Usual'),
        ('official', 'Official'),
        ('temp', 'Temporary'),
        ('secondary', 'Secondary'),
        ('old', 'Old'),
    ]

    use = models.CharField(
        max_length=16, choices=USE_CHOICES, default='official', help_text="FHIR Identifier.use semantics")
    system = models.URLField(max_length=255, help_text="Identifier system URL")
    value = models.CharField(max_length=128, help_text="Identifier value in the given system")

    class Meta:
        """Model metadata."""
        constraints = [
            models.UniqueConstraint(
                fields=['system', 'value'],
                name='unique_identifier_system_value'
            )
        ]
        indexes = [
            models.Index(fields=['system', 'value']),
        ]
        ordering = ['system', 'value']

    def __str__(self):
        return f"{self.system}: {self.value}"


class Address(TimestampedModel):
    """Minimal address, FHIR-style"""
    use = models.CharField(max_length=16, blank=True, help_text="Address use (home, work, temp, etc.)")
    type = models.CharField(max_length=16, blank=True, help_text="Address type (postal, physical, both)")
    line1 = models.CharField(max_length=255, blank=True, help_text="Primary street address line")
    line2 = models.CharField(max_length=255, blank=True, help_text="Secondary street address line")
    city = models.CharField(max_length=128, blank=True, help_text="City or locality")
    district = models.CharField(max_length=128, blank=True, help_text="District or county")
    state = models.CharField(max_length=128, blank=True, help_text="State, province, or region")
    postal_code = models.CharField(max_length=32, blank=True, help_text="Postal or ZIP code")
    country = models.CharField(
        max_length=2, blank=True, help_text="ISO 3166-1 alpha-2 country code")

    class Meta:
        """Model metadata."""
        verbose_name_plural = "Addresses"
        ordering = ['country', 'city']

    def __str__(self):
        parts = [self.line1, self.city, self.state, self.country]
        return ", ".join(filter(None, parts)) or "Empty Address"


class Collection(TimestampedModel):
    """Dataset container (e.g., Bolton, Brush, ...)"""
    short_name = models.CharField(max_length=64, unique=True, help_text="Short unique collection key used in paths and filters")
    full_name = models.CharField(max_length=255, help_text="Human-readable collection name")
    curator = models.CharField(max_length=255, blank=True, help_text="Primary curator or maintainer of the collection")
    institution = models.CharField(max_length=255, blank=True, help_text="Institution responsible for the collection")
    address = models.ForeignKey(
        Address, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField(blank=True, help_text="Narrative description of collection scope")
    start_date = models.DateField(
        null=True, blank=True, help_text="Collection start date")
    end_date = models.DateField(
        null=True, blank=True, help_text="Collection end date")

    class Meta:
        """Model metadata."""
        ordering = ['short_name']
        indexes = [
            models.Index(fields=['short_name']),
        ]

    def clean(self):
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise ValidationError("End date must be after start date")

    def __str__(self):
        return f"{self.short_name} - {self.full_name}"


class Subject(TimestampedModel):
    """Patient/Subject"""

    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
        ('unknown', 'Unknown'),
    ]

    gender = models.CharField(max_length=16, choices=GENDER_CHOICES, help_text="Administrative sex/gender for the subject")
    birth_date = models.DateField(help_text="Subject date of birth")
    humanname_family = models.CharField(
        max_length=128, help_text="Family name", null=True, blank=True)
    humanname_given = models.CharField(
        max_length=128, help_text="Given name", null=True, blank=True)
    address = models.ForeignKey(
        Address, on_delete=models.SET_NULL, null=True, blank=True)
    ethnicity = models.ForeignKey(
        Coding,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='subjects_ethnicity'
    )
    skeletal_pattern = models.ForeignKey(
        Coding,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='subjects_skeletal_pattern'
    )
    palatal_cleft = models.ForeignKey(
        Coding,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='subjects_palatal_cleft'
    )
    identifiers = models.ManyToManyField(
        Identifier, blank=True, related_name='subjects', help_text="External identifiers associated with this subject")
    collection = models.ForeignKey(
        Collection,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='subjects'
    )

    class Meta:
        """Model metadata."""
        ordering = ['humanname_family', 'humanname_given']
        indexes = [
            models.Index(fields=['birth_date']),
            models.Index(fields=['humanname_family', 'humanname_given']),
        ]

    def clean(self):
        # Validation for required identifiers will be done at form level
        # and post-save signal to prevent empty M2M
        pass

    def get_collections(self):
        """Return the subject's assigned collection, if any"""
        if self.collection is not None:
            return Collection.objects.filter(pk=self.collection.pk)
        return Collection.objects.none()

    def __str__(self):
        return f"{self.humanname_family}, {self.humanname_given}"


class Encounter(TimestampedModel):
    """Visit/Contact"""
    DATE_PRECISION_CHOICES = [
        ("day", "Day"),
        ("month", "Month"),
        ("year", "Year"),
        ("unknown", "Unknown"),
    ]
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='encounters',
        help_text="Subject linked to this encounter"
    )
    actual_period_start = models.DateField(
        null=True, blank=True, help_text="Encounter start date")
    actual_period_start_raw = models.CharField(
        max_length=64,
        blank=True,
        help_text="Original encounter date token from import sources",
    )
    actual_period_start_precision = models.CharField(
        max_length=16,
        blank=True,
        choices=DATE_PRECISION_CHOICES,
        help_text="Precision of actual_period_start",
    )
    actual_period_start_uncertain = models.BooleanField(
        default=False,
        help_text="True when actual_period_start is inferred from partial data",
    )
    actual_period_end = models.DateField(
        null=True, blank=True, help_text="Encounter end date")
    diagnosis = models.ForeignKey(
        Coding,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='encounters_diagnosis',
        help_text="Optional diagnostic coding associated with this encounter"
    )
    procedure_occurrence_age = models.DurationField(null=True, blank=True, help_text="Age at procedure/encounter when supplied by source data")
    procedure_occurrence_datetime = models.DateTimeField(null=True, blank=True, help_text="Exact procedure occurrence datetime when known")
    procedure_code = models.ForeignKey(
        Coding,
        on_delete=models.PROTECT,
        related_name='encounters_procedure',
        help_text="Procedure coding describing the encounter type"
    )

    class Meta:
        """Model metadata."""
        ordering = ['-actual_period_start']
        indexes = [
            models.Index(fields=['subject', 'actual_period_start']),
        ]

    def clean(self):
        if self.actual_period_start and self.actual_period_end:
            if self.actual_period_end < self.actual_period_start:
                raise ValidationError(
                    "Encounter end date must be after start date")

    def __str__(self):
        date_str = self.actual_period_start.strftime(
            '%Y-%m-%d') if self.actual_period_start else 'No date'
        return f"Encounter for {self.subject} on {date_str}"


class Location(TimestampedModel):
    """Location/Facility for scans"""
    name = models.CharField(max_length=255, help_text="Name of facility or location")
    address = models.ForeignKey(
        Address, on_delete=models.SET_NULL, null=True, blank=True, help_text="Postal address for this location")

    class Meta:
        """Model metadata."""
        ordering = ['name']

    def __str__(self):
        return str(self.name)


class ImagingStudy(TimestampedModel):
    """
    Digital imaging study. One study is associated with a single clinical
    Encounter (OneToOne). Study groups multiple Series which in turn contain
    Records. See docs/data_model.md for details.
    """
    encounter = models.OneToOneField(
        Encounter,
        on_delete=models.PROTECT,
        related_name='imaging_study',
        help_text='The Encounter this ImagingStudy documents (one study per encounter)'
    )
    collection = models.ForeignKey(
        Collection,
        on_delete=models.PROTECT,
        help_text='Dataset/collection this study belongs to'
    )
    identifiers = models.ManyToManyField(
        Identifier, blank=True, related_name='imaging_studies', help_text="External identifiers for this imaging study")
    instance_uid = models.CharField(
        max_length=64, blank=True, help_text='DICOM Study Instance UID'
    )
    endpoint = models.URLField(
        max_length=500, blank=True, help_text='URL providing access to study-level data (DICOMweb, PACS, etc.)'
    )
    description = models.CharField(
        max_length=255, blank=True, help_text='Institution-generated human readable description of the study'
    )

    class Meta:
        verbose_name_plural = 'Imaging Studies'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['encounter']),
            models.Index(fields=['instance_uid']),
        ]

    def __str__(self):
        if self.instance_uid:
            return f"ImagingStudy {self.instance_uid}"
        return f"ImagingStudy for {self.encounter}"


class Series(TimestampedModel):
    """
    A grouping of Records within an ImagingStudy that share the same
    modality and clinical record_type. Corresponds to the DICOM Series.
    """
    imaging_study = models.ForeignKey(
        ImagingStudy,
        on_delete=models.PROTECT,
        related_name='series',
        help_text='The ImagingStudy this series belongs to'
    )
    uid = models.CharField(max_length=64, blank=True, help_text='DICOM Series Instance UID')
    record_type = models.ForeignKey(
        Coding,
        on_delete=models.PROTECT,
        related_name='series_record_type',
        help_text='SNOMED CT code identifying the clinical study type (e.g. Cephalogram, Dental model)'
    )
    modality = models.ForeignKey(
        Coding,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='series_modality',
        help_text='DICOM modality code for this series (e.g. RG, XC, M3D)'
    )
    acquisition_location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='series_acquisition_location',
        help_text='Physical or institutional location where this series was acquired/digitized'
    )
    description = models.CharField(max_length=255, blank=True, help_text='Short human-readable description of this series')

    class Meta:
        verbose_name_plural = 'Series'
        ordering = ['imaging_study', 'record_type']
        indexes = [models.Index(fields=['imaging_study'])]

    def __str__(self):
        return f"Series {self.uid or self.pk} ({self.record_type})"


class Record(TimestampedModel):
    """
    Physical or digital artifact instance. Corresponds to DICOM Instance.

    Each Record belongs to a Series. Records store file-level metadata,
    thumbnails, acquisition timestamps and operator information.
    """
    series = models.ForeignKey(
        Series,
        on_delete=models.PROTECT,
        related_name='records',
        help_text='The Series this record instance belongs to'
    )
    sop_instance_uid = models.CharField(
        max_length=64, blank=True, help_text='DICOM SOP Instance UID uniquely identifying this artifact instance'
    )
    acquisition_datetime = models.DateTimeField(
        null=True, blank=True, help_text='Date and time this artifact was acquired or scanned'
    )
    scan_operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='records_scanned',
        help_text='User who performed the scan or acquisition of this record'
    )
    source_file = models.FileField(
        upload_to=record_upload_path,
        null=True, blank=True,
        help_text='Raw uploaded file (PNG/TIFF/STL). Transient — may be deleted after archival.'
    )
    thumbnail = models.ImageField(
        upload_to=record_thumbnail_path,
        null=True, blank=True,
        help_text='Compressed preview image (<300KB JPEG).'
    )
    endpoint = models.URLField(
        max_length=500, blank=True,
        help_text='URL of the permanently archived virtual record (DICOMweb, Box, PACS, etc.)'
    )
    # Legacy/local image type coding
    image_type = models.ForeignKey(
        Coding,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='records_image_type',
        help_text='Legacy Bolton/Lancaster compound code encoding medium+view (e.g. L, SM). See docs/data_model.md.'
    )
    patient_orientation = models.CharField(
        max_length=16, blank=True, help_text='DICOM PatientOrientation (0020,0020), encoded as A\\F'
    )
    image_transform_ops = models.JSONField(
        default=list, blank=True, help_text='Ordered list of transform ops applied to preview image'
    )
    physical_location = models.ForeignKey(
        Address, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='records_physical_location',
        help_text='Physical location where physical artifact is stored (archive address)'
    )
    physical_location_box = models.CharField(max_length=128, blank=True, help_text='Box identifier in physical archive')
    physical_location_shelf = models.CharField(max_length=128, blank=True, help_text='Shelf identifier in physical archive')
    physical_location_tray = models.CharField(max_length=128, blank=True, help_text='Tray identifier in physical archive')
    physical_location_compartment = models.CharField(max_length=128, blank=True, help_text='Compartment identifier in physical archive')
    identifiers = models.ManyToManyField(Identifier, blank=True, related_name='records', help_text="External identifiers for this record instance")
    device = models.CharField(max_length=255, blank=True, help_text='Device used to capture this record')

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['series'])]

    @property
    def encounter(self):
        """Navigate to Encounter via Series → ImagingStudy → Encounter"""
        return self.series.imaging_study.encounter

    @property
    def subject(self):
        """Navigate to Subject via Series → ImagingStudy → Encounter → Subject"""
        return self.series.imaging_study.encounter.subject

    def __str__(self):
        return f"Record {self.pk} ({self.series.record_type if self.series else 'NoSeries'})"
