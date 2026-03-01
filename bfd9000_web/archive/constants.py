"""Shared code systems and identifier system URLs."""

SYSTEM_RECORD_TYPE = 'http://snomed.info/sct'
SYSTEM_ORIENTATION = 'http://snomed.info/sct'
SYSTEM_MODALITY = 'http://dicom.nema.org/resources/ontology/DCM'
SYSTEM_PROCEDURE = 'http://snomed.info/sct'
SYSTEM_BODY_SITE = 'http://snomed.info/sct'
SYSTEM_IDENTIFIER_BOLTON_SUBJECT = 'https://orthodontics.case.edu/fhir/identifier-system/bolton-subject-id'
SYSTEM_IDENTIFIER_BRUSH = 'https://orthodontics.case.edu/fhir/identifier-system/brush-id'
SYSTEM_IDENTIFIER_LANCASTER_SUBJECT = 'https://cleftclinic.org/fhir/identifier-system/lancaster-subject-id'
SYSTEM_IDENTIFIER_IMAGE_TYPE = 'https://orthodontics.case.edu/fhir/identifier-system/image-type'

BFD9000_ROOT_UID = "1.3.6.1.4.1.61741.11.8"
STUDYINSTANCEUID_ROOT = f"{BFD9000_ROOT_UID}.2"
SERIESINSTANCEUID_ROOT = f"{BFD9000_ROOT_UID}.3"
SOPINSTANCEUID_ROOT = f"{BFD9000_ROOT_UID}.4"
