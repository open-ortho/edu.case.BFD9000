# API Implementation Notes

This document describes discrepancies between the API specification (`api_requirements.md`) and the current backend implementation.

## Subject API

### Spec vs Implementation

| Spec Field | Backend Field | Notes |
|------------|---------------|-------|
| `identifier` (string) | `identifiers` (array of Identifier objects) | Backend uses M2M relationship. To get subject identifier, access `identifiers[0].value`. To create, must POST identifier separately or extend serializer. |
| `sex` (M/F/O) | `gender` (male/female/other/unknown) | Different values. Frontend must map: M->male, F->female, O->other |
| `date_of_birth` | `birth_date` | Same format (date), different name |
| `dental_classification` | `skeletal_pattern` (FK to Coding) | Backend uses Coding reference, not simple string |
| `collection` | `collection` (SlugRelatedField) | Compatible - uses short_name |

### Workarounds for Frontend

1. **Display identifier**: Use `subject.identifiers[0]?.value` or fall back to `subject.id`
2. **Display subject**: Use `humanname_family, humanname_given` or identifier
3. **Create subject**: Currently requires `gender`, `birth_date`, `humanname_family`, `humanname_given` (all required by model)

## Encounter API

### Spec vs Implementation

| Spec Field | Backend Field | Notes |
|------------|---------------|-------|
| `encounter_date` | `actual_period_start` | Different name |
| `subject_id` | `subject` | Backend expects integer PK, not identifier string |
| `age_at_encounter` | `age_at_encounter` | Compatible (float, years) |
| - | `procedure_code` | **Required** FK to Coding - not in spec but required by model |

### Workarounds for Frontend

1. **Create encounter**: Must provide `procedure_code` (Coding PK). Need to fetch/create a default procedure code.
2. **Filter by subject**: Use `?subject={pk}` not identifier string

## Record API

### Spec vs Implementation

| Spec Field | Backend Field | Notes |
|------------|---------------|-------|
| `encounter_id` | `encounter` | Integer PK |
| `subject_id` | N/A | Must join through encounter.subject |
| `file_size` | N/A | Must get from `imaging_study.source_file` if available |
| `image_type` | N/A | Must derive from `imaging_study.source_file` extension |
| `acquisition_date` | `imaging_study.scan_datetime` | Via related imaging_study |
| `thumbnail_url` | `/api/records/{id}/thumbnail/` | Custom action endpoint |
| `image_url` | `/api/records/{id}/image/` | Custom action endpoint |

### Record List Response

The current RecordSerializer doesn't include nested encounter/subject data. To display subject info in records list, either:
1. Make additional API calls per record
2. Extend RecordSerializer to include nested data (recommended future work)

## Recommendations

1. **Short-term**: Frontend adapts to current backend structure
2. **Medium-term**: Add convenience fields to serializers (e.g., `identifier` computed field on SubjectSerializer)
3. **Long-term**: Review model to simplify Subject.identifiers to single identifier field if multiple identifiers aren't needed
