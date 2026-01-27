# File Naming Scheme

## Overview

Uploaded image files are organized hierarchically by collection, subject, and encounter with structured, meaningful filenames. This ensures files from different collections remain separate and organized by their data provenance.

See [api_requirements.md](./api_requirements.md) for the complete API specification.

## Directory Structure

```
media/uploads/
└── {collection}/
    └── {subject_id}/
        └── {encounter_id}/
            └── YYYYMMDD_HHMMSS_{record_type}.{ext}
```

## Naming Components

### Directory Hierarchy
- **`{collection}`**: Collection short name (e.g., `bolton`, `brush`) - files organized by data source
- **`{subject_id}`**: Subject ID within that collection
- **`{encounter_id}`**: Encounter/visit ID for that subject

### Filename Format
- **`YYYYMMDD`**: Date when file was uploaded (e.g., 20260127)
- **`HHMMSS`**: Time when file was uploaded (e.g., 143052)
- **`{record_type}`**: Coding code for the record type (e.g., `lateral`, `pa`, `201456002`)
- **`.{ext}`**: Original file extension (`.png`, `.stl`)

## Examples

```
media/uploads/bolton/5/3/20260127_143052_lateral.png
              ↑      ↑ ↑    ↑               ↑
          Collection Subject Encounter   Timestamp + Type

media/uploads/brush/12/7/20260128_091523_pa.stl
              ↑     ↑  ↑    ↑               ↑
          Collection Subject Encounter   Timestamp + Type
```

## Benefits

✅ **Organized by Collection**: Separates datasets from different sources
✅ **Organized by Subject**: Easy to find all files for a patient within a collection
✅ **Organized by Encounter**: Group files from same visit
✅ **Meaningful Names**: Timestamp + record type tells you what it is
✅ **No Collisions**: Timestamp ensures uniqueness, collection prevents ID conflicts
✅ **Sortable**: Filenames sort chronologically
✅ **Traceable**: Can trace file back to collection, subject, and encounter

## Implementation

The naming is handled by `imaging_study_upload_path()` function in `archive/models.py`:

```python
def imaging_study_upload_path(instance, filename: str) -> str:
    """Generate structured upload path for imaging study files."""
    ext = os.path.splitext(filename)[1].lower()
    collection_name = instance.collection.short_name
    subject_id = instance.encounter.subject.id
    encounter_id = instance.encounter.id
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    record_type = instance.record_type.code
    new_filename = f"{timestamp}_{record_type}{ext}"
    return os.path.join('uploads', collection_name, str(subject_id), str(encounter_id), new_filename)
```

## Migration Note

**Existing files are NOT renamed or moved.** The new naming scheme only applies to:
- Files uploaded after this change
- New records created after the change

Old files will remain at their original paths.

## Testing the New Scheme

After deployment, upload a new record via the API as documented in [api_requirements.md#51-create-record-with-file-upload](./api_requirements.md#51-create-record-with-file-upload):

```bash
curl -X POST http://localhost:8000/api/encounters/3/records/ \
  -u admin:password \
  -F "file=@image.png" \
  -F "record_type=lateral" \
  -F "orientation=left" \
  -F "modality=RG"
```

Check the directory structure (example assuming collection "bolton"):
```bash
tree media/uploads/bolton/5/
```

Expected output:
```
media/uploads/bolton/5/
└── 3/
    └── 20260127_174523_lateral.png
```
