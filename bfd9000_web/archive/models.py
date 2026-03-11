"""
Data models for the archive app.

This module defines the database schema for the BFD9000 system, including
core entities like Subject, Encounter, ImagingStudy, and Record, as well as
supporting entities like Coding, Identifier, and Collection.
"""
import json
from typing import Any, Optional

from cryptography.fernet import Fernet, InvalidToken
from django.db import models
from django.db.models import Max
from .media_utils import generate_dicom_uid
from django.db.models import QuerySet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError

from .constants import (
    STUDYINSTANCEUID_ROOT,
    SERIESINSTANCEUID_ROOT,
    SOPINSTANCEUID_ROOT,
    SYSTEM_IDENTIFIER_BOLTON_SUBJECT,
    SYSTEM_IDENTIFIER_BOLTON_RECORD,
)


def _get_preferred_subject_identifier(identifiers) -> Optional[str]:
    """Return the preferred subject identifier value: official first, then Bolton system, then first available."""
    official: Optional[str] = None
    bolton: Optional[str] = None
    first: Optional[str] = None
    for ident in identifiers:
        if first is None:
            first = ident.value
        if official is None and ident.use == 'official':
            official = ident.value
        if bolton is None and ident.system == SYSTEM_IDENTIFIER_BOLTON_SUBJECT:
            bolton = ident.value
    return official or bolton or first


def compute_bolton_record_id(
    subject_identifiers,
    record_type_code: Optional[str],
    gender: str,
    age_years: Optional[float],
    sequence_number: Optional[int],
) -> str:
    """
    Compute the Bolton-style record identifier string.

    Schema: <subject_identifier><record_type_code><sex_code><age><seq>
    Example: R001LM08y06m01

    Returns empty string if subject_identifier or record_type_code is missing.
    """
    subject_identifier: Optional[str] = _get_preferred_subject_identifier(subject_identifiers)
    if not subject_identifier or not record_type_code:
        return ''
    sex_map: dict[str, str] = {'male': 'M', 'female': 'F', 'other': 'O', 'unknown': 'U'}
    sex: str = sex_map.get(gender, 'U')
    if age_years is not None:
        total_months: int = int(round(age_years * 12))
        years: int = total_months // 12
        months: int = total_months % 12
        age_str: str = f"{years:02d}y{months:02d}m"
    else:
        age_str = ''
    seq: int = sequence_number or 1
    return f"{subject_identifier}{record_type_code}{sex}{age_str}{seq:02d}"


def _compute_age_years_from_encounter(encounter: 'Encounter', subject: 'Subject') -> Optional[float]:
    """Return age in decimal years for the given encounter+subject, or None if not computable."""
    import datetime as _dt
    birth_date = getattr(subject, 'birth_date', None)
    if getattr(encounter, 'procedure_occurrence_age', None):
        return round(encounter.procedure_occurrence_age.days / 365.25, 2)
    if encounter.actual_period_start and birth_date:
        # Guard: DateField values may be strings if the instance was not round-tripped
        # through the database (e.g. immediately after create() in tests).
        start = encounter.actual_period_start
        bd = birth_date
        if isinstance(start, str):
            try:
                start = _dt.date.fromisoformat(start)
            except ValueError:
                return None
        if isinstance(bd, str):
            try:
                bd = _dt.date.fromisoformat(bd)
            except ValueError:
                return None
        return round((start - bd).days / 365.25, 2)
    return None


class TimestampedModel(models.Model):
    """Abstract base class with timestamps and user tracking"""
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="Timestamp when this record was created")
    updated_at = models.DateTimeField(
        auto_now=True, help_text="Timestamp when this record was last updated")
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
    version = models.CharField(
        max_length=64, blank=True, help_text="Code system version")
    code = models.CharField(
        max_length=128, help_text="Code value in the code system")
    display = models.CharField(
        max_length=255, blank=True, help_text="Human-readable label for this code")
    meaning = models.TextField(blank=True, help_text="Extended description")

    class Meta(TimestampedModel.Meta):
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

    def __str__(self) -> str:
        return f"[{self.code}] - {self.display or self.meaning or 'No display'}"


