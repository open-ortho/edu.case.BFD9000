"""
Example usage of the new converter architecture.

This demonstrates the router-based converter system that automatically
selects the right converter based on file type.
"""

from bfd9000_dicom import (
    RadiographMetadata,
    DocumentMetadata,
    PhotographMetadata,
    PatientSex,
    ModalityType,
    ConversionType,
    BurnedInAnnotation,
    convert_to_dicom,
    get_converter_for_file,
)
from pydicom.uid import generate_uid


def example_simple_conversion():
    """
    Example 1: Simple conversion using the router.
    
    The router automatically picks the right converter based on file extension.
    """
    print("\n" + "="*60)
    print("Example 1: Simple Automatic Conversion")
    print("="*60)
    
    # Create metadata
    metadata = RadiographMetadata(
        patient_id="B0013",
        patient_sex=PatientSex.M,
        patient_age="217M",
    )
    
    # Router automatically picks TIFFConverter
    # ds = convert_to_dicom(metadata, "xray.tiff", "output.dcm", compression=True)
    print("✓ Would convert xray.tiff using TIFFConverter")
    
    # Router automatically picks PNGConverter
    # ds = convert_to_dicom(metadata, "xray.png", "output.dcm", compression=True)
    print("✓ Would convert xray.png using PNGConverter")
    
    # Router automatically picks JPEGConverter
    # ds = convert_to_dicom(metadata, "photo.jpg", "output.dcm", compression=False)
    print("✓ Would convert photo.jpg using JPEGConverter")


def example_multi_series_cephalograms():
    """
    Example 2: Multiple images in the same series (PA and Lateral cephalograms).
    
    Shows how to maintain consistent UIDs across multiple images.
    """
    print("\n" + "="*60)
    print("Example 2: Multi-Image Series (PA + Lateral Cephs)")
    print("="*60)
    
    # Generate UIDs for the series
    study_uid = generate_uid()
    series_uid = generate_uid()
    
    # PA Cephalogram (Instance 1)
    pa_metadata = RadiographMetadata(
        patient_id="B0013",
        patient_sex=PatientSex.M,
        patient_age="217M",
        study_instance_uid=study_uid,
        series_instance_uid=series_uid,
        series_number="1",
        instance_number="1",
        patient_orientation="PA",
        conversion_type=ConversionType.DF,
        burned_in_annotation=BurnedInAnnotation.YES,
    )
    
    # Lateral Cephalogram (Instance 2)
    lateral_metadata = RadiographMetadata(
        patient_id="B0013",
        patient_sex=PatientSex.M,
        patient_age="217M",
        study_instance_uid=study_uid,         # Same study
        series_instance_uid=series_uid,       # Same series
        series_number="1",
        instance_number="2",                  # Different instance
        patient_orientation="L",
        conversion_type=ConversionType.DF,
        burned_in_annotation=BurnedInAnnotation.YES,
    )
    
    print(f"Study UID: {study_uid}")
    print(f"Series UID: {series_uid}")
    print(f"\nPA Ceph:")
    print(f"  - Instance: {pa_metadata.instance_number}")
    print(f"  - Orientation: {pa_metadata.patient_orientation}")
    print(f"\nLateral Ceph:")
    print(f"  - Instance: {lateral_metadata.instance_number}")
    print(f"  - Orientation: {lateral_metadata.patient_orientation}")
    
    # Convert both (router picks converter automatically)
    # pa_ds = convert_to_dicom(pa_metadata, "pa_ceph.tiff", "pa.dcm", compression=True)
    # lateral_ds = convert_to_dicom(lateral_metadata, "lateral_ceph.tiff", "lateral.dcm", compression=True)
    
    print("\n✓ Both images would be in the same series")


