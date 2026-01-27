# File Naming Scheme

## Overview

Uploaded image files are now organized by subject and encounter with structured, meaningful filenames.

## Directory Structure

```
media/uploads/
└── subject_{subject_id}/
    └── encounter_{encounter_id}/
        └── YYYYMMDD_HHMMSS_{record_type}.{ext}
```

## Naming Components

### Directory Hierarchy
- **`subject_{id}`**: Groups all files for a specific subject
- **`encounter_{id}`**: Groups files by clinical encounter/visit

### Filename Format
- **`YYYYMMDD`**: Date when file was uploaded (e.g., 20260127)
- **`HHMMSS`**: Time when file was uploaded (e.g., 143052)
- **`{record_type}`**: Coding code for the record type (e.g., `201456002` for Cephalogram, `lateral`, `pa`)
- **`.{ext}`**: Original file extension (`.png`, `.stl`)

## Examples

```
media/uploads/subject_3/encounter_5/20260127_143052_201456002.png
                ↑              ↑              ↑        ↑
              Subject 3    Encounter 5    Timestamp  Record Type: Cephalogram

media/uploads/subject_7/encounter_12/20260128_091523_lateral.stl
                ↑              ↑               ↑        ↑
              Subject 7    Encounter 12    Timestamp  Record Type: Lateral
```

## Benefits

✅ **Organized by Subject**: Easy to find all files for a patient
✅ **Organized by Encounter**: Group files from same visit
✅ **Meaningful Names**: Timestamp + record type tells you what it is
✅ **No Collisions**: Timestamp ensures uniqueness
✅ **Sortable**: Filenames sort chronologically
✅ **Traceable**: Can trace file back to exact subject and encounter

## Implementation

The naming is handled by `imaging_study_upload_path()` function in `archive/models.py`:

```python
def imaging_study_upload_path(instance, filename: str) -> str:
    """Generate structured upload path for imaging study files."""
    subject_id = instance.encounter.subject.id
    encounter_id = instance.encounter.id
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    record_type = instance.record_type.code
    ext = os.path.splitext(filename)[1]

    return f'uploads/subject_{subject_id}/encounter_{encounter_id}/{timestamp}_{record_type}{ext}'
```

## Migration Note

**Existing files are NOT renamed or moved.** The new naming scheme only applies to:
- Files uploaded after restarting the server
- New records created after the change

Old files will remain at their original paths (e.g., `uploads/2026/01/27/test1-dental-film...png`)

## Testing the New Scheme

After restarting the server, upload a new record:

```bash
curl -X POST http://localhost:8000/api/encounters/3/records/ \
  -u admin:password \
  -F "file=@image.png" \
  -F "record_type=201456002" \
  -F "orientation=7771000" \
  -F "modality=RG"
```

Check the directory structure:
```bash
tree media/uploads/subject_3/
```

Expected output:
```
media/uploads/subject_3/
└── encounter_3/
    └── 20260127_174523_201456002.png
```