class ValueSet(TimestampedModel):
    """FHIR-style value set grouping a curated list of codes."""

    slug = models.SlugField(max_length=128, unique=True,
                            help_text="Internal stable key used by API queries")
    url = models.URLField(max_length=255, unique=True,
                          help_text="Canonical URL")
    name = models.CharField(
        max_length=255, help_text="Computable ValueSet name")
    title = models.CharField(max_length=255, blank=True,
                             help_text="Human-readable ValueSet title")
    description = models.TextField(
        blank=True, help_text="Narrative description of this ValueSet")
    version = models.CharField(
        max_length=64, blank=True, help_text="Version string for this ValueSet")
    status = models.CharField(
        max_length=32, blank=True, help_text="Publication status (e.g., active, draft)")
    publisher = models.CharField(
        max_length=255, blank=True, help_text="Organization that publishes this ValueSet")
    publication_url = models.URLField(
        max_length=255, blank=True, help_text="Documentation URL for this ValueSet")
    code_system_url = models.URLField(
        max_length=255, blank=True, help_text="Canonical URL for the related code system")
    code_system_publication_url = models.URLField(
        max_length=255, blank=True, help_text="Documentation URL for the code system")
    code_system_status = models.CharField(
        max_length=32, blank=True, help_text="Status of the underlying code system")

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

    class Meta(TimestampedModel.Meta):
        """Model metadata."""
        ordering = ['slug']
        indexes = [
            models.Index(fields=['slug']),
        ]

    def __str__(self) -> str:
        return str(self.slug)


class ValueSetConcept(TimestampedModel):
    """Join table connecting ValueSets to Codings."""

    valueset = models.ForeignKey(
        ValueSet, on_delete=models.CASCADE, help_text="ValueSet that includes the coding")
    coding = models.ForeignKey(
        Coding, on_delete=models.CASCADE, help_text="Coding member included in the ValueSet")

    class Meta(TimestampedModel.Meta):
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

    def __str__(self) -> str:
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
    value = models.CharField(
        max_length=128, help_text="Identifier value in the given system")

    class Meta(TimestampedModel.Meta):
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

    def __str__(self) -> str:
        return f"{self.system}: {self.value}"


class Address(TimestampedModel):
    """Minimal address, FHIR-style"""

    use = models.CharField(max_length=16, blank=True,
                           help_text="Address use (home, work, temp, etc.)")
    type = models.CharField(max_length=16, blank=True,
                            help_text="Address type (postal, physical, both)")
    line1 = models.CharField(max_length=255, blank=True,
                             help_text="Primary street address line")
    line2 = models.CharField(max_length=255, blank=True,
                             help_text="Secondary street address line")
    city = models.CharField(max_length=128, blank=True,
                            help_text="City or locality")
    district = models.CharField(
        max_length=128, blank=True, help_text="District or county")
    state = models.CharField(max_length=128, blank=True,
                             help_text="State, province, or region")
    postal_code = models.CharField(
        max_length=32, blank=True, help_text="Postal or ZIP code")
    country = models.CharField(
        max_length=2, blank=True, help_text="ISO 3166-1 alpha-2 country code")

    class Meta(TimestampedModel.Meta):
        """Model metadata."""
        verbose_name_plural = "Addresses"
        ordering = ['country', 'city']

    def __str__(self) -> str:
        parts = [self.line1, self.city, self.state, self.country]
        return ", ".join(filter(None, parts)) or "Empty Address"


