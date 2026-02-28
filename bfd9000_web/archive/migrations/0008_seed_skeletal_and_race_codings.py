from django.db import migrations


def add_codings(apps, schema_editor) -> None:
    Coding = apps.get_model("archive", "Coding")

    snomed_system = "http://snomed.info/sct"
    race_system = "urn:oid:2.16.840.1.113883.6.238"

    snomed_codings = [
        {
            "system": snomed_system,
            "code": "248292005",
            "display": "Class I facial skeletal pattern",
            "meaning": "Class I facial skeletal pattern (finding)",
        },
        {
            "system": snomed_system,
            "code": "248293000",
            "display": "Class II facial skeletal pattern",
            "meaning": "Class II facial skeletal pattern (finding)",
        },
        {
            "system": snomed_system,
            "code": "248294006",
            "display": "Class III facial skeletal pattern",
            "meaning": "Class III facial skeletal pattern (finding)",
        },
    ]

    race_codings = [
        {
            "system": race_system,
            "code": "2106-3",
            "display": "White",
            "meaning": "White",
        },
        {
            "system": race_system,
            "code": "2054-5",
            "display": "Black or African American",
            "meaning": "Black or African American",
        },
    ]

    for coding in snomed_codings + race_codings:
        Coding.objects.get_or_create(
            system=coding["system"],
            version="",
            code=coding["code"],
            defaults={
                "display": coding["display"],
                "meaning": coding["meaning"],
            },
        )


def remove_codings(apps, schema_editor) -> None:
    Coding = apps.get_model("archive", "Coding")
    Coding.objects.filter(
        system="http://snomed.info/sct",
        code__in=["248292005", "248293000", "248294006"],
    ).delete()
    Coding.objects.filter(
        system="urn:oid:2.16.840.1.113883.6.238",
        code__in=["2106-3", "2054-5"],
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("archive", "0007_alter_subject_names_nullable"),
    ]

    operations = [
        migrations.RunPython(add_codings, remove_codings),
    ]