def example_different_file_types():
    """
    Example 3: Convert different file types with appropriate metadata.
    
    Shows how the same converter API works for all file types.
    """
    print("\n" + "="*60)
    print("Example 3: Different File Types")
    print("="*60)
    
    # 1. Radiograph from TIFF
    radiograph_meta = RadiographMetadata(
        patient_id="B0013",
        patient_sex=PatientSex.M,
        patient_age="217M",
        modality=ModalityType.RG,
    )
    print("\n1. Radiograph (TIFF):")
    print(f"   Modality: {radiograph_meta.modality.value}")
    # convert_to_dicom(radiograph_meta, "xray.tiff", "xray.dcm")
    
    # 2. Photograph from JPEG
    photo_meta = PhotographMetadata(
        patient_id="B0013",
        patient_sex=PatientSex.M,
        patient_age="217M",
        # modality automatically set to XC (External-camera Photography)
    )
    print("\n2. Photograph (JPEG):")
    print(f"   Modality: {photo_meta.modality.value}")
    # convert_to_dicom(photo_meta, "intraoral.jpg", "photo.dcm")
    
    # 3. Document from PDF
    doc_meta = DocumentMetadata(
        patient_id="B0013",
        patient_sex=PatientSex.M,
        patient_age="217M",
        document_title="Informed Consent",
        # modality automatically set to DOC
    )
    print("\n3. Document (PDF):")
    print(f"   Modality: {doc_meta.modality.value}")
    print(f"   Title: {doc_meta.document_title}")
    # convert_to_dicom(doc_meta, "consent.pdf", "consent.dcm")


def example_compression_options():
    """
    Example 4: Using different compression options.
    
    Shows the difference between compressed and uncompressed encoding.
    """
    print("\n" + "="*60)
    print("Example 4: Compression Options")
    print("="*60)
    
    metadata = RadiographMetadata(
        patient_id="B0013",
        patient_sex=PatientSex.M,
        patient_age="217M",
    )
    
    # Compressed (JPEG2000 Lossless) - smaller file size
    print("\n1. With compression (JPEG2000 Lossless):")
    print("   - Transfer Syntax: JPEG2000Lossless")
    print("   - Smaller file size")
    print("   - All DICOM viewers support this")
    # ds = convert_to_dicom(metadata, "xray.tiff", "compressed.dcm", compression=True)
    
    # Uncompressed (ExplicitVRLittleEndian) - larger file, faster access
    print("\n2. Without compression (Uncompressed):")
    print("   - Transfer Syntax: ExplicitVRLittleEndian")
    print("   - Larger file size")
    print("   - Required baseline transfer syntax")
    print("   - Fastest to read/write")
    # ds = convert_to_dicom(metadata, "xray.tiff", "uncompressed.dcm", compression=False)


def example_query_converter():
    """
    Example 5: Query which converter will be used.
    
    Shows how to check which converter will be used before conversion.
    """
    print("\n" + "="*60)
    print("Example 5: Query Converter")
    print("="*60)
    
    test_files = [
        "image.tiff",
        "scan.png",
        "photo.jpg",
        "document.pdf",
        "model.stl",
    ]
    
    for filename in test_files:
        try:
            converter = get_converter_for_file(filename)
            print(f"✓ {filename:20s} → {converter.__name__}")
        except Exception as e:
            print(f"✗ {filename:20s} → {e}")


def example_without_saving():
    """
    Example 6: Convert without saving (for testing or inspection).
    
    Shows how to get a Dataset without saving to disk.
    """
    print("\n" + "="*60)
    print("Example 6: Convert Without Saving")
    print("="*60)
    
    metadata = RadiographMetadata(
        patient_id="B0013",
        patient_sex=PatientSex.M,
        patient_age="217M",
    )
    
    # Don't provide output_path - dataset is returned but not saved
    # ds = convert_to_dicom(metadata, "xray.tiff", output_path=None, compression=True)
    # 
    # # Now you can inspect or modify the dataset
    # print(f"Patient ID: {ds.PatientID}")
    # print(f"Modality: {ds.Modality}")
    # print(f"Image size: {ds.Rows} x {ds.Columns}")
    # 
    # # Save later if needed
    # ds.save_as("custom_path.dcm")
    
    print("✓ Dataset returned without saving")
    print("  Can inspect, modify, then save manually")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("BFD9000 DICOM - New Converter Architecture Examples")
    print("="*60)
    
    example_simple_conversion()
    example_multi_series_cephalograms()
    example_different_file_types()
    example_compression_options()
    example_query_converter()
    example_without_saving()
    
    print("\n" + "="*60)
    print("All examples completed!")
    print("="*60)