class Collection(TimestampedModel):
    """ This model represents a collection of records, typically longitudinal
    datasets which where collected over a specific time period and/or by a
    specific institution and have a specific scope. For example a collection of
    subject with cleft palate, or twins.
    """
    short_name = models.CharField(
        max_length=64, unique=True, help_text="Short unique collection key used in paths and filters")
    full_name = models.CharField(
        max_length=255, help_text="Human-readable collection name")
    curator = models.CharField(
        max_length=255, blank=True, help_text="Primary curator or maintainer of the collection (an individual)")
    institution = models.CharField(
        max_length=255, blank=True, help_text="Institution responsible for the collection, associated with the curator")
    address = models.ForeignKey(
        Address, on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Address of the institution or physical location associated with this collection or its curator")
    description = models.TextField(
        blank=True, help_text="Narrative description of collection scope")
    start_date = models.DateField(
        null=True, blank=True, help_text="Date of the first record in this collection")
    end_date = models.DateField(
        null=True, blank=True, help_text="Date of the last record in this collection")

    class Meta(TimestampedModel.Meta):
        """Model metadata."""
        ordering = ['short_name']
        indexes = [
            models.Index(fields=['short_name']),
        ]

    def clean(self) -> None:
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise ValidationError("End date must be after start date")

    def __str__(self) -> str:
        return f"{self.short_name} - {self.full_name}"


class Subject(TimestampedModel):
    """Patient/Subject"""
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
        ('unknown', 'Unknown'),
    ]

    gender = models.CharField(
        max_length=16,
        choices=GENDER_CHOICES,
        help_text=(
            "Administrative gender for the subject. "
            "Values align with FHIR Patient.gender: "
            "https://hl7.org/fhir/patient-definitions.html#Patient.gender"
        ),
    )
    birth_date = models.DateField(help_text="Subject date of birth")
    humanname_family = models.CharField(
        max_length=128, help_text="Family name", null=True, blank=True)
    humanname_given = models.CharField(
        max_length=128, help_text="Given name", null=True, blank=True)
    address = models.ForeignKey(
        Address, on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Subject mailing or residence address")
    ethnicity = models.ForeignKey(
        Coding,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='subjects_ethnicity',
        help_text="Optional ethnicity coding for subject demographics"
    )
    skeletal_pattern = models.ForeignKey(
        Coding,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='subjects_skeletal_pattern',
        help_text="Optional skeletal pattern coding"
    )
    palatal_cleft = models.ForeignKey(
        Coding,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='subjects_palatal_cleft',
        help_text="Optional palatal cleft coding"
    )
    identifiers = models.ManyToManyField(
        Identifier, blank=True, related_name='subjects', help_text="External identifiers associated with this subject")
    collection = models.ForeignKey(
        Collection,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='subjects',
        help_text="Collection/dataset the subject belongs to"
    )
    notes = models.TextField(
        blank=True,
        default='',
        help_text='Free-text notes about this subject (e.g. archival condition notes)'
    )

    class Meta(TimestampedModel.Meta):
        """Model metadata."""
        # No default ordering: ordering by the preferred display identifier
        # requires annotation subqueries and is applied explicitly in SubjectViewSet.
        indexes = [
            models.Index(fields=['birth_date']),
            models.Index(fields=['humanname_family', 'humanname_given']),
        ]

    def clean(self) -> None:
        # Validation for required identifiers will be done at form level
        # and post-save signal to prevent empty M2M
        pass

    def get_collections(self) -> 'QuerySet[Collection]':
        """Return the subject's assigned collection, if any"""
        if self.collection is not None:
            return Collection.objects.filter(pk=self.collection.pk)
        return Collection.objects.none()

    def __str__(self) -> str:
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
    procedure_occurrence_age = models.DurationField(
        null=True, blank=True, help_text="Age at procedure/encounter when supplied by source data")
    procedure_code = models.ForeignKey(
        Coding,
        on_delete=models.PROTECT,
        related_name='encounters_procedure',
        help_text="Procedure coding describing the encounter type"
    )

    class Meta(TimestampedModel.Meta):
        """Model metadata."""
        ordering = ['-actual_period_start']
        indexes = [
            models.Index(fields=['subject', 'actual_period_start']),
        ]

    def clean(self) -> None:
        if self.actual_period_start and self.actual_period_end:
            if self.actual_period_end < self.actual_period_start:
                raise ValidationError(
                    "Encounter end date must be after start date")

    def __str__(self) -> str:
        date_str = self.actual_period_start.strftime(
            '%Y-%m-%d') if self.actual_period_start else 'No date'
        return f"Encounter for {self.subject} on {date_str}"


class Location(TimestampedModel):
    """Location/Facility for scans"""
    name = models.CharField(
        max_length=255, help_text="Name of facility or location")
    address = models.ForeignKey(
        Address, on_delete=models.SET_NULL, null=True, blank=True, help_text="Postal address for this location")

    class Meta(TimestampedModel.Meta):
        """Model metadata."""
        ordering = ['name']

    def __str__(self) -> str:
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
    # Intentionally aligned to the official DICOM keyword StudyInstanceUID.
    study_instance_uid = models.CharField(
        max_length=64, blank=True, help_text='DICOM StudyInstanceUID'
    )
    endpoint = models.URLField(
        max_length=500, blank=True, help_text='URL providing access to study-level data (DICOMweb, PACS, etc.)'
    )
    description = models.CharField(
        max_length=255, blank=True, help_text='Institution-generated human readable description of the study'
    )

    class Meta(TimestampedModel.Meta):
        """Model metadata."""
        verbose_name_plural = 'Imaging Studies'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['encounter']),
            models.Index(fields=['study_instance_uid']),
        ]

    def __str__(self) -> str:
        if self.study_instance_uid:
            return f"ImagingStudy {self.study_instance_uid}"
        return f"ImagingStudy for {self.encounter}"

    def save(self, *args, **kwargs) -> None:
        if not self.study_instance_uid:
            # DICOM StudyInstanceUID (official DICOM keyword)
            self.study_instance_uid = generate_dicom_uid(STUDYINSTANCEUID_ROOT)
        super().save(*args, **kwargs)


