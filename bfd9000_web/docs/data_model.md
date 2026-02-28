# Archive Data Model

This document defines the archive concepts and rationale used by the Django models.

## Core hierarchy

Imaging data is organized as:

`Encounter 1 -> 1 ImagingStudy 1 -> N Series 1 -> N Record`

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
- All records can share the same study (`ImagingStudy.instance_uid`).
- Cephalometric images and model scans belong to different `Series` because modality/acquisition context differs.

## Field ownership and non-duplication rules

These rules are strict.

### ImagingStudy

Owns study-level context only:

- `encounter` (one-to-one)
- `collection`
- study identifiers (`instance_uid`, external identifiers)
- study-level endpoint/description

Must not own instance-level fields such as file uploads, scan operator, scan datetime, modality, or record type.

### Series

Owns grouping/classification fields:

- `record_type` (SNOMED clinical study type)
- `modality` (DICOM modality)
- `acquisition_location`
- optional `uid` and description

### Record

Owns per-instance/acquisition fields:

- `sop_instance_uid` (instance UID)
- acquisition metadata (`acquisition_datetime`, `scan_operator`)
- file/preview/archive linkage (`source_file`, `thumbnail`, `endpoint`)
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
- Virtual location: represented by `endpoint` for permanent retrieval target.

Current schema supports one canonical endpoint per record. If multiple virtual endpoints are required later, add a separate child model instead of overloading existing fields.

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
