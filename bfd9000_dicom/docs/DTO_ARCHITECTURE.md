# bfd9000_dicom DTO Architecture

## Overview

This document describes the Data Transfer Object (DTO) architecture implemented in `bfd9000_dicom` for Django integration.

## Design Rationale

### Why DTOs?

The package uses a **DTO pattern** inspired by Django's ORM to provide:

1. **Type Safety**: Clear contracts with type hints
2. **Django-like Interface**: Familiar `.to_dataset()` method pattern
3. **Validation**: Built-in field validation
4. **Flexibility**: Support for multiple imaging modalities
5. **Maintainability**: Single source of truth for DICOM metadata

### Single Package, Multiple Modalities

We chose a **single package** architecture for:

- **Radiographs** (TIFF/PNG) → `RadiographMetadata`
- **3D Models** (STL) → `SurfaceMetadata`
- **Documents** (PDF) → `DocumentMetadata`
- **Photographs** (JPEG/PNG) → `PhotographMetadata`

This provides:
- Shared infrastructure (UIDs, patient data, validation)
- Single dependency for Django apps
- Code reuse across modalities
- Unified API

## Class Hierarchy

```
BaseDICOMMetadata (abstract base)
├── RadiographMetadata (scanned radiographs)
├── SurfaceMetadata (3D models/STL)
├── DocumentMetadata (PDF documents)
└── PhotographMetadata (visible light photos)
```

## Key Classes

### BaseDICOMMetadata

Base class containing common DICOM attributes across all modalities.

**Key Features:**
- Auto-generates UIDs if not provided (Study, Series, SOP Instance)
- Auto-generates patient name from patient ID
- Maps Python field names to DICOM keywords
- Provides `.to_dataset()` method for conversion

**DICOM Modules Implemented:**
- Patient Information Module
- Study Information Module
- Series Information Module
- Instance Information Module
- Secondary Capture Device Module
- General Image Module

**Field Naming Convention:**
Python field names follow `snake_case` and map directly to DICOM keywords:
- `patient_id` → `PatientID` (0010,0020)
- `study_instance_uid` → `StudyInstanceUID` (0020,000D)
- `series_instance_uid` → `SeriesInstanceUID` (0020,000E)

### RadiographMetadata

Extends `BaseDICOMMetadata` for radiographic images.

**Additional Fields:**
- `conversion_type`: How the image was digitized (DF, DI, SYN)
- `burned_in_annotation`: Whether annotations are burned in
- `nominal_scanned_pixel_spacing`: Scanner pixel spacing
- `pixel_spacing`: Calibrated pixel spacing
- `image_laterality`: Left/Right/Bilateral/Unknown

**Default Modality:** `RG` (Radiographic imaging)

**Use Cases:**
- Scanned film radiographs (TIFF)
- Digital radiographs (PNG)
- Cephalometric images
- Hand-wrist radiographs

### SurfaceMetadata

Extends `BaseDICOMMetadata` for 3D surface models.

**Additional Fields:**
- `surface_processing_description`: Description of processing
- `surface_processing_algorithm`: Algorithm used

**Use Cases:**
- STL files from 3D scans
- Dental cast models
- Facial surface scans

### DocumentMetadata

Extends `BaseDICOMMetadata` for document encapsulation.

**Additional Fields:**
- `document_title`: Title of the document
- `mime_type`: MIME type (default: application/pdf)

**Default Modality:** `DOC`

**Use Cases:**
- Scanned consent forms
- Clinical reports
- Study documentation

### PhotographMetadata

Extends `BaseDICOMMetadata` for visible light photography.

**Default Modality:** `XC` (External-camera Photography)

**Use Cases:**
- Clinical photographs
- Intraoral photos
- Profile photographs

## Usage Patterns

### Pattern 1: Direct Instantiation

```python
from bfd9000_dicom import RadiographMetadata, PatientSex

metadata = RadiographMetadata(
    patient_id="B0013",
    patient_sex=PatientSex.M,
    patient_age="217M"
)

ds = metadata.to_dataset()
ds.save_as("output.dcm")
```

### Pattern 2: Django Model Integration

