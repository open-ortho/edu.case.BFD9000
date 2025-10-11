# Converters Package

The converters package provides file-type-specific converters for transforming binary files (images, documents, 3D models) into DICOM format.

## Architecture

### Design Principles

1. **Separation of Concerns**: Converters handle ONLY binary encoding. Metadata comes from DTO objects in `models.py`.
2. **File-Type Based**: Each file type (TIFF, PNG, JPEG, PDF, STL) has its own converter module.
3. **Automatic Routing**: The router automatically selects the correct converter based on file extension.
4. **Simple Compression API**: Bool flag for compression (True = JPEG2000 lossless, False = uncompressed).

### Structure

```
converters/
├── __init__.py         # Public API exports
├── base.py             # Abstract base class and exceptions
├── router.py           # Automatic converter selection
├── tiff.py             # TIFF → DICOM with PixelData
├── png.py              # PNG → DICOM with PixelData  
├── jpeg.py             # JPEG → DICOM with PixelData
├── pdf.py              # PDF → DICOM Encapsulated PDF
├── stl.py              # STL → DICOM Encapsulated STL (planned)
└── old/                # Legacy code for reference
```

## Usage

### Basic Conversion (Recommended)

Use the router for automatic converter selection:

```python
from bfd9000_dicom import RadiographMetadata, PatientSex, convert_to_dicom

# Create metadata
metadata = RadiographMetadata(
    patient_id="B0013",
    patient_sex=PatientSex.M,
    patient_age="217M"
)

# Router automatically picks the right converter based on file extension
ds = convert_to_dicom(
    metadata=metadata,
    input_path="xray.tiff",        # TIFFConverter used
    output_path="output.dcm",
    compression=True                # JPEG2000 lossless
)
```

### Multi-Image Series

For multiple images in the same series (e.g., PA and Lateral cephalograms):

```python
from pydicom.uid import generate_uid

# Generate shared UIDs
study_uid = generate_uid()
series_uid = generate_uid()

# PA Cephalogram (Instance 1)
pa_metadata = RadiographMetadata(
    patient_id="B0013",
    patient_sex=PatientSex.M,
    patient_age="217M",
    study_instance_uid=study_uid,
    series_instance_uid=series_uid,
    instance_number="1",
    patient_orientation="PA"
)

# Lateral Cephalogram (Instance 2)
lateral_metadata = RadiographMetadata(
    patient_id="B0013",
    patient_sex=PatientSex.M,
    patient_age="217M",
    study_instance_uid=study_uid,    # Same!
    series_instance_uid=series_uid,  # Same!
    instance_number="2",             # Different
    patient_orientation="L"
)

# Convert both
convert_to_dicom(pa_metadata, "pa.tiff", "pa.dcm")
convert_to_dicom(lateral_metadata, "lateral.tiff", "lateral.dcm")
```

### Different File Types

Same API works for all file types:

```python
# Radiograph from TIFF
convert_to_dicom(radiograph_meta, "xray.tiff", "xray.dcm")

# Photograph from JPEG
convert_to_dicom(photo_meta, "intraoral.jpg", "photo.dcm")

# Document from PDF
convert_to_dicom(doc_meta, "consent.pdf", "consent.dcm")
```

### Compression Options

```python
# Compressed (JPEG2000 Lossless) - smaller files
convert_to_dicom(metadata, "input.tiff", "output.dcm", compression=True)

# Uncompressed (ExplicitVRLittleEndian) - faster, larger files
convert_to_dicom(metadata, "input.tiff", "output.dcm", compression=False)
```

### Query Converter

Check which converter will be used:

```python
from bfd9000_dicom import get_converter_for_file

converter = get_converter_for_file("image.tiff")
print(converter.__name__)  # "TIFFConverter"
```

### Direct Converter Usage

For advanced use cases, call converters directly:

```python
from bfd9000_dicom.converters import TIFFConverter

ds = TIFFConverter.convert(
    metadata=metadata,
    input_path="xray.tiff",
    output_path="output.dcm",
    compression=True
)
```

## Supported File Types

| Extension | Converter | Encoding Method | Notes |
|-----------|-----------|-----------------|-------|
| `.tif`, `.tiff` | `TIFFConverter` | PixelData | Supports 8/16-bit, grayscale/RGB |
| `.png` | `PNGConverter` | PixelData | Typically 8-bit |
| `.jpg`, `.jpeg` | `JPEGConverter` | PixelData | 8-bit, RGB/grayscale |
| `.pdf` | `PDFConverter` | EncapsulatedDocument | Embedded as binary |
| `.stl` | `STLConverter` | Encapsulated3D | Planned, not yet implemented |

## Transfer Syntaxes

### Compression Enabled (`compression=True`)

- **Transfer Syntax**: JPEG2000 Lossless (`1.2.840.10008.1.2.4.90`)
- **Benefits**: 
  - Significantly smaller file size (often 50-70% reduction)
  - Lossless compression (no data loss)
  - Widely supported by DICOM viewers
- **Use for**: Archives, long-term storage, network transmission

### Compression Disabled (`compression=False`)

- **Transfer Syntax**: Explicit VR Little Endian (`1.2.840.10008.1.2.1`)
- **Benefits**:
  - Required baseline transfer syntax (all DICOM software must support)
  - Faster to read/write (no compression/decompression overhead)
  - Simpler debugging
- **Use for**: Testing, development, fast processing

## Error Handling

```python
from bfd9000_dicom import (
    convert_to_dicom,
    UnsupportedFileTypeError,
    ConversionError
)

try:
    ds = convert_to_dicom(metadata, "image.xyz", "output.dcm")
except UnsupportedFileTypeError as e:
    print(f"File type not supported: {e}")
except ConversionError as e:
    print(f"Conversion failed: {e}")
```

## Extending with New Converters

To add support for a new file type:

1. Create a new converter module (e.g., `obj.py`)
2. Inherit from `BaseConverter`
3. Implement the `convert()` method
4. Add to `CONVERTER_MAP` in `router.py`
5. Export from `__init__.py`

Example:

```python
# obj.py
from .base import BaseConverter

class OBJConverter(BaseConverter):
    @staticmethod
    def convert(metadata, input_path, output_path=None, compression=True):
        # Implementation here
        pass
```

```python
# router.py
CONVERTER_MAP = {
    # ... existing mappings
    '.obj': OBJConverter,
}
```

## See Also

- `examples/converter_examples.py` - Comprehensive usage examples
- `models.py` - Metadata DTOs
- `core/compression.py` - JPEG2000 compression utilities
