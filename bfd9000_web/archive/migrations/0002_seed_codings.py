from django.db import migrations


SCT = "http://snomed.info/sct"
DCM = "http://dicom.nema.org/resources/ontology/DCM"
RACE = "urn:oid:2.16.840.1.113883.6.238"
IMAGE_TYPE_SYSTEM = "https://orthodontics.case.edu/fhir/identifier-system/image-type"


VALUESETS = [
    {
        "slug": "record_types",
        "url": "https://orthodontics.case.edu/fhir/ValueSet/record-types",
        "name": "RecordTypes",
        "title": "Record types",
        "status": "active",
        "publisher": "Case Western Reserve University",
    },
    {
        "slug": "orientations",
        "url": "https://orthodontics.case.edu/fhir/ValueSet/orientations",
        "name": "Orientations",
        "title": "Orientations",
        "status": "active",
        "publisher": "Case Western Reserve University",
    },
    {
        "slug": "modalities",
        "url": "https://orthodontics.case.edu/fhir/ValueSet/modalities",
        "name": "Modalities",
        "title": "Modalities",
        "status": "active",
        "publisher": "Case Western Reserve University",
    },
    {
        "slug": "body_sites",
        "url": "https://orthodontics.case.edu/fhir/ValueSet/body-sites",
        "name": "BodySites",
        "title": "Body sites",
        "status": "active",
        "publisher": "Case Western Reserve University",
    },
    {
        "slug": "procedures",
        "url": "https://orthodontics.case.edu/fhir/ValueSet/procedures",
        "name": "Procedures",
        "title": "Procedures",
        "status": "active",
        "publisher": "Case Western Reserve University",
    },
    {
        "slug": "image_types",
        "url": "https://orthodontics.case.edu/fhir/ValueSet/image-types",
        "name": "Image Types",
        "title": "Image types",
        "description": "Image type codes for archived records",
        "version": "1.0.0",
        "status": "active",
    },
    {
        "slug": "skeletal-pattern",
        "url": "https://orthodontics.case.edu/fhir/ValueSet/skeletal-pattern",
        "name": "SkeletalPattern",
        "title": "Skeletal pattern",
        "description": "Angle classification skeletal pattern value set.",
        "status": "active",
        "publisher": "Case Western Reserve University",
    },
    {
        "slug": "race",
        "url": "http://terminology.hl7.org/ValueSet/v2-0005",
        "name": "PHVSRaceHL72x",
        "title": "PHVS_Race_HL7_2x",
        "version": "4.0.0",
        "status": "active",
        "publisher": "Health Level Seven International",
        "publication_url": "https://terminology.hl7.org/7.0.1/ValueSet-v2-0005.html",
        "code_system_url": RACE,
        "code_system_publication_url": "https://terminology.hl7.org/7.0.1/CodeSystem-v2-0005.html",
        "code_system_status": "retired",
        "description": (
            "Race value set based on CDC check-digit codes and HL7 v2 table 0005. "
            "The v2-0005 CodeSystem is retired; the codes used here are from the "
            "CDC Race & Ethnicity system (urn:oid:2.16.840.1.113883.6.238)."
        ),
    },
]