```python
# In Django views or services
def convert_scan_to_dicom(scan_record):
    """Convert a Django scan record to DICOM."""
    
    # Map Django model to DTO
    metadata = RadiographMetadata(
        patient_id=scan_record.patient.study_id,
        patient_sex=PatientSex[scan_record.patient.sex],
        patient_age=f"{scan_record.patient.age_months}M",
        study_instance_uid=scan_record.study.dicom_uid,
        series_instance_uid=scan_record.series.dicom_uid,
        secondary_capture_device_manufacturer=scan_record.device.manufacturer,
        secondary_capture_device_manufacturer_model_name=scan_record.device.model,
    )
    
    # Convert to DICOM
    ds = metadata.to_dataset()
    
    # Save generated UIDs back to Django
    scan_record.study.dicom_uid = ds.StudyInstanceUID
    scan_record.series.dicom_uid = ds.SeriesInstanceUID
    scan_record.sop_instance_uid = ds.SOPInstanceUID
    scan_record.save()
    
    return ds
```

### Pattern 3: Batch Processing

```python
from bfd9000_dicom import RadiographMetadata, PatientSex

def batch_convert_radiographs(patient_scans):
    """Convert multiple scans for a patient."""
    
    # Create study-level UID (shared across series)
    study_uid = generate_uid()
    
    for scan in patient_scans:
        metadata = RadiographMetadata(
            patient_id=scan.patient_id,
            patient_sex=PatientSex[scan.sex],
            patient_age=f"{scan.age_months}M",
            study_instance_uid=study_uid,  # Shared
            series_number=str(scan.series_number),
        )
        
        ds = metadata.to_dataset()
        # ... add image data and save
```

## Enumeration Types

The package provides type-safe enumerations for DICOM standard values:

### PatientSex
- `M`: Male
- `F`: Female
- `O`: Other
- `U`: Unknown

### ModalityType
- `RG`: Radiographic imaging
- `DX`: Digital Radiography
- `CR`: Computed Radiography
- `OT`: Other
- `DOC`: Document
- `XC`: External-camera Photography

### ConversionType
- `DF`: Digitized Film
- `DI`: Digital Interface
- `SYN`: Synthetic Image

### BurnedInAnnotation
- `YES`: Annotations burned in
- `NO`: No burned in annotations

## DICOM Tag Mapping

The DTOs handle the mapping from Python attributes to DICOM tags automatically:

| Python Attribute | DICOM Keyword | DICOM Tag | Module |
|-----------------|---------------|-----------|---------|
| `patient_id` | `PatientID` | (0010,0020) | Patient |
| `patient_sex` | `PatientSex` | (0010,0040) | Patient |
| `patient_age` | `PatientAge` | (0010,1010) | Patient |
| `patient_name` | `PatientName` | (0010,0010) | Patient |
| `study_instance_uid` | `StudyInstanceUID` | (0020,000D) | Study |
| `series_instance_uid` | `SeriesInstanceUID` | (0020,000E) | Series |
| `sop_instance_uid` | `SOPInstanceUID` | (0008,0018) | Instance |
| `modality` | `Modality` | (0008,0060) | Series |

The mapping is handled internally by the `to_dataset()` method and its helper methods:
- `_add_patient_module()`
- `_add_study_module()`
- `_add_series_module()`
- `_add_instance_module()`
- `_add_device_module()`
- `_add_image_module()`

## Extension Points

### Adding New Modalities

To add a new modality:

```python
@dataclass
class NewModalityMetadata(BaseDICOMMetadata):
    """Metadata for new modality."""
    
    # Add modality-specific fields
    custom_field: str = ""
    
    def __post_init__(self):
        """Set modality-specific defaults."""
        super().__post_init__()
        self.modality = ModalityType.OT
        # Set appropriate SOP Class UID
    
    def _add_image_module(self, ds: Dataset):
        """Add modality-specific attributes."""
        super()._add_image_module(ds)
        
        # Add custom DICOM tags
        if self.custom_field:
            ds.CustomTag = self.custom_field
```

### Adding Custom Fields

To add custom fields to existing DTOs, subclass them:

