# Converter Package Refactoring Summary

## Overview

Completely redesigned the `converters/` package with a clean, file-type-based architecture that separates metadata handling from binary encoding.

## Key Changes

### 1. **File-Type Based Organization**

**Before**: Modality-based converters (RadiographConverter, PhotographConverter, etc.)
**After**: File-type based converters (TIFFConverter, PNGConverter, JPEGConverter, PDFConverter, STLConverter)

**Rationale**: A TIFF file could be a radiograph, photograph, or other modality. The metadata DTO determines the modality, while the converter handles the binary encoding.

### 2. **Automatic Router**

New `router.py` module automatically selects the correct converter based on file extension:

```python
# Automatically picks TIFFConverter
convert_to_dicom(metadata, "xray.tiff", "output.dcm")

# Automatically picks PNGConverter  
convert_to_dicom(metadata, "xray.png", "output.dcm")

# Automatically picks PDFConverter
convert_to_dicom(doc_metadata, "consent.pdf", "output.dcm")
```

### 3. **Simplified Compression API**

**Before**: Complex transfer syntax management
**After**: Simple boolean flag

```python
# Compressed (JPEG2000 Lossless)
convert_to_dicom(metadata, "input.tiff", "output.dcm", compression=True)

# Uncompressed (ExplicitVRLittleEndian - required baseline)
convert_to_dicom(metadata, "input.tiff", "output.dcm", compression=False)
```

### 4. **Clean Separation of Concerns**

**Metadata DTOs** (`models.py`):
- Patient demographics
- Study/Series/Instance UIDs
- Modality-specific attributes
- **Does NOT** handle binary data

**Converters** (`converters/`):
- Load binary files
- Process/encode data
- Add PixelData or EncapsulatedDocument to Dataset
- **Does NOT** create metadata

## New File Structure

```
converters/
├── __init__.py              # Public API exports
├── README.md                # Documentation
├── base.py                  # Abstract base class, exceptions
├── router.py                # Automatic converter selection
├── tiff.py                  # TIFF → DICOM (8/16-bit, grayscale/RGB)
├── png.py                   # PNG → DICOM (8-bit)
├── jpeg.py                  # JPEG → DICOM (8-bit RGB/grayscale)
├── pdf.py                   # PDF → Encapsulated PDF Storage
├── stl.py                   # STL → Encapsulated STL (planned)
└── old/                     # Legacy code moved here
    ├── radiograph.py
    ├── photograph.py
    ├── document.py
    └── surface.py
```

## Usage Examples

### Basic Conversion

```python
from bfd9000_dicom import RadiographMetadata, PatientSex, convert_to_dicom

metadata = RadiographMetadata(
    patient_id="B0013",
    patient_sex=PatientSex.M,
    patient_age="217M"
)

ds = convert_to_dicom(metadata, "xray.tiff", "output.dcm", compression=True)
```

### Multi-Image Series (PA + Lateral Cephalograms)

```python
from pydicom.uid import generate_uid

# Shared UIDs for the series
study_uid = generate_uid()
series_uid = generate_uid()

# PA Ceph (Instance 1)
pa_meta = RadiographMetadata(
    patient_id="B0013",
    patient_sex=PatientSex.M,
    patient_age="217M",
    study_instance_uid=study_uid,
    series_instance_uid=series_uid,
    instance_number="1",
    patient_orientation="PA"
)

# Lateral Ceph (Instance 2)
lateral_meta = RadiographMetadata(
    patient_id="B0013",
    patient_sex=PatientSex.M,
    patient_age="217M",
    study_instance_uid=study_uid,      # Same
    series_instance_uid=series_uid,    # Same
    instance_number="2",               # Different
    patient_orientation="L"
)

convert_to_dicom(pa_meta, "pa.tiff", "pa.dcm")
convert_to_dicom(lateral_meta, "lateral.tiff", "lateral.dcm")
```

### Different File Types

```python
# Radiograph from any image format
convert_to_dicom(radiograph_meta, "xray.tiff", "xray.dcm")
convert_to_dicom(radiograph_meta, "xray.png", "xray.dcm")
convert_to_dicom(radiograph_meta, "xray.jpg", "xray.dcm")

# Photograph
convert_to_dicom(photo_meta, "intraoral.jpg", "photo.dcm")

# Document
convert_to_dicom(doc_meta, "consent.pdf", "consent.dcm")
```

## API Changes

### New Exports from `bfd9000_dicom`

```python
from bfd9000_dicom import (
    # Main API
    convert_to_dicom,              # NEW
    get_converter_for_file,        # NEW
    
    # Individual converters
    TIFFConverter,                 # NEW
    PNGConverter,                  # NEW
    JPEGConverter,                 # NEW
    PDFConverter,                  # NEW
    STLConverter,                  # NEW
    
    # Exceptions
    UnsupportedFileTypeError,      # NEW
    ConversionError,               # NEW
)
```

### Removed Exports

```python
# OLD - removed
RadiographConverter
SurfaceConverter
DocumentConverter
PhotographConverter
```

## Benefits

1. **Clearer Architecture**: File type determines converter, metadata determines modality
2. **Automatic Routing**: No need to manually choose converter
3. **Consistent API**: Same `convert_to_dicom()` for all file types
4. **Easy to Extend**: Add new file type by creating one converter module
5. **Better Maintainability**: Each converter is independent and focused
6. **Simpler Compression**: Boolean flag instead of transfer syntax constants

## Backward Compatibility

The old converter classes have been moved to `converters/old/` for reference. Code using the old API will need to be updated to use the new router-based approach.

## Next Steps

1. **Test with Real Files**: Test converters with actual TIFF/PNG/JPEG files
2. **Complete STL Converter**: Implement encapsulated STL support
3. **Add OBJ Support**: Add Wavefront OBJ 3D model support
4. **Performance Optimization**: Profile and optimize JPEG2000 compression
5. **Documentation**: Update main README.md with new API

## Files Changed

- ✅ Created: `converters/base.py`
- ✅ Created: `converters/router.py`
- ✅ Created: `converters/tiff.py`
- ✅ Created: `converters/png.py`
- ✅ Created: `converters/jpeg.py`
- ✅ Created: `converters/pdf.py`
- ✅ Created: `converters/stl.py`
- ✅ Created: `converters/README.md`
- ✅ Updated: `converters/__init__.py`
- ✅ Updated: `bfd9000_dicom/__init__.py`
- ✅ Created: `examples/converter_examples.py`
- ✅ Moved: Old converters to `converters/old/`
