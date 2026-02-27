from django.db import migrations, models
import django.db.models.deletion


IMAGE_TYPE_CODES = [
    ("L", "Lateral"),
    ("F", "Frontal"),
    ("P", "Pelvis"),
    ("FA", "Foot & Ankle"),
    ("H", "Hand & Wrist"),
    ("RE", "Record of Examination"),
    ("RF", "Record of Facial and Jaw Examination"),
    ("SM", "Scan of Study Model"),
    ("FM", "Scan of Facial Moulage"),
]


def seed_image_types(apps, schema_editor):
    del schema_editor
    Coding = apps.get_model("archive", "Coding")
    ValueSet = apps.get_model("archive", "ValueSet")
    ValueSetConcept = apps.get_model("archive", "ValueSetConcept")

    valueset, _ = ValueSet.objects.get_or_create(
        slug="image_types",
        defaults={
            "name": "Image Types",
            "url": "https://orthodontics.case.edu/fhir/ValueSet/image-types",
            "description": "Image type codes for archived records",
            "version": "1.0.0",
            "status": "active",
        },
    )

    for code, display in IMAGE_TYPE_CODES:
        coding, _ = Coding.objects.get_or_create(
            system="https://orthodontics.case.edu/fhir/identifier-system/image-type",
            code=code,
            defaults={"display": display},
        )
        ValueSetConcept.objects.get_or_create(valueset=valueset, coding=coding)


def unseed_image_types(apps, schema_editor):
    del schema_editor
    ValueSet = apps.get_model("archive", "ValueSet")
    ValueSet.objects.filter(slug="image_types").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("archive", "0011_add_encounter_date_precision_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="record",
            name="image_transform_ops",
            field=models.JSONField(blank=True, default=list, help_text="Ordered list of transform ops applied to preview image"),
        ),
        migrations.AddField(
            model_name="record",
            name="patient_orientation",
            field=models.CharField(blank=True, help_text="DICOM PatientOrientation (0020,0020), encoded as A\\F", max_length=16),
        ),
        migrations.AddField(
            model_name="record",
            name="sop_class_uid",
            field=models.CharField(blank=True, help_text="DICOM SOP Class UID", max_length=64),
        ),
        migrations.AddField(
            model_name="record",
            name="image_type",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="records_image_type", to="archive.coding"),
        ),
        migrations.RunPython(seed_image_types, unseed_image_types),
    ]