class Series(TimestampedModel):
    """
    A grouping of Records within an ImagingStudy that share the same
    modality and clinical record_type. Corresponds to the DICOM Series.
    See docs/data_model.md for field ownership and semantics.
    """
    imaging_study = models.ForeignKey(
        ImagingStudy,
        on_delete=models.PROTECT,
        related_name='series',
        help_text='The ImagingStudy this series belongs to'
    )
    # Intentionally aligned to the official DICOM keyword SeriesInstanceUID.
    series_instance_uid = models.CharField(max_length=64, blank=True,
                                           help_text='DICOM SeriesInstanceUID')

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
    description = models.CharField(
        max_length=255, blank=True, help_text='Short human-readable description of this series')

    class Meta(TimestampedModel.Meta):
        """Model metadata."""
        verbose_name_plural = 'Series'
        ordering = ['imaging_study']
        indexes = [models.Index(fields=['imaging_study'])]

    def __str__(self) -> str:
        return f"Series {self.series_instance_uid or self.pk}"

    def save(self, *args, **kwargs) -> None:
        if not self.series_instance_uid:
            # DICOM SeriesInstanceUID (official DICOM keyword)
            self.series_instance_uid = generate_dicom_uid(SERIESINSTANCEUID_ROOT)
        super().save(*args, **kwargs)


