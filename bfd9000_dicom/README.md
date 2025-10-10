# bfd9000_dicom: DICOM Conversion Package for Medical Imaging

Convert various medical imaging formats (TIFF, PNG, STL, PDF) to DICOM standard format.

Originally developed for the Bolton-Brush Growth Study Collection (BBGSC), this package provides a Django-idiomatic interface for converting scanned radiographs, 3D models, documents, and photographs into DICOM format.

## Architecture

The package uses a **Data Transfer Object (DTO)** pattern with Django-like models for maximum flexibility and ease of use:

### Core Modules:
- **`models.py`**: Django-style DTOs for DICOM metadata (NEW!)
  - `BaseDICOMMetadata`: Common DICOM attributes
  - `RadiographMetadata`: Radiograph-specific metadata
  - `SurfaceMetadata`: 3D model metadata
  - `DocumentMetadata`: PDF document metadata
  - `PhotographMetadata`: Photograph metadata
  
- **`tiff2dcm.py`**: Command-line interface (legacy)
- **`dicom_tags.py`**: DICOM tag building utilities
- **`jpeg2000.py`**: JPEG2000 compression utilities
- **`__init__.py`**: Package initialization and exception classes

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

## Usage

### Command Line Interface

The main conversion tool can be used from the command line:

```bash
python -m bfd9000_dicom.tiff2dcm input.tif output.dcm [options]
```

#### Basic Usage

Convert a TIFF file to DICOM without compression:
```bash
python -m bfd9000_dicom.tiff2dcm B0013LM18y01m.tif B0013LM18y01m.dcm
```

Convert with JPEG2000 lossless compression:
```bash
python -m bfd9000_dicom.tiff2dcm B0013LM18y01m.tif B0013LM18y01m.dcm --compress
```

Use custom DICOM metadata from JSON file:
```bash
python -m bfd9000_dicom.tiff2dcm input.tif output.dcm --dicom_json metadata.json
```

#### Command Line Options

- `input_tiff`: Input TIFF file path (required)
- `output_dcm`: Output DICOM file path (required)
- `--dicom_json`: Path to JSON file containing custom DICOM tags (optional)
- `-c, --compress`: Enable JPEG2000 lossless compression (optional)

### Programmatic Usage

You can also use the package programmatically in Python:

```python
from bfd9000_dicom.tiff2dcm import convert_tiff_to_dicom

# Basic conversion
convert_tiff_to_dicom('input.tif', 'output.dcm')

# With compression
convert_tiff_to_dicom('input.tif', 'output.dcm', with_compression=True)

# With custom DICOM metadata
convert_tiff_to_dicom('input.tif', 'output.dcm', dicom_json='metadata.json')
```

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
python -m pytest tests/
```

Or run individual test files:
```bash
python -m unittest tests.test_tiff2dcm
python -m unittest tests.test_dicom_tags
```

## Examples

### Example 1: Batch Conversion
```bash
# Convert multiple files with compression
for file in *.tif; do
    python -m bfd9000_dicom.tiff2dcm "$file" "${file%.tif}.dcm" --compress
done
```

### Example 2: Custom Metadata
```python
from bfd9000_dicom.tiff2dcm import convert_tiff_to_dicom

# Convert with custom study information
convert_tiff_to_dicom(
    'B0013LM18y01m.tif',
    'B0013LM18y01m.dcm',
    dicom_json='custom_study_tags.json',
    with_compression=True
)
```

## Output

The conversion process will:
1. Extract patient metadata from the filename
2. Load and process the TIFF image
3. Generate required DICOM metadata
4. Apply optional JPEG2000 compression
5. Save the resulting DICOM file

Success message: `"Saved DICOM file at [output_path]"`
