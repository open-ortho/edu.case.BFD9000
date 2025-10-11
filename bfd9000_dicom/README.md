# bfd9000_dicom: DICOM Conversion Package for Medical Imaging

Convert various medical imaging formats (TIFF, PNG, STL, PDF) to DICOM standard format.

Originally developed for the Bolton-Brush Growth Study Collection (BBGSC), this package provides a Django-idiomatic interface for converting scanned radiographs, 3D models, documents, and photographs into DICOM format.

## Architecture

The package uses a **Data Transfer Object (DTO)** pattern with Django-like models for maximum flexibility and ease of use:

### Package Structure:

```
bfd9000_dicom/
├── converters/          # Specialized converters for different modalities
│   ├── radiograph.py    # TIFF/PNG radiograph conversion
│   ├── surface.py       # STL 3D model conversion (planned)
│   ├── document.py      # PDF document conversion (planned)
│   └── photograph.py    # JPEG/PNG photograph conversion (planned)
├── core/                # Core utilities
│   ├── dicom_builder.py # DICOM dataset building utilities
│   └── compression.py   # JPEG2000 compression utilities
├── models.py            # Django-style DTOs for DICOM metadata
├── examples/            # Usage examples
│   └── basic_usage.py   # Example code demonstrating the API
└── tests/               # Unit tests
    ├── test_converters.py
    ├── test_compression.py
    └── test_dicom_tags.py
```

### Core Components:

- **`models.py`**: Django-style DTOs for DICOM metadata
  - `BaseDICOMMetadata`: Common DICOM attributes
  - `RadiographMetadata`: Radiograph-specific metadata
  - `SurfaceMetadata`: 3D model metadata
  - `DocumentMetadata`: PDF document metadata
  - `PhotographMetadata`: Photograph metadata
  
- **`converters/`**: Specialized image converters for each modality
  - `RadiographConverter`: Convert TIFF/PNG radiographs to DICOM
  - `SurfaceConverter`: Convert STL 3D models (planned)
  - `DocumentConverter`: Convert PDF documents (planned)
  - `PhotographConverter`: Convert photographs (planned)

- **`core/`**: Core building blocks
  - `dicom_builder.py`: DICOM tag building utilities
  - `compression.py`: JPEG2000 compression utilities

### Design Philosophy:

The package is designed with Django integration in mind. Metadata classes work like Django models with methods such as `.to_dataset()` that convert metadata into pydicom Dataset objects.

## Requirements

Required packages:
- `imagecodecs` - JPEG2000 encoding/decoding
- `numpy` - Array processing
- `pillow` - Image processing
- `pydicom` - DICOM file handling

## Installation

Install the package in development mode:

```bash
pip install -e .
```

Or install from source:

```bash
pip install git+https://github.com/open-ortho/BFD9000.git#subdirectory=bfd9000_dicom
```

## Quick Start - Django Integration (Recommended)

The new DTO-based approach is designed for easy Django integration:

```python
from bfd9000_dicom import RadiographMetadata, PatientSex

# Create metadata from Django models
metadata = RadiographMetadata(
    patient_id=scan.patient.study_id,
    patient_sex=PatientSex.M,
    patient_age=f"{scan.patient.age_months}M",
    study_instance_uid=scan.study.dicom_uid,
    secondary_capture_device_manufacturer="Vidar",
    secondary_capture_device_manufacturer_model_name="DosimetryPRO Advantage",
)

# Convert to DICOM dataset (like Django's .save())
ds = metadata.to_dataset()

# Add pixel data and save
# ... add image data ...
ds.save_as("output.dcm")
```

See `examples/basic_usage.py` for more detailed examples.

## Quick Start - Using Converters

For simple conversions, use the converter classes:

```python
from bfd9000_dicom import RadiographConverter

# Convert a TIFF radiograph to DICOM with compression
RadiographConverter.convert(
    tiff_path="B0013LM18y01m.tif",
    dicom_path="B0013LM18y01m.dcm",
    with_compression=True
)

# Extract metadata from filename
patient_id, image_type, sex, age = RadiographConverter.extract_metadata_from_filename(
    "B0013LM18y01m.tif"
)
```

## Usage

### Programmatic Usage (Recommended)

Use the converter classes directly:

```python
from bfd9000_dicom.converters import RadiographConverter

# Basic conversion
RadiographConverter.convert('input.tif', 'output.dcm')

# With compression
RadiographConverter.convert('input.tif', 'output.dcm', with_compression=True)

# With custom DICOM metadata from JSON
RadiographConverter.convert('input.tif', 'output.dcm', dicom_json='metadata.json')
```