class Endpoint(TimestampedModel):
    """Configurable archive destination for one or more record copies."""

    class Status(models.TextChoices):
        ACTIVE = 'active', 'active'
        SUSPENDED = 'suspended', 'suspended'
        OFF = 'off', 'off'

    class ConnectionType(models.TextChoices):
        DICOM_STOW_RS = 'dicom-stow-rs', 'dicom-stow-rs'
        DICOM_DIMSE = 'dicom-dimse', 'dicom-dimse'
        SMB = 'smb', 'smb'
        BOX = 'box', 'box'
        DRIVE = 'drive', 'drive'
        FILE = 'file', 'file'
        OTHER = 'other', 'other'

    name = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    connection_type = models.CharField(max_length=32, choices=ConnectionType.choices)
    address = models.CharField(max_length=500, blank=True)
    config = models.JSONField(default=dict, blank=True)
    credentials_encrypted = models.TextField(blank=True)

    class Meta(TimestampedModel.Meta):
        ordering = ['name']
        indexes = [
            models.Index(fields=['status', 'connection_type']),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.connection_type})"

    def _get_fernet(self) -> Fernet:
        # ENDPOINT_CREDENTIALS_KEY must be set explicitly and separately from SECRET_KEY.
        # Sharing SECRET_KEY for encryption would enlarge the blast radius of a key compromise
        # (SECRET_KEY also protects sessions, CSRF tokens, and password reset links) and would
        # break all stored credentials silently if SECRET_KEY is rotated, with no migration path.
        configured_key = str(getattr(settings, 'ENDPOINT_CREDENTIALS_KEY', '') or '').strip()
        if not configured_key:
            raise ImproperlyConfigured(
                "ENDPOINT_CREDENTIALS_KEY must be set in settings. "
                "Do not reuse SECRET_KEY for credential encryption."
            )
        key_bytes = configured_key.encode('utf-8')
        return Fernet(key_bytes)

    def set_credentials(self, payload: dict[str, Any]) -> None:
        serialized = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        token = self._get_fernet().encrypt(serialized.encode('utf-8'))
        self.credentials_encrypted = token.decode('utf-8')

    def get_credentials(self) -> dict[str, Any]:
        if not self.credentials_encrypted:
            return {}
        try:
            plaintext = self._get_fernet().decrypt(self.credentials_encrypted.encode('utf-8'))
        except InvalidToken as exc:
            raise ValidationError('Endpoint credentials cannot be decrypted with current key') from exc

        data = json.loads(plaintext.decode('utf-8'))
        if not isinstance(data, dict):
            raise ValidationError('Endpoint credentials payload must be a JSON object')
        return data


class Device(TimestampedModel):
    """
    Physical device used for acquisition or digitization.
    Modeled after the FHIR Device resource.
    """
    serial_number = models.CharField(
        max_length=255, blank=True,
        help_text='Manufacturer-assigned serial number for this specific device unit (FHIR Device.serialNumber)'
    )
    display_name = models.CharField(
        max_length=255, help_text='Human-readable device name'
    )
    manufacturer = models.CharField(
        max_length=255, blank=True, help_text='Manufacturer name'
    )
    model_number = models.CharField(
        max_length=128, blank=True, help_text='Model number'
    )
    version = models.CharField(
        max_length=128, blank=True, help_text='Firmware or software version'
    )
    modalities = models.ManyToManyField(
        Coding,
        blank=True,
        related_name='devices',
        help_text='DICOM modality codes this device can produce'
    )
    identifiers = models.ManyToManyField(
        'Identifier',
        blank=True,
        related_name='devices',
        help_text='Institutional or business identifiers for this device (FHIR Device.identifier)',
    )

    class Meta(TimestampedModel.Meta):
        """Model metadata."""
        ordering = ['display_name']
        constraints = [
            models.UniqueConstraint(
                condition=models.Q(serial_number__gt=''),
                fields=('serial_number', 'manufacturer', 'model_number'),
                name='unique_device_serial_manufacturer_model',
            )
        ]

    def __str__(self) -> str:
        parts = [self.display_name]
        if self.manufacturer:
            parts.append(self.manufacturer)
        if self.model_number:
            parts.append(self.model_number)
        return ' — '.join(parts)


class PhysicalLocation(TimestampedModel):
    """
    A physical storage slot in an archive (e.g. a single compartment in a cabinet).

    Structured as cabinet / shelf / slot so that a single box string like
    ``1-A-16/17`` can be split into two rows sharing the same cabinet and shelf.
    A free-form ``raw`` field preserves the original box string for provenance.
    """
    address = models.ForeignKey(
        Address,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='physical_locations',
        help_text='Address of the building or facility where this storage slot is located',
    )
    cabinet = models.CharField(
        max_length=64, blank=True,
        help_text='Cabinet or box number within the facility (e.g. "1", "10")',
    )
    shelf = models.CharField(
        max_length=64, blank=True,
        help_text='Shelf identifier within the cabinet (e.g. "A", "B")',
    )
    slot = models.CharField(
        max_length=64, blank=True,
        help_text='Slot or compartment identifier on the shelf (e.g. "16", "30")',
    )
    raw = models.CharField(
        max_length=256, blank=True,
        help_text='Original unparsed location string from the source spreadsheet',
    )

    class Meta(TimestampedModel.Meta):
        """Model metadata."""
        ordering = ['cabinet', 'shelf', 'slot']
        indexes = [
            models.Index(fields=['cabinet', 'shelf', 'slot']),
        ]

    def __str__(self) -> str:
        parts = [p for p in [self.cabinet, self.shelf, self.slot] if p]
        label = '-'.join(parts) if parts else '(empty)'
        return f"PhysicalLocation {label}"


