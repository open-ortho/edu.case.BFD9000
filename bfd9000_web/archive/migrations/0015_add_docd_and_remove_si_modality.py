from django.db import migrations


def add_docd_and_remove_si(apps, schema_editor) -> None:
    Coding = apps.get_model("archive", "Coding")
    ValueSet = apps.get_model("archive", "ValueSet")
    ValueSetConcept = apps.get_model("archive", "ValueSetConcept")

    dicom_system = "http://dicom.nema.org/resources/ontology/DCM"
    modalities_valueset = ValueSet.objects.filter(slug="modalities").first()

    docd, _ = Coding.objects.get_or_create(
        system=dicom_system,
        code="DOCD",
        defaults={
            "display": "Document Digitizer Equipment",
            "meaning": "A device, process or method that digitizes hardcopy documents and imports them.",
        },
    )

    if docd.display != "Document Digitizer Equipment" or docd.meaning != "A device, process or method that digitizes hardcopy documents and imports them.":
        docd.display = "Document Digitizer Equipment"
        docd.meaning = "A device, process or method that digitizes hardcopy documents and imports them."
        docd.save(update_fields=["display", "meaning"])

    if modalities_valueset:
        ValueSetConcept.objects.get_or_create(valueset=modalities_valueset, coding=docd)

    Coding.objects.filter(system=dicom_system, code="SI").delete()


def noop_reverse(apps, schema_editor) -> None:
    return


class Migration(migrations.Migration):
    dependencies = [
        ("archive", "0014_update_modalities_from_dcm"),
    ]

    operations = [
        migrations.RunPython(add_docd_and_remove_si, noop_reverse),
    ]