```python
@dataclass
class CustomRadiographMetadata(RadiographMetadata):
    """Extended radiograph metadata."""
    
    institution_name: str = ""
    
    def _add_study_module(self, ds: Dataset):
        """Override to add institution."""
        super()._add_study_module(ds)
        if self.institution_name:
            ds.InstitutionName = self.institution_name[:64]
```

## Django Integration Best Practices

### 1. Create a Conversion Service

```python
# myapp/services/dicom_converter.py
from bfd9000_dicom import RadiographMetadata, PatientSex

class DICOMConversionService:
    """Service for converting scans to DICOM."""
    
    @staticmethod
    def create_metadata_from_scan(scan):
        """Create DICOM metadata from scan model."""
        return RadiographMetadata(
            patient_id=scan.patient.study_id,
            patient_sex=PatientSex[scan.patient.sex],
            patient_age=f"{scan.patient.age_months}M",
            # ... other fields
        )
    
    @classmethod
    def convert_to_dicom(cls, scan, output_path):
        """Full conversion pipeline."""
        metadata = cls.create_metadata_from_scan(scan)
        ds = metadata.to_dataset()
        # Add pixel data...
        ds.save_as(output_path)
        return ds
```

### 2. Store Generated UIDs

```python
# myapp/models.py
from django.db import models

class Study(models.Model):
    dicom_study_uid = models.CharField(max_length=64, blank=True)
    
class Series(models.Model):
    study = models.ForeignKey(Study)
    dicom_series_uid = models.CharField(max_length=64, blank=True)
    
class Scan(models.Model):
    series = models.ForeignKey(Series)
    dicom_sop_instance_uid = models.CharField(max_length=64, blank=True)
```

### 3. Use Celery for Async Conversion

```python
# myapp/tasks.py
from celery import shared_task
from .services import DICOMConversionService

@shared_task
def convert_scan_to_dicom(scan_id):
    """Convert scan to DICOM asynchronously."""
    scan = Scan.objects.get(id=scan_id)
    ds = DICOMConversionService.convert_to_dicom(scan, scan.dicom_path)
    
    # Update scan with generated UIDs
    scan.dicom_sop_instance_uid = ds.SOPInstanceUID
    scan.save()
```

## Testing

Example test for Django integration:

```python
# tests/test_dicom_conversion.py
from django.test import TestCase
from bfd9000_dicom import RadiographMetadata, PatientSex

class DICOMConversionTestCase(TestCase):
    def test_metadata_creation(self):
        """Test DTO creation from test data."""
        metadata = RadiographMetadata(
            patient_id="TEST001",
            patient_sex=PatientSex.M,
            patient_age="120M"
        )
        
        ds = metadata.to_dataset()
        
        self.assertEqual(ds.PatientID, "TEST001")
        self.assertEqual(ds.PatientSex, "M")
        self.assertEqual(ds.PatientAge, "120M")
        self.assertIsNotNone(ds.StudyInstanceUID)
```

## Migration from Legacy Code

The legacy `tiff2dcm.py` CLI still works. To migrate to DTOs:

### Before (Legacy):
```python
from bfd9000_dicom.tiff2dcm import convert_tiff_to_dicom

convert_tiff_to_dicom('input.tif', 'output.dcm', with_compression=True)
```

### After (DTO):
```python
from bfd9000_dicom import RadiographMetadata, PatientSex

metadata = RadiographMetadata(
    patient_id="B0013",
    patient_sex=PatientSex.M,
    patient_age="217M"
)

ds = metadata.to_dataset()
# Add image data from TIFF...
ds.save_as('output.dcm')
```

## Future Enhancements

Potential future additions:

1. **Validation Framework**: Add `.validate()` method to check required fields
2. **Serialization**: Add `.to_dict()` and `.from_dict()` for JSON serialization
3. **Converter Classes**: Create dedicated converter classes per modality
4. **Pixel Data Handling**: Integrate image loading directly into DTOs
5. **DICOM Templates**: Pre-configured DTOs for common use cases

## Summary

The DTO architecture provides:
- ✅ Django-idiomatic interface
- ✅ Type-safe metadata handling
- ✅ Extensible for multiple modalities
- ✅ Clear DICOM tag mapping
- ✅ Easy integration with Django ORM
- ✅ Backward compatible with legacy code

For questions or contributions, see the main README.md or contact the development team.