class PhysicalRecord(TimestampedModel):
    """
    The original physical artifact produced at an encounter: an acetate film,
    plaster model, paper chart, etc.

    Lives directly under Encounter — no DICOM UIDs, no Series FK.
    See docs/data_model.md for field ownership and semantics.
    """
    encounter = models.ForeignKey(
        Encounter,
        on_delete=models.PROTECT,
        related_name='physical_records',
        help_text='Encounter at which this physical artifact was produced'
    )
    record_type = models.ForeignKey(
        Coding,
        on_delete=models.PROTECT,
        related_name='physical_records_record_type',
        help_text='CWRU record type code identifying the clinical study type (e.g. L, SM)'
    )
    sequence_number = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text=(
            'One-based sequence within (encounter, record_type). '
            'Auto-assigned on first save. Used in identifier_str suffix.'
        ),
    )
    acquisition_datetime = models.DateTimeField(
        null=True, blank=True,
        help_text='When the original was acquired (X-ray taken, model cast, etc.)'
    )
    operator = models.CharField(
        max_length=255,
        blank=True,
        default='Unknown',
        help_text='Technician who operated the acquisition device. Defaults to "Unknown" for historical records.'
    )
    device = models.ForeignKey(
        'Device',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='physical_records',
        help_text='Device used to acquire the patient data (e.g. cephalostat)'
    )
    locations = models.ManyToManyField(
        PhysicalLocation,
        blank=True,
        related_name='physical_records',
        help_text='Physical archive storage slots where this artifact is held',
    )
    identifiers = models.ManyToManyField(
        Identifier,
        blank=True,
        related_name='physical_records',
        help_text='External identifiers for this physical artifact'
    )
    notes = models.TextField(
        blank=True,
        default='',
        help_text='Free-text notes about this physical artifact'
    )

    class Meta(TimestampedModel.Meta):
        """Model metadata."""
        ordering = ['-acquisition_datetime']
        indexes = [models.Index(fields=['encounter'])]

    @property
    def subject(self) -> 'Subject':
        """Navigate to Subject via Encounter."""
        return self.encounter.subject

    def __str__(self) -> str:
        return f"PhysicalRecord {self.pk} ({self.record_type})"

    @property
    def bolton_record_id(self) -> str:
        """Compute the Bolton-style record identifier for this physical record."""
        encounter = getattr(self, 'encounter', None)
        if not encounter:
            return ''
        subject = getattr(encounter, 'subject', None)
        if not subject:
            return ''
        age: Optional[float] = _compute_age_years_from_encounter(encounter, subject)
        rt_code: Optional[str] = self.record_type.code if self.record_type else None
        return compute_bolton_record_id(
            subject_identifiers=subject.identifiers.all(),
            record_type_code=rt_code,
            gender=subject.gender,
            age_years=age,
            sequence_number=self.sequence_number,
        )

    def save(self, *args: Any, **kwargs: Any) -> None:
        encounter_pk: Optional[int] = self.encounter_id  # type: ignore[attr-defined]
        record_type_pk: Optional[int] = self.record_type_id  # type: ignore[attr-defined]
        if self.sequence_number is None and encounter_pk and record_type_pk:
            max_seq: Optional[int] = PhysicalRecord.objects.filter(
                encounter_id=encounter_pk,
                record_type_id=record_type_pk,
            ).aggregate(m=Max('sequence_number'))['m']
            self.sequence_number = (max_seq or 0) + 1
        super().save(*args, **kwargs)
        self._assign_bolton_record_identifier()

    def _assign_bolton_record_identifier(self) -> None:
        """Create or update the stored Bolton record identifier on the M2M identifiers field."""
        new_value: str = self.bolton_record_id
        if not new_value:
            return
        existing = list(self.identifiers.filter(system=SYSTEM_IDENTIFIER_BOLTON_RECORD))
        official_existing = [i for i in existing if i.use == 'official']
        if official_existing and official_existing[0].value == new_value:
            # Already up to date
            return
        # Mark any existing official as old
        for old_ident in official_existing:
            old_ident.use = 'old'
            old_ident.save(update_fields=['use'])
        # Create or fetch new identifier
        new_ident, _ = Identifier.objects.get_or_create(
            system=SYSTEM_IDENTIFIER_BOLTON_RECORD,
            value=new_value,
            defaults={'use': 'official'},
        )
        if new_ident.use != 'official':
            new_ident.use = 'official'
            new_ident.save(update_fields=['use'])
        self.identifiers.add(new_ident)


