# Archive Data Model

This document defines the archive concepts and rationale used by the Django models.


## Core hierarchy

Imaging data is organized as:

`Subject 1 -> N Encounter 1 -> 1 ImagingStudy 1 -> N Series 1 -> N Record`

- `Subject`: human/animal originator of the data, that the data represents
- `Encounter`: clinical event context.
- `ImagingStudy`: one study wrapper per encounter.
- `Series`: grouping of records with shared modality and clinical study type.
- `Record`: individual instance/artifact (physical and/or digital representation).

## Why a `Series` model exists

`Series` is intentionally explicit (not collapsed into `ImagingStudy` or `Record`) because grouping semantics matter for UID assignment and DICOM export:

- Different acquisition modalities during the same encounter belong to different series.
- Related records can share Study UID but must differ by Series UID.
- This grouping is known by the archive workflow; downstream DICOM generation should consume it, not infer it.

Example:

- One encounter can contain cephalometric films and scanned study models.
- All records can share the same study (`ImagingStudy.study_instance_uid`).
- Cephalometric images and model scans belong to different `Series` because modality/acquisition context differs.

## Field ownership and non-duplication rules

These rules are strict.

### ImagingStudy

Owns study-level context only:

- `encounter` (one-to-one)
- `collection`
- study identifiers (`study_instance_uid`, external identifiers)
- study-level endpoint/description

Must not own instance-level fields such as file uploads, scan operator, scan datetime, modality, or record type.

### Series

Owns grouping/classification fields:

- `record_type` (SNOMED clinical study type)
- `modality` (DICOM modality)
- `acquisition_location`
- optional `series_instance_uid` and description

### Record

```text
[Record]
    - id
    - (clinical metadata: sop_instance_uid, series, date, etc.)
[ArchiveLocation]
    - record_id     FK → Record
    - endpoint_id   FK → Endpoint
    - assigned_id   string (UID, Box file ID, SMB path, whatever)
    - status        (pending | archived | failed | verified)
    - archived_at   timestamp
[Endpoint]
    - id
    - status        (active | suspended | off)
    - connection_type  (dicom-stow-rs | dicom-dimse | smb | box | drive | file | ...)
    - address       (base URI/address)
    - name
    - config        (JSON blob: AE title, port overrides, non-secret settings)
    - credentials_encrypted (encrypted secret payload, not exposed via API)
```

FHIR Mapping When You Plug In Later

|   Your table    |               FHIR                |                         Notes                         |
| --------------- | --------------------------------- | ----------------------------------------------------- |
| Endpoint        | Endpoint                          | Nearly 1:1. config blob maps to header[] + extensions |
| Record          | ImagingStudy or DocumentReference | Depends on content type                               |
| ArchiveLocation | No native resource                | Gap — use extension or one-DocRef-per-copy pattern    |

For ArchiveLocation, the cleanest FHIR mapping when the time comes will be one DocumentReference per row, where:

- content[0].attachment.url = the full resolved URL (base address + assigned_id, composed at query time or stored directly)
- An extension holds the Endpoint reference + raw assigned_id separately if you need them decomposed
The relatesTo chain links all copies back to the canonical record.
Owns per-instance/acquisition fields:

- `sop_instance_uid` (instance UID)
- acquisition metadata (`acquisition_datetime`, `scan_operator`)
- file/preview linkage (`source_file`, `thumbnail`)
- archive linkage via `ArchiveLocation` rows
- transform and orientation metadata (`patient_orientation`, `image_transform_ops`)
- physical storage details (`physical_location_*`)
- optional capture `device`

## Critical semantic distinction: `record_type` vs `image_type`

These are different concepts and must never be substituted.

- `record_type`:
  - SNOMED clinical study type.
  - Owned by `Series`.
  - Used for clinical grouping/filtering.
- `image_type`:
  - Legacy identifier code (e.g., `L`, `SM`).
  - Owned by `Record`.
  - Used for source compatibility/import semantics.

## Clarifications from the refactor

- `Record.sop_class_uid` is removed; instance identity is `Record.sop_instance_uid`.
- `ImagingStudy` does not carry instance number; instance-level identity stays on `Record`.
- `scan_operator` and `acquisition_datetime` are record-level, not imaging-study-level.
- `scan_location` is replaced by `Series.acquisition_location` to represent where acquisition/digitization occurred for that series.
- `laterality` and `body_site` are not modeled on `ImagingStudy`.

## Physical and virtual record location model

`Record` can represent physical artifacts, virtual artifacts, or both:

- Physical location: represented by structured archive fields and optional address link.
- Virtual location: represented by one or more `ArchiveLocation` rows, each referencing an `Endpoint`.
- `Endpoint` stores connection definition (`connection_type`, `address`, `config`, status).
- `ArchiveLocation` stores record-specific assignment (`assigned_id`, status, `archived_at`).

## Staging vs archival storage

During pre-archive staging inside Django:

- file path layout is intentionally simple and implementation-focused
- `source_file` is transitory and can should removed after archival

Archival path hierarchy and provider-specific layout belong to the Storage Layer implementation (see issue #43), including local-storage hierarchy rules.

## Thumbnail policy

Thumbnails are persistent UI previews and follow these defaults:

- JPEG output
- max dimensions: 300x300
- target size: about 20KB
- hard size limit: 100KB
- default quality: 75 (tunable)

- Thumbnails are generated at upload only for raster image files (PNG, TIFF, JPEG). For 3D file types (STL, PLY, OBJ), no thumbnail is generated.
- Upload clients may provide an optional preprocessed preview image (`thumbnail_preview`) to be compressed and stored as the thumbnail source of truth.
- Thumbnail endpoint serves persisted thumbnail only; it does not generate previews at view time.
- If no thumbnail exists for a record, the API and UI return a static fallback JPEG image.

This is tuned for large-scale browse workloads. For planning, 500k thumbnails at ~20KB is roughly 10GB total.

## Device semantics

`Record.device` captures acquisition/scanning device information for the specific artifact instance (physical generation device or digitization device).

## API and UI implications

- Upload flow creates/reuses `ImagingStudy` and `Series`, then creates a `Record`.
- Subject/Encounter record counts traverse `...imaging_study__series__records`.
- Filtering by encounter/subject traverses through series/study chain.
- UI should present age-at-encounter (with precision/uncertainty) rather than raw study/series/record dates for clinical views.

## Migration policy for this refactor

- Historical archive migrations were replaced with a fresh baseline migration plus consolidated seed migration.
- No old-to-new data backfill migration is part of this schema reset workflow.
