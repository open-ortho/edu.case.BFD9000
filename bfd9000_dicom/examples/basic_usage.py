"""
Example usage of bfd9000_dicom models and converters.

This demonstrates how a Django application would use the DTOs
to convert images to DICOM format, and how to use the converters
for various image types.
"""

from bfd9000_dicom import (
    RadiographMetadata,
    PatientSex,
    ConversionType,
    BurnedInAnnotation,
)

from bfd9000_dicom.extractors import extract_metadata_from_filename, MetadataExtractionError

def example_basic_radiograph():
    """Basic example: Create DICOM metadata for a radiograph."""

    # Create metadata (similar to Django model instantiation)
    metadata = RadiographMetadata(
        # Required patient information
        patient_id="B0013",
        patient_sex=PatientSex.M,
        patient_age="217M",  # 217 months = 18 years 1 month

        # Optional patient information
        patient_name="B0013^Bolton Study Subject",

        # Study information (UIDs auto-generated if not provided)
        study_id="1",

        # Device information
        secondary_capture_device_manufacturer="Vidar",
        secondary_capture_device_manufacturer_model_name="DosimetryPRO Advantage",
        secondary_capture_device_software_versions="49.7",

        # Radiograph-specific
        conversion_type=ConversionType.DF,  # Digitized Film
        burned_in_annotation=BurnedInAnnotation.YES,
        image_laterality="U",  # Unknown
    )

    # Convert to DICOM dataset (similar to Django's .save())
    ds = metadata.to_dataset()

    # At this point, ds is a pydicom Dataset with all metadata
    # You would then add pixel data and save:
    # ds.save_as("output.dcm")

    print("Created DICOM dataset:")
    print(f"  Patient ID: {ds.PatientID}")
    print(f"  Patient Sex: {ds.PatientSex}")
    print(f"  Patient Age: {ds.PatientAge}")
    print(f"  Study UID: {ds.StudyInstanceUID}")
    print(f"  Series UID: {ds.SeriesInstanceUID}")
    print(f"  SOP Instance UID: {ds.SOPInstanceUID}")
    print(f"  Modality: {ds.Modality}")

    return ds


def example_django_integration():
    """
    Example showing how this would integrate with Django models.

    Assume you have Django models like:
        class Patient(models.Model):
            study_id = models.CharField(max_length=10)
            sex = models.CharField(max_length=1)
            age_months = models.IntegerField()

        class RadiographScan(models.Model):
            patient = models.ForeignKey(Patient)
            file = models.FileField()
            study_uid = models.CharField(max_length=64)
            series_uid = models.CharField(max_length=64)
    """

    # Simulated Django model data
    class MockPatient:
        study_id = "B0013"
        sex = "M"
        age_months = 217

    class MockScan:
        patient = MockPatient()
        study_uid = None  # Will be auto-generated
        series_uid = None  # Will be auto-generated

    scan = MockScan()

    # Create DICOM metadata from Django model
    metadata = RadiographMetadata(
        patient_id=scan.patient.study_id,
        patient_sex=PatientSex[scan.patient.sex],
        patient_age=f"{scan.patient.age_months}M",
        study_instance_uid=scan.study_uid,
        series_instance_uid=scan.series_uid,
        secondary_capture_device_manufacturer="Vidar",
        secondary_capture_device_manufacturer_model_name="DosimetryPRO Advantage",
    )

    # Convert to DICOM
    ds = metadata.to_dataset()

    # Save generated UIDs back to Django model
    scan.study_uid = ds.StudyInstanceUID
    scan.series_uid = ds.SeriesInstanceUID
    # scan.save()  # In real Django app

    print("\nDjango Integration Example:")
    print(f"  Generated Study UID: {scan.study_uid}")
    print(f"  Generated Series UID: {scan.series_uid}")

    return ds


def example_filename_parsing():
    """
    Example: Parse filename to create metadata.

    Bolton Brush filenames follow pattern: B0013LM18y01m.tif
    - B0013: Patient ID
    - L: Image type
    - M: Sex
    - 18y01m: Age (18 years 1 month)
    """
    filename = "B0013LM18y01m.tif"

    try:
        result = extract_metadata_from_filename(filename)
    except MetadataExtractionError as exc:
        print(f"Failed to extract metadata from {filename}: {exc}")
        return None
    sex = PatientSex(result.patient_sex)

    # Create metadata
    metadata = RadiographMetadata(
        patient_id=result.patient_id,
        patient_sex=sex,
        patient_age=result.patient_age,
        secondary_capture_device_manufacturer="Vidar",
        secondary_capture_device_manufacturer_model_name="DosimetryPRO Advantage",
    )

    ds = metadata.to_dataset()

    print(f"\nParsed from filename: {filename}")
    print(f"  Patient ID: {result.patient_id}")
    print(f"  Sex: {sex.value}")
    print(f"  Age: {result.patient_age}")

    return ds


def example_radiograph_converter():
    """
    Example: Use RadiographConverter to convert a TIFF file.
    
    This shows the simplest way to convert a radiograph TIFF to DICOM.
    """
    # Method 1: Using the converter directly (simplest approach)
    # RadiographConverter.convert(
    #     tiff_path="path/to/B0013LM18y01m.tif",
    #     dicom_path="path/to/output.dcm",
    #     with_compression=True
    # )
    
    # Method 2: Using metadata from filename
    filename = "B0013LM18y01m.tif"
    try:
        result = extract_metadata_from_filename(filename)
    except MetadataExtractionError as exc:
        print(f"Failed to extract metadata from {filename}: {exc}")
        return
    sex = PatientSex(result.patient_sex)
    
    print("\nRadiograph Converter Example:")
    print(f"  Extracted from {filename}:")
    print(f"    Patient ID: {result.patient_id}")
    print(f"    Image Type: {result.image_type}")
    print(f"    Sex: {sex.value}")
    print(f"    Age: {result.patient_age}")
    print("  Ready to convert to DICOM!")


if __name__ == "__main__":
    print("=" * 60)
    print("BFD9000 DICOM Models - Usage Examples")
    print("=" * 60)

    print("\n1. Basic Radiograph Example")
    print("-" * 60)
    example_basic_radiograph()

    print("\n2. Django Integration Example")
    print("-" * 60)
    example_django_integration()

    print("\n3. Filename Parsing Example")
    print("-" * 60)
    example_filename_parsing()

    print("\n4. Radiograph Converter Example")
    print("-" * 60)
    example_radiograph_converter()

    print("\n" + "=" * 60)
    print("All examples completed successfully!")
    print("=" * 60)