class DigitalRecord(TimestampedModel):
    """
    One digital instance: either a digitization of a PhysicalRecord, or a
    born-digital acquisition with no physical counterpart.
    Corresponds to a DICOM SOP Instance.

    See docs/data_model.md for field ownership, constraints, and semantics.
    """
    physical_record = models.ForeignKey(
        PhysicalRecord,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='digital_records',
        help_text='Physical artifact this digital record was derived from. Null for born-digital records.'
    )
    series = models.ForeignKey(
        Series,
        on_delete=models.PROTECT,
        related_name='digital_records',
        help_text='Series this digital record belongs to (always required for DICOM grouping)'
    )
    # Intentionally aligned to the official DICOM keyword SOPInstanceUID.
    sop_instance_uid = models.CharField(
        max_length=64, blank=True,
        help_text='DICOM SOPInstanceUID uniquely identifying this digital instance'
    )
    record_type = models.ForeignKey(
        Coding,
        on_delete=models.PROTECT,
        related_name='digital_records_record_type',
        help_text=(
            'CWRU record type code (e.g. L, SM). '
            'Must match physical_record.record_type when physical_record is set.'
        )
    )
    acquisition_datetime = models.DateTimeField(
        null=True, blank=True,
        help_text='When the physical record was scanned, or when born-digital data was acquired'
    )
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='digital_records_operated',
        help_text='System user who performed the scan or born-digital acquisition'
    )
    source_file = models.FileField(
        upload_to='uploads/',
        null=True, blank=True,
        help_text='Raw uploaded file (PNG/TIFF/STL). Transient — may be deleted after archival.'
    )
    thumbnail = models.ImageField(
        upload_to='thumbnails/',
        null=True, blank=True,
        help_text='Compressed preview image (target 20 KB, hard limit 100 KB JPEG). Persists for browse UX.'
    )
    patient_orientation = models.CharField(
        max_length=16, blank=True,
        help_text='DICOM PatientOrientation (0020,0020), encoded as e.g. A\\F'
    )
    image_transform_ops = models.JSONField(
        default=list, blank=True,
        help_text='Ordered list of transform ops applied to the preview image'
    )
    device = models.ForeignKey(
        Device,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='digital_records',
        help_text='Device used to digitize the physical record, or to acquire born-digital data'
    )
    identifiers = models.ManyToManyField(
        Identifier,
        blank=True,
        related_name='digital_records',
        help_text='External identifiers for this digital instance'
    )
    sequence_number = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text=(
            'One-based sequence within (encounter, record_type) among DigitalRecords. '
            'Auto-assigned on first save. Used in identifier_str suffix.'
        ),
    )

    class Meta(TimestampedModel.Meta):
        """Model metadata."""
        ordering = ['-created_at']
        indexes = [models.Index(fields=['series'])]

    def clean(self) -> None:
        if self.physical_record is not None:
            if self.record_type != self.physical_record.record_type:
                raise ValidationError(
                    'DigitalRecord.record_type must match physical_record.record_type'
                )
            digital_encounter = self.series.imaging_study.encounter
            if digital_encounter != self.physical_record.encounter:
                raise ValidationError(
                    'DigitalRecord series encounter must match physical_record encounter'
                )

    @property
    def encounter(self) -> Encounter:
        """Navigate to Encounter via Series → ImagingStudy → Encounter."""
        return self.series.imaging_study.encounter

    @property
    def subject(self) -> Subject:
        """Navigate to Subject via Series → ImagingStudy → Encounter → Subject."""
        return self.series.imaging_study.encounter.subject

    def __str__(self) -> str:
        return f"DigitalRecord {self.pk} ({self.record_type})"

    @property
    def bolton_record_id(self) -> str:
        """Compute the Bolton-style record identifier for this digital record."""
        try:
            encounter = self.series.imaging_study.encounter
        except Exception:
            return ''
        subject = getattr(encounter, 'subject', None)
        if not subject:
            return ''
        age: Optional[float] = _compute_age_years_from_encounter(encounter, subject)
        rt_code: Optional[str] = self.record_type.code if self.record_type else None
        return compute_bolton_record_id(
            subject_identifiers=subject.identifiers.all(),
            record_type_code=rt_code,
            gender=subject.gender,
            age_years=age,
            sequence_number=self.sequence_number,
        )

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self.sop_instance_uid:
            self.sop_instance_uid = generate_dicom_uid(SOPINSTANCEUID_ROOT)
        if self.sequence_number is None:
            series_pk: Optional[int] = self.series_id  # type: ignore[attr-defined]
            record_type_pk: Optional[int] = self.record_type_id  # type: ignore[attr-defined]
            if series_pk and record_type_pk:
                # Resolve encounter via DB rather than traversing ORM relations
                # so we don't require a pre-fetched series on a new instance.
                encounter_ids = (
                    ImagingStudy.objects
                    .filter(series__id=series_pk)
                    .values_list('encounter_id', flat=True)
                )
                if encounter_ids:
                    encounter_id = encounter_ids[0]
                    max_seq: Optional[int] = DigitalRecord.objects.filter(
                        series__imaging_study__encounter_id=encounter_id,
                        record_type_id=record_type_pk,
                    ).aggregate(m=Max('sequence_number'))['m']
                    self.sequence_number = (max_seq or 0) + 1
        super().save(*args, **kwargs)
        self._assign_bolton_record_identifier()

    def _assign_bolton_record_identifier(self) -> None:
        """Create or update the stored Bolton record identifier on the M2M identifiers field."""
        new_value: str = self.bolton_record_id
        if not new_value:
            return
        existing = list(self.identifiers.filter(system=SYSTEM_IDENTIFIER_BOLTON_RECORD))
        official_existing = [i for i in existing if i.use == 'official']
        if official_existing and official_existing[0].value == new_value:
            return
        for old_ident in official_existing:
            old_ident.use = 'old'
            old_ident.save(update_fields=['use'])
        new_ident, _ = Identifier.objects.get_or_create(
            system=SYSTEM_IDENTIFIER_BOLTON_RECORD,
            value=new_value,
            defaults={'use': 'official'},
        )
        if new_ident.use != 'official':
            new_ident.use = 'official'
            new_ident.save(update_fields=['use'])
        self.identifiers.add(new_ident)



class ArchiveLocation(TimestampedModel):
    """One concrete archived copy of a digital record stored at an endpoint."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'pending'
        ARCHIVED = 'archived', 'archived'
        FAILED = 'failed', 'failed'
        VERIFIED = 'verified', 'verified'

    digital_record = models.ForeignKey(
        DigitalRecord,
        on_delete=models.CASCADE,
        related_name='archive_locations',
        help_text='DigitalRecord represented by this archived copy',
    )
    endpoint = models.ForeignKey(
        Endpoint,
        on_delete=models.PROTECT,
        related_name='archive_locations',
        help_text='Archive endpoint where the record copy is stored',
    )
    assigned_id = models.CharField(
        max_length=500,
        help_text='Endpoint-assigned identifier (UID, file id, path, etc.)',
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta(TimestampedModel.Meta):
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['digital_record']),
            models.Index(fields=['endpoint']),
            models.Index(fields=['status']),
        ]

    def __str__(self) -> str:
        return f"ArchiveLocation digital_record={self.digital_record.pk} endpoint={self.endpoint.pk}"
