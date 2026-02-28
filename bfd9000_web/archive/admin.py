"""Admin configuration for archive models."""

from django.contrib import admin

from .models import (
    Address,
    Coding,
    Collection,
    Encounter,
    Identifier,
    ImagingStudy,
    Location,
    Record,
    Subject,
)


class TimestampedAdmin(admin.ModelAdmin):
    """Base admin class with automatic user tracking for created_by and modified_by"""

    readonly_fields = ("created_at", "updated_at", "created_by", "modified_by")

    def save_model(self, request, obj, form, change):
        """Automatically set created_by and modified_by based on the current user"""
        if not change:  # Creating new object
            obj.created_by = request.user
        obj.modified_by = request.user
        super().save_model(request, obj, form, change)

    def get_fieldsets(self, request, obj=None):
        """Add audit fields section to all admin forms"""
        fieldsets = super().get_fieldsets(request, obj)

        # Convert to list if it's a tuple
        fieldsets = list(fieldsets) if fieldsets else []

        # Add audit section if not already present
        if fieldsets and not any("Audit Information" in str(fs) for fs in fieldsets):
            fieldsets.append(
                (
                    None,
                    {
                        "fields": [
                            "created_at",
                            "created_by",
                            "updated_at",
                            "modified_by",
                        ],
                        "classes": ["collapse"],
                    },
                )
            )

        return fieldsets


@admin.register(Coding)
class CodingAdmin(TimestampedAdmin):
    """Admin settings for Coding entries."""
    list_display = ("system", "code", "display", "version", "created_at")
    list_filter = ("system",)
    search_fields = ("system", "code", "display", "meaning")
    fieldsets = (
        (None, {"fields": ("system", "version", "code", "display", "meaning")}),
    )


@admin.register(Identifier)
class IdentifierAdmin(TimestampedAdmin):
    """Admin settings for Identifier entries."""
    list_display = ("system", "value", "use", "created_at")
    list_filter = ("use",)
    search_fields = ("system", "value")
    fieldsets = ((None, {"fields": ("use", "system", "value")}),)


@admin.register(Address)
class AddressAdmin(TimestampedAdmin):
    """Admin settings for Address entries."""
    list_display = ("line1", "city", "state", "country", "postal_code")
    list_filter = ("country", "state")
    search_fields = ("line1", "line2", "city", "state", "postal_code")
    fieldsets = (
        (None, {"fields": ("use", "type")}),
        (
            "Address Details",
            {
                "fields": (
                    "line1",
                    "line2",
                    "city",
                    "district",
                    "state",
                    "postal_code",
                    "country",
                )
            },
        ),
    )


@admin.register(Collection)
class CollectionAdmin(TimestampedAdmin):
    """Admin settings for collections/datasets."""
    list_display = (
        "short_name",
        "full_name",
        "curator",
        "institution",
        "start_date",
        "end_date",
    )
    list_filter = ("start_date", "end_date")
    search_fields = ("short_name", "full_name", "curator", "institution", "description")
    fieldsets = (
        (None, {"fields": ("short_name", "full_name", "description")}),
        ("Responsible Parties", {"fields": ("curator", "institution", "address")}),
        ("Timeframe", {"fields": ("start_date", "end_date")}),
    )


@admin.register(Subject)
class SubjectAdmin(TimestampedAdmin):
    """Admin settings for subjects/patients."""
    list_display = (
        "humanname_family",
        "humanname_given",
        "gender",
        "birth_date",
        "created_at",
    )
    list_filter = ("gender", "birth_date")
    search_fields = ("humanname_family", "humanname_given")
    filter_horizontal = ("identifiers",)
    fieldsets = (
        (
            "Personal Information",
            {"fields": ("humanname_family", "humanname_given", "gender", "birth_date")},
        ),
        ("Contact", {"fields": ("address",)}),
        (
            "Medical Information",
            {"fields": ("ethnicity", "skeletal_pattern", "palatal_cleft")},
        ),
        ("Identifiers", {"fields": ("identifiers",)}),
    )


@admin.register(Encounter)
class EncounterAdmin(TimestampedAdmin):
    """Admin settings for encounters/visits."""
    list_display = (
        "subject",
        "actual_period_start",
        "actual_period_end",
        "procedure_code",
        "created_at",
    )
    list_filter = ("actual_period_start", "actual_period_end")
    search_fields = ("subject__humanname_family", "subject__humanname_given")
    autocomplete_fields = ("subject",)
    fieldsets = (
        (None, {"fields": ("subject",)}),
        ("Timeframe", {"fields": ("actual_period_start", "actual_period_end")}),
        (
            "Medical Details",
            {
                "fields": (
                    "diagnosis",
                    "procedure_code",
                    "procedure_occurrence_age",
                    "procedure_occurrence_datetime",
                )
            },
        ),
    )


@admin.register(Location)
class LocationAdmin(TimestampedAdmin):
    """Admin settings for scan locations."""
    list_display = ("name", "address", "created_at")
    search_fields = ("name",)
    fieldsets = ((None, {"fields": ("name", "address")}),)


@admin.register(ImagingStudy)
class ImagingStudyAdmin(TimestampedAdmin):
    """Admin settings for imaging studies."""
    list_display = (
        "encounter",
        "collection",
        "record_type",
        "scan_datetime",
        "scan_operator",
    )
    list_filter = ("collection", "scan_datetime", "record_type")
    search_fields = (
        "encounter__subject__humanname_family",
        "encounter__subject__humanname_given",
        "instance_uid",
        "series_uid",
    )
    autocomplete_fields = ("encounter",)
    filter_horizontal = ("identifiers",)
    fieldsets = (
        (None, {"fields": ("encounter", "collection")}),
        (
            "Study Details",
            {"fields": ("record_type", "view", "body_site", "laterality")},
        ),
        (
            "Scan Information",
            {
                "fields": (
                    "scan_datetime",
                    "scan_operator",
                    "scan_location",
                    "device",
                    "endpoint",
                )
            },
        ),
        (
            "DICOM Fields",
            {
                "fields": (
                    "instance_uid",
                    "instance_sop_class",
                    "instance_number",
                    "series_uid",
                    "series_modality",
                ),
                "classes": ("collapse",),
            },
        ),
        ("Identifiers", {"fields": ("identifiers",)}),
    )


@admin.register(Record)
class RecordAdmin(TimestampedAdmin):
    """Admin settings for records and linked imaging studies."""
    list_display = (
        "encounter",
        "record_type",
        "is_scanned",
        "created_at",
    )
    list_filter = ("record_type", "created_at")
    search_fields = (
        "encounter__subject__humanname_family",
        "encounter__subject__humanname_given",
        "physical_location_box",
        "physical_location_shelf",
    )
    autocomplete_fields = ("encounter",)
    filter_horizontal = ("identifiers",)
    fieldsets = (
        (None, {"fields": ("encounter", "record_type")}),
        (
            "Physical Location",
            {
                "fields": (
                    "physical_location",
                    "physical_location_box",
                    "physical_location_shelf",
                    "physical_location_tray",
                    "physical_location_compartment",
                )
            },
        ),
        ("Digital Link", {"fields": ("imaging_study",)}),
        ("Other", {"fields": ("device",)}),
        ("Identifiers", {"fields": ("identifiers",)}),
    )
