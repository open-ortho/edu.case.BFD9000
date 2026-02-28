from django.db import migrations


def update_modalities_from_dcm(apps, schema_editor) -> None:
    Coding = apps.get_model("archive", "Coding")
    ValueSet = apps.get_model("archive", "ValueSet")
    ValueSetConcept = apps.get_model("archive", "ValueSetConcept")

    dicom_system = "http://dicom.nema.org/resources/ontology/DCM"
    modalities_valueset = ValueSet.objects.filter(slug="modalities").first()

    modality_definitions = [
        (
            "RG",
            "Radiographic imaging",
            "An acquisition device, process or method that performs radiographic imaging (conventional film/screen).",
        ),
        (
            "XC",
            "External-camera Photography",
            "An acquisition device, process or method that performs photography with an external camera.",
        ),
        (
            "M3D",
            "3D Manufacturing Modeling System",
            "A device, process or method that produces data (models) for use in 3D manufacturing.",
        ),
        (
            "OSS",
            "Optical Surface Scanner",
            "An acquisition device, process or method that performs optical surface scanning.",
        ),
        (
            "DOC",
            "Document",
            "A device, process or method that produces documents. i.e., representations of documents as images, whether by scanning or other means.",
        ),
        (
            "110038",
            "Paper Document",
            "Any paper or similar document.",
        ),
    ]

    for code, display, meaning in modality_definitions:
        coding, created = Coding.objects.get_or_create(
            system=dicom_system,
            code=code,
            defaults={
                "display": display,
                "meaning": meaning,
            },
        )
        if not created:
            updated = False
            if coding.display != display:
                coding.display = display
                updated = True
            if coding.meaning != meaning:
                coding.meaning = meaning
                updated = True
            if updated:
                coding.save(update_fields=["display", "meaning"])

        if modalities_valueset:
            ValueSetConcept.objects.get_or_create(valueset=modalities_valueset, coding=coding)

    si_coding = Coding.objects.filter(system=dicom_system, code="SI").first()
    if si_coding and modalities_valueset:
        ValueSetConcept.objects.filter(valueset=modalities_valueset, coding=si_coding).delete()


def noop_reverse(apps, schema_editor) -> None:
    return


class Migration(migrations.Migration):
    dependencies = [
        ("archive", "0013_seed_dropdown_valuesets"),
    ]

    operations = [
        migrations.RunPython(update_modalities_from_dcm, noop_reverse),
    ]
