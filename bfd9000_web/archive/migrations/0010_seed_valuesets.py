from django.db import migrations


def add_valuesets(apps, schema_editor) -> None:
    Coding = apps.get_model("archive", "Coding")
    ValueSet = apps.get_model("archive", "ValueSet")
    ValueSetConcept = apps.get_model("archive", "ValueSetConcept")

    skeletal_valueset, _ = ValueSet.objects.get_or_create(
        slug="skeletal-pattern",
        defaults={
            "url": "https://orthodontics.case.edu/fhir/ValueSet/skeletal-pattern",
            "name": "SkeletalPattern",
            "title": "Skeletal pattern",
            "description": "Angle classification skeletal pattern value set.",
            "status": "active",
            "publisher": "Case Western Reserve University",
        },
    )

    race_valueset, _ = ValueSet.objects.get_or_create(
        slug="race",
        defaults={
            "url": "http://terminology.hl7.org/ValueSet/v2-0005",
            "name": "PHVSRaceHL72x",
            "title": "PHVS_Race_HL7_2x",
            "version": "4.0.0",
            "status": "active",
            "publisher": "Health Level Seven International",
            "publication_url": "https://terminology.hl7.org/7.0.1/ValueSet-v2-0005.html",
            "code_system_url": "urn:oid:2.16.840.1.113883.6.238",
            "code_system_publication_url": "https://terminology.hl7.org/7.0.1/CodeSystem-v2-0005.html",
            "code_system_status": "retired",
            "description": (
                "Race value set based on CDC check-digit codes and HL7 v2 table 0005. "
                "The v2-0005 CodeSystem is retired; the codes used here are from the CDC Race & Ethnicity system "
                "(urn:oid:2.16.840.1.113883.6.238)."
            ),
        },
    )

    skeletal_codes = ["248292005", "248293000", "248294006"]
    snomed_system = "http://snomed.info/sct"
    for code in skeletal_codes:
        coding = Coding.objects.get(system=snomed_system, code=code)
        ValueSetConcept.objects.get_or_create(
            valueset=skeletal_valueset, coding=coding)

    race_codes = ["2106-3", "2054-5"]
    race_system = "urn:oid:2.16.840.1.113883.6.238"
    for code in race_codes:
        coding = Coding.objects.get(system=race_system, code=code)
        ValueSetConcept.objects.get_or_create(
            valueset=race_valueset, coding=coding)


def remove_valuesets(apps, schema_editor) -> None:
    ValueSet = apps.get_model("archive", "ValueSet")
    ValueSet.objects.filter(slug__in=["skeletal-pattern", "race"]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("archive", "0009_add_valuesets"),
    ]

    operations = [
        migrations.RunPython(add_valuesets, remove_valuesets),
    ]
