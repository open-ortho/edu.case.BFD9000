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


def imaging_study_upload_path(instance, filename: str) -> str:
    """
    Generate a structured upload path for imaging study files.

    Format: uploads/{collection}/{subject_id}/{encounter_id}/YYYYMMDD_HHMMSS_{record_type}.{ext}

    Args:
        instance: ImagingStudy instance
        filename: Original filename

    Returns:
        Structured path string
    """
    ext = os.path.splitext(filename)[1].lower()
    collection_name = instance.collection.short_name if instance.collection else 'unknown'
    subject_id = instance.encounter.subject.id if instance.encounter else 'unknown'
    encounter_id = instance.encounter.id if instance.encounter else 'unknown'
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    record_type = instance.record_type.code if instance.record_type else 'unknown'
    new_filename = f"{timestamp}_{record_type}{ext}"
    return os.path.join('uploads', collection_name, str(subject_id), str(encounter_id), new_filename)


class TimestampedModel(models.Model):
    """Abstract base class with timestamps and user tracking"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
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
        abstract = True


class Coding(TimestampedModel):
    """Normalized coding table, FHIR-style"""
    system = models.URLField(max_length=255, help_text="Code system URL")
    version = models.CharField(max_length=64, blank=True)
    code = models.CharField(max_length=128)
    display = models.CharField(max_length=255, blank=True)
    meaning = models.TextField(blank=True, help_text="Extended description")

    class Meta:
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
    slug = models.SlugField(max_length=128, unique=True)
    url = models.URLField(max_length=255, unique=True, help_text="Canonical URL")
    name = models.CharField(max_length=255)
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    version = models.CharField(max_length=64, blank=True)
    status = models.CharField(max_length=32, blank=True)
    publisher = models.CharField(max_length=255, blank=True)
    publication_url = models.URLField(max_length=255, blank=True)
    code_system_url = models.URLField(max_length=255, blank=True)
    code_system_publication_url = models.URLField(max_length=255, blank=True)
    code_system_status = models.CharField(max_length=32, blank=True)

    # NOTE: We use an explicit through model (ValueSetConcept) so we can
    # capture timestamps and enforce uniqueness at the join level. This means
    # Django will not auto-create join rows unless we insert them ourselves
    # (e.g., in migrations or via ValueSetConcept.objects.create()).
    codings = models.ManyToManyField(
        Coding,
        through='ValueSetConcept',
        related_name='value_sets',
        blank=True,
    )

    class Meta:
        ordering = ['slug']
        indexes = [
            models.Index(fields=['slug']),
        ]

    def __str__(self):
        return self.slug


class ValueSetConcept(TimestampedModel):
    """Join table connecting ValueSets to Codings."""
    valueset = models.ForeignKey(ValueSet, on_delete=models.CASCADE)
    coding = models.ForeignKey(Coding, on_delete=models.CASCADE)

    class Meta:
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
        max_length=16, choices=USE_CHOICES, default='official')
    system = models.URLField(max_length=255, help_text="Identifier system URL")
    value = models.CharField(max_length=128)

    class Meta:
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
    use = models.CharField(max_length=16, blank=True)
    type = models.CharField(max_length=16, blank=True)
    line1 = models.CharField(max_length=255, blank=True)
    line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=128, blank=True)
    district = models.CharField(max_length=128, blank=True)
    state = models.CharField(max_length=128, blank=True)
    postal_code = models.CharField(max_length=32, blank=True)
    country = models.CharField(
        max_length=2, blank=True, help_text="ISO 3166-1 alpha-2 country code")

    class Meta:
        verbose_name_plural = "Addresses"
        ordering = ['country', 'city']

    def __str__(self):
        parts = [self.line1, self.city, self.state, self.country]
        return ", ".join(filter(None, parts)) or "Empty Address"


class Collection(TimestampedModel):
    """Dataset container (e.g., Bolton, Brush, ...)"""
    short_name = models.CharField(max_length=64, unique=True)
    full_name = models.CharField(max_length=255)
    curator = models.CharField(max_length=255, blank=True)
    institution = models.CharField(max_length=255, blank=True)
    address = models.ForeignKey(
        Address, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField(blank=True)
    start_date = models.DateField(
        null=True, blank=True, help_text="Collection start date")
    end_date = models.DateField(
        null=True, blank=True, help_text="Collection end date")

    class Meta:
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

    gender = models.CharField(max_length=16, choices=GENDER_CHOICES)
    birth_date = models.DateField()
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
        Identifier, blank=True, related_name='subjects')
    collection = models.ForeignKey(
        Collection,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='subjects'
    )

    class Meta:
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
        if self.collection_id:
            return Collection.objects.filter(pk=self.collection_id)
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
        related_name='encounters'
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
        related_name='encounters_diagnosis'
    )
    procedure_occurrence_age = models.DurationField(null=True, blank=True)
    procedure_occurrence_datetime = models.DateTimeField(null=True, blank=True)
    procedure_code = models.ForeignKey(
        Coding,
        on_delete=models.PROTECT,
        related_name='encounters_procedure'
    )

    class Meta:
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
    name = models.CharField(max_length=255)
    address = models.ForeignKey(
        Address, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class ImagingStudy(TimestampedModel):
    """Digital imaging study (subject derived from Encounter)"""
    encounter = models.ForeignKey(
        Encounter,
        on_delete=models.PROTECT,
        related_name='imaging_studies'
    )
    collection = models.ForeignKey(Collection, on_delete=models.PROTECT)
    scan_operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='imaging_studies'
    )
    scan_location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    identifiers = models.ManyToManyField(
        Identifier, blank=True, related_name='imaging_studies')

    # Main fields
    record_type = models.ForeignKey(
        Coding,
        on_delete=models.PROTECT,
        related_name='imaging_studies_record_type'
    )
    view = models.ForeignKey(
        Coding,
        on_delete=models.PROTECT,
        related_name='imaging_studies_view'
    )
    scan_datetime = models.DateTimeField(null=True, blank=True)
    device = models.CharField(max_length=255, blank=True)
    endpoint = models.URLField(
        max_length=500, blank=True, help_text="URL endpoint for imaging data")
    source_file = models.FileField(upload_to=imaging_study_upload_path,
                                   null=True, blank=True, help_text="Original uploaded file (PNG/STL)")
    body_site = models.ForeignKey(
        Coding,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='imaging_studies_body_site'
    )
    laterality = models.ForeignKey(
        Coding,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='imaging_studies_laterality'
    )

    # DICOM optional fields
    instance_uid = models.CharField(
        max_length=64, blank=True, help_text="DICOM Instance UID")
    instance_sop_class = models.CharField(
        max_length=64, blank=True, help_text="DICOM SOP Class")
    instance_number = models.PositiveIntegerField(null=True, blank=True)
    series_uid = models.CharField(
        max_length=64, blank=True, help_text="DICOM Series UID")
    series_modality = models.ForeignKey(
        Coding,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='imaging_studies_series_modality'
    )

    class Meta:
        verbose_name_plural = "Imaging Studies"
        ordering = ['-scan_datetime']
        indexes = [
            models.Index(fields=['encounter']),
            models.Index(fields=['series_uid']),
            models.Index(fields=['instance_uid']),
            models.Index(fields=['scan_datetime']),
        ]

    @property
    def subject(self):
        """Convenience property to get subject from encounter"""
        return self.encounter.subject

    @property
    def image_url(self):
        """Return local file URL if present, otherwise external endpoint"""
        if self.source_file:
            return self.source_file.url
        return self.endpoint

    def __str__(self):
        date_str = self.scan_datetime.strftime(
            '%Y-%m-%d') if self.scan_datetime else 'No date'
        return f"ImagingStudy for {self.subject} - {date_str}"


class Record(TimestampedModel):
    """Physical artifact record (subject derived from Encounter)"""
    encounter = models.ForeignKey(
        Encounter,
        on_delete=models.PROTECT,
        related_name='records'
    )
    record_type = models.ForeignKey(
        Coding,
        on_delete=models.PROTECT,
        related_name='records_record_type'
    )
    physical_location = models.ForeignKey(
        Address,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='records_physical_location'
    )
    imaging_study = models.OneToOneField(
        ImagingStudy,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='record'
    )
    identifiers = models.ManyToManyField(
        Identifier, blank=True, related_name='records')

    device = models.CharField(max_length=255, blank=True)
    physical_location_box = models.CharField(max_length=128, blank=True)
    physical_location_shelf = models.CharField(max_length=128, blank=True)
    physical_location_tray = models.CharField(max_length=128, blank=True)
    physical_location_compartment = models.CharField(
        max_length=128, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['encounter']),
        ]

    @property
    def subject(self):
        """Convenience property to get subject from encounter"""
        return self.encounter.subject

    def is_scanned(self):
        """Check if this record has been digitally scanned"""
        return self.imaging_study is not None

    def __str__(self):
        return f"Record for {self.subject} - {self.record_type}"
