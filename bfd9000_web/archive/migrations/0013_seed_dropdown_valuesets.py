from django.db import migrations


def add_dropdown_valuesets(apps, schema_editor) -> None:
    Coding = apps.get_model("archive", "Coding")
    ValueSet = apps.get_model("archive", "ValueSet")
    ValueSetConcept = apps.get_model("archive", "ValueSetConcept")

    valuesets = [
        (
            "record_types",
            "RecordTypes",
            "Record types",
            "https://orthodontics.case.edu/fhir/ValueSet/record-types",
        ),
        (
            "orientations",
            "Orientations",
            "Orientations",
            "https://orthodontics.case.edu/fhir/ValueSet/orientations",
        ),
        (
            "modalities",
            "Modalities",
            "Modalities",
            "https://orthodontics.case.edu/fhir/ValueSet/modalities",
        ),
        (
            "body_sites",
            "BodySites",
            "Body sites",
            "https://orthodontics.case.edu/fhir/ValueSet/body-sites",
        ),
        (
            "procedures",
            "Procedures",
            "Procedures",
            "https://orthodontics.case.edu/fhir/ValueSet/procedures",
        ),
    ]

    valueset_by_slug = {}
    for slug, name, title, url in valuesets:
        valueset, _ = ValueSet.objects.get_or_create(
            slug=slug,
            defaults={
                "url": url,
                "name": name,
                "title": title,
                "status": "active",
                "publisher": "Case Western Reserve University",
            },
        )
        valueset_by_slug[slug] = valueset

    snomed_system = "http://snomed.info/sct"
    dicom_system = "http://dicom.nema.org/resources/ontology/DCM"

    valueset_codes = {
        "record_types": {
            "system": snomed_system,
            "codes": [
                "201456002",
                "268425006",
                "39714003",
                "1597004",
                "302189007",
            ],
        },
        "orientations": {
            "system": snomed_system,
            "codes": [
                "399198007",
                "399173006",
                "272479007",
                "399348003",
                "7771000",
                "24028007",
            ],
        },
        "body_sites": {
            "system": snomed_system,
            "codes": [
                "69536005",
                "609617007",
                "731298009",
                "729875002",
                "1927002",
                "71889004",
                "210659002",
                "210562007",
            ],
        },
        "modalities": {
            "system": dicom_system,
            "codes": [
                "RG",
                "XC",
                "M3D",
                "OSS",
                "DOC",
                "DOCD",
                "110038",
            ],
        },
        "procedures": {
            "system": snomed_system,
            "codes": [],
        },
    }

    for slug, info in valueset_codes.items():
        valueset = valueset_by_slug[slug]
        codings = Coding.objects.filter(
            system=info["system"],
            code__in=info["codes"],
        )
        for coding in codings:
            ValueSetConcept.objects.get_or_create(valueset=valueset, coding=coding)


def remove_dropdown_valuesets(apps, schema_editor) -> None:
    ValueSet = apps.get_model("archive", "ValueSet")
    ValueSet.objects.filter(
        slug__in=["record_types", "orientations", "modalities", "body_sites", "procedures"]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("archive", "0012_record_dicom_fields_and_image_types"),
    ]

    operations = [
        migrations.RunPython(add_dropdown_valuesets, remove_dropdown_valuesets),
    ]