CODINGS = {
    "record_types": [
        (SCT, "201456002", "Cephalogram", ""),
        (SCT, "268425006", "Pelvis X-ray", ""),
        (SCT, "39714003", "Skeletal X-ray of wrist and hand", ""),
        (SCT, "1597004", "Skeletal X-ray of ankle and foot", ""),
        (SCT, "302189007", "Dental model", ""),
    ],
    "orientations": [
        (SCT, "399198007", "Right lateral projection", ""),
        (SCT, "399173006", "Left lateral projection", ""),
        (SCT, "272479007", "Posteroanterior projection", ""),
        (SCT, "399348003", "Antero-posterior projection", ""),
        (SCT, "7771000", "Left", ""),
        (SCT, "24028007", "Right", ""),
    ],
    "body_sites": [
        (SCT, "69536005", "Head", ""),
        (SCT, "609617007", "Structure of pelvic segment of trunk", ""),
        (SCT, "731298009", "Entire ankle and foot", ""),
        (SCT, "729875002", "Entire wrist and hand", ""),
        (SCT, "1927002", "Entire left elbow region", ""),
        (SCT, "71889004", "Entire right elbow region", ""),
        (SCT, "210659002", "Entire left knee", ""),
        (SCT, "210562007", "Entire right knee", ""),
    ],
    "modalities": [
        (
            DCM,
            "RG",
            "Radiographic imaging",
            "An acquisition device, process or method that performs radiographic imaging (conventional film/screen).",
        ),
        (
            DCM,
            "XC",
            "External-camera Photography",
            "An acquisition device, process or method that performs photography with an external camera.",
        ),
        (
            DCM,
            "M3D",
            "3D Manufacturing Modeling System",
            "A device, process or method that produces data (models) for use in 3D manufacturing.",
        ),
        (
            DCM,
            "OSS",
            "Optical Surface Scanner",
            "An acquisition device, process or method that performs optical surface scanning.",
        ),
        (
            DCM,
            "DOC",
            "Document",
            "A device, process or method that produces documents. i.e., representations of documents as images, whether by scanning or other means.",
        ),
        (
            DCM,
            "DOCD",
            "Document Digitizer Equipment",
            "A device, process or method that digitizes hardcopy documents and imports them.",
        ),
        (DCM, "110038", "Paper Document", "Any paper or similar document."),
    ],
    "procedures": [
        (SCT, "ortho-visit", "Orthodontic Visit", ""),
    ],
    "image_types": [
        (IMAGE_TYPE_SYSTEM, "L", "Lateral", ""),
        (IMAGE_TYPE_SYSTEM, "F", "Frontal", ""),
        (IMAGE_TYPE_SYSTEM, "P", "Pelvis", ""),
        (IMAGE_TYPE_SYSTEM, "FA", "Foot & Ankle", ""),
        (IMAGE_TYPE_SYSTEM, "H", "Hand & Wrist", ""),
        (IMAGE_TYPE_SYSTEM, "RE", "Record of Examination", ""),
        (IMAGE_TYPE_SYSTEM, "RF", "Record of Facial and Jaw Examination", ""),
        (IMAGE_TYPE_SYSTEM, "SM", "Scan of Study Model", ""),
        (IMAGE_TYPE_SYSTEM, "FM", "Scan of Facial Moulage", ""),
    ],
    "skeletal-pattern": [
        (SCT, "248292005", "Class I facial skeletal pattern", "Class I facial skeletal pattern (finding)"),
        (SCT, "248293000", "Class II facial skeletal pattern", "Class II facial skeletal pattern (finding)"),
        (SCT, "248294006", "Class III facial skeletal pattern", "Class III facial skeletal pattern (finding)"),
    ],
    "race": [
        (RACE, "2106-3", "White", "White"),
        (RACE, "2054-5", "Black or African American", "Black or African American"),
    ],
}


def seed_valuesets_and_codings(apps, schema_editor):
    del schema_editor
    Coding = apps.get_model("archive", "Coding")
    ValueSet = apps.get_model("archive", "ValueSet")
    ValueSetConcept = apps.get_model("archive", "ValueSetConcept")

    valuesets_by_slug = {}
    for payload in VALUESETS:
        slug = payload["slug"]
        defaults = dict(payload)
        defaults.pop("slug")
        valueset, _ = ValueSet.objects.get_or_create(slug=slug, defaults=defaults)
        valuesets_by_slug[slug] = valueset

    for slug, coding_rows in CODINGS.items():
        valueset = valuesets_by_slug[slug]
        for system, code, display, meaning in coding_rows:
            coding, _ = Coding.objects.get_or_create(
                system=system,
                version="",
                code=code,
                defaults={"display": display, "meaning": meaning},
            )
            updates = []
            if coding.display != display:
                coding.display = display
                updates.append("display")
            if coding.meaning != meaning:
                coding.meaning = meaning
                updates.append("meaning")
            if updates:
                coding.save(update_fields=updates)

            ValueSetConcept.objects.get_or_create(valueset=valueset, coding=coding)

    Coding.objects.filter(system=DCM, code="SI").delete()


def unseed_valuesets_and_codings(apps, schema_editor):
    del schema_editor
    ValueSet = apps.get_model("archive", "ValueSet")
    ValueSet.objects.filter(
        slug__in=[
            "record_types",
            "orientations",
            "modalities",
            "body_sites",
            "procedures",
            "image_types",
            "skeletal-pattern",
            "race",
        ]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("archive", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_valuesets_and_codings, unseed_valuesets_and_codings),
    ]