### Legacy Command Line Interface

**Note**: The CLI entry point has been removed in favor of using the examples module.

To use the conversion functionality from the command line, run:

```bash
python -m bfd9000_dicom.examples.basic_usage
```

Or create your own script using the converters.

## File Naming Convention

The package expects TIFF files to follow a specific naming convention for automatic metadata extraction:

**Format**: `[PatientID][ImageType][Sex][Age].tif`

**Example**: `B0013LM18y01m.tif`
- `B0013`: Patient ID (5 characters)
- `L`: Image type (1 character)
- `M`: Patient sex (1 character - M/F)
- `18y01m`: Patient age (format: XXyYYm - years and months)

The age is automatically converted to DICOM format (total months with 'M' suffix, e.g., "217M").

## DICOM Metadata

### Automatically Generated Tags

The package automatically generates standard DICOM tags including:

- **Patient Information**: Patient ID, Name, Sex, Age
- **Study Information**: Study/Series/SOP Instance UIDs
- **Image Information**: Rows, Columns, Bits Allocated, Pixel Spacing
- **Device Information**: Secondary Capture device details (Vidar DosimetryPRO Advantage)
- **Bolton-Brush Specific**: Modality (RG), Conversion Type (DF), deidentification markers

### Custom Metadata via JSON

You can provide additional DICOM metadata via a JSON file. See `tests/test.dcm.json` for an example format:

```json
{
    "00100010": {
        "vr": "PN",
        "Value": [{"Alphabetic": "Patient^Name"}]
    },
    "00080020": {
        "vr": "DA", 
        "Value": ["20241007"]
    }
}
```

## Image Processing

### Supported Formats
- **Input**: TIFF files with various bit depths and color modes
- **Color Modes**: L (grayscale), RGB, RGBA→RGB, LA→L, P→RGB
- **Bit Depths**: 8-bit and 16-bit
- **Output**: DICOM with optional JPEG2000 lossless compression

### Compression Options
- **Uncompressed**: Raw pixel data (default)
- **JPEG2000 Lossless**: Compressed pixel data with no quality loss (`--compress` flag)

## Error Handling

The package includes custom exception classes:

- `TIFF2DICOMError`: Base exception class
- `UnsupportedImageModeError`: Raised for unsupported image color modes
- `UnsupportedBitDepthError`: Raised for unsupported bit depths
- `InvalidJPEG2000CodestreamError`: Raised for invalid JPEG2000 compression

## Testing

Run the test suite:

```bash
cd bfd9000_dicom
python -m pytest tests/
```

Run individual test modules:
```bash
python -m pytest tests/test_converters.py
python -m pytest tests/test_compression.py
python -m pytest tests/test_dicom_tags.py
```

Run with coverage:
```bash
python -m pytest tests/ --cov=bfd9000_dicom --cov-report=html
```

See `tests/README.md` for more details on the test structure.

## Examples

### Example 1: Batch Conversion
```python
import os
from bfd9000_dicom import RadiographConverter

# Convert multiple files with compression
for filename in os.listdir('.'):
    if filename.endswith('.tif'):
        output = filename.replace('.tif', '.dcm')
        RadiographConverter.convert(filename, output, with_compression=True)
        print(f"Converted {filename} -> {output}")
```

### Example 2: Custom Metadata
```python
from bfd9000_dicom import RadiographConverter

# Convert with custom study information from JSON
RadiographConverter.convert(
    tiff_path='B0013LM18y01m.tif',
    dicom_path='B0013LM18y01m.dcm',
    dicom_json='custom_study_tags.json',
    with_compression=True
)
```

### Example 3: Using DTOs
```python
from bfd9000_dicom import RadiographMetadata, PatientSex, ConversionType, BurnedInAnnotation

# Create detailed metadata
metadata = RadiographMetadata(
    patient_id="B0013",
    patient_sex=PatientSex.M,
    patient_age="217M",
    conversion_type=ConversionType.DF,
    burned_in_annotation=BurnedInAnnotation.YES,
    secondary_capture_device_manufacturer="Vidar",
    secondary_capture_device_manufacturer_model_name="DosimetryPRO Advantage",
)

# Convert to DICOM dataset
ds = metadata.to_dataset()

# Add pixel data from image file and save
# ... (add pixel data processing) ...
# ds.save_as("output.dcm")
```

## Output

The conversion process will:
1. Extract patient metadata from the filename
2. Load and process the TIFF image
3. Generate required DICOM metadata
4. Apply optional JPEG2000 compression
5. Save the resulting DICOM file

Success message: `"Saved DICOM file at [output_path]"`
