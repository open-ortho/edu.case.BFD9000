from django import forms

from .models import Encounter, Record


class RecordForm(forms.ModelForm):
    """Form used to capture the minimum metadata for a new physical record."""

    INGESTION_CHOICES = (
        ("upload", "Upload local file"),
        ("bfd9001", "Scan via BFD9001 (TODO)"),
        ("external", "Import from external storage (TODO)"),
    )

    upload = forms.FileField(
        required=False,
        help_text="Upload a local TIFF/PDF as a proof-of-concept placeholder.",
        widget=forms.ClearableFileInput(attrs={"class": "input"}),
        label="Upload file",
    )
    ingestion_mode = forms.ChoiceField(
        choices=INGESTION_CHOICES,
        initial="upload",
        widget=forms.RadioSelect,
        label="Digital content source",
    )

    class Meta:
        model = Record
        fields = [
            "encounter",
            "collection",
            "record_type",
            "physical_location",
            "physical_location_box",
            "physical_location_shelf",
            "physical_location_tray",
            "physical_location_compartment",
            "device",
            "imaging_study",
            "identifiers",
        ]
        widgets = {
            "identifiers": forms.CheckboxSelectMultiple,
        }

    def __init__(self, *args, **kwargs):
        self.subject = kwargs.pop("subject", None)
        super().__init__(*args, **kwargs)
        self.fields["identifiers"].required = False
        self.fields["imaging_study"].required = False
        encounter_field = self.fields.get("encounter")
        if isinstance(encounter_field, forms.ModelChoiceField):
            if self.subject is not None:
                encounter_field.queryset = Encounter.objects.filter(subject=self.subject)
                if not encounter_field.queryset.exists():
                    encounter_field.help_text = (
                        "No encounters found for this subject. Create one via the admin site first."
                    )
            encounter_field.empty_label = "Select encounter"
