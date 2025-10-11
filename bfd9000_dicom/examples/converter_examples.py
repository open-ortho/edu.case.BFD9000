"""Examples and CLI entry point for the converter architecture.

This module doubles as:

1. A CLI utility that accepts a file path, auto-detects the converter,
   derives metadata from the Bolton Brush filename, and writes a DICOM file.
2. A collection of illustrative examples that demonstrate how the router
   behaves for various scenarios. Pass ``--demo`` (or no arguments) to run
   the examples interactively.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Callable, Dict, Tuple

from pydicom.uid import generate_uid

from bfd9000_dicom import (
    BaseDICOMMetadata,
    RadiographMetadata,
    DocumentMetadata,
    PhotographMetadata,
    PatientSex,
    ModalityType,
    ConversionType,
    BurnedInAnnotation,
    get_converter_for_file,
    convert_to_dicom,
    UnsupportedFileTypeError,
)
from bfd9000_dicom.core.utils import extract_metadata_from_filename


MetadataBuilder = Callable[[str], BaseDICOMMetadata]


def _safe_patient_sex(raw_value: str) -> PatientSex:
    """Best effort conversion from single-letter code to :class:`PatientSex`."""
    try:
        return PatientSex(raw_value)
    except ValueError:
        return PatientSex.U


def _extract_basic_metadata(file_path: str) -> Tuple[str, str, PatientSex, str]:
    """Pull Bolton Brush data from filename and normalise the patient sex."""
    patient_id, image_type, patient_sex, formatted_age = extract_metadata_from_filename(
        file_path)
    return patient_id, image_type, _safe_patient_sex(patient_sex), formatted_age


def _build_radiograph_metadata(file_path: str) -> RadiographMetadata:
    patient_id, image_type, patient_sex, formatted_age = _extract_basic_metadata(
        file_path)
    return RadiographMetadata(
        patient_id=patient_id,
        patient_sex=patient_sex,
        patient_age=formatted_age,
        image_laterality=image_type,
        conversion_type=ConversionType.DF,
        burned_in_annotation=BurnedInAnnotation.YES,
    )


def _build_photograph_metadata(file_path: str) -> PhotographMetadata:
    patient_id, _image_type, patient_sex, formatted_age = _extract_basic_metadata(
        file_path)
    return PhotographMetadata(
        patient_id=patient_id,
        patient_sex=patient_sex,
        patient_age=formatted_age,
    )


def _build_document_metadata(file_path: str) -> DocumentMetadata:
    patient_id, _image_type, patient_sex, formatted_age = _extract_basic_metadata(
        file_path)
    return DocumentMetadata(
        patient_id=patient_id,
        patient_sex=patient_sex,
        patient_age=formatted_age,
        document_title=Path(file_path).stem.replace('_', ' ').title(),
    )


METADATA_BUILDERS: Dict[str, MetadataBuilder] = {
    '.tif': _build_radiograph_metadata,
    '.tiff': _build_radiograph_metadata,
    '.png': _build_radiograph_metadata,
    '.jpg': _build_photograph_metadata,
    '.jpeg': _build_photograph_metadata,
    '.pdf': _build_document_metadata,
}


def _get_metadata_for_file(file_path: str) -> BaseDICOMMetadata:
    extension = Path(file_path).suffix.lower()
    builder = METADATA_BUILDERS.get(extension)
    if builder is None:
        supported = ', '.join(sorted(METADATA_BUILDERS))
        raise UnsupportedFileTypeError(
            f"No metadata builder registered for '{extension}'. "
            f"Supported metadata builders: {supported}"
        )
    return builder(file_path)


def _default_output_path(input_path: Path) -> Path:
    return input_path.with_suffix('.dcm')


def convert_file(input_path: str, output_path: str | None, compression: bool) -> Path:
    """Convert a file to DICOM using auto-detected metadata and converter."""
    input_path_obj = Path(input_path)
    if not input_path_obj.exists():
        raise FileNotFoundError(f"Input file not found: {input_path_obj}")

    # Ensure the file type is supported before doing any heavy work
    converter_cls = get_converter_for_file(str(input_path_obj))

    metadata = _get_metadata_for_file(str(input_path_obj))
    destination = Path(
        output_path) if output_path else _default_output_path(input_path_obj)
    destination.parent.mkdir(parents=True, exist_ok=True)

    dataset = convert_to_dicom(
        metadata=metadata,
        input_path=str(input_path_obj),
        output_path=str(destination),
        compression=compression,
    )

    print(f"✓ Used {converter_cls.__name__} with {metadata.__class__.__name__}")
    print(f"  - Patient ID: {metadata.patient_id}")
    print(f"  - Patient Sex: {metadata.patient_sex.value}")
    print(f"  - Patient Age: {metadata.patient_age}")
    print(
        f"  - Compression: {'JPEG2000 Lossless' if compression else 'Uncompressed'}")
    sop_instance_uid = getattr(dataset, 'SOPInstanceUID', 'unknown')
    print(f"  - SOP Instance UID: {sop_instance_uid}")

    if destination.exists():
        print(f"✓ DICOM file written to: {destination}")
    else:
        print("⚠ Conversion produced a dataset but did not write a file.")

    # Return path in case callers need it
    return destination


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Auto-convert Bolton Brush files to DICOM using the router. "
            "Provide an input file to perform the conversion or run with no "
            "arguments/--demo to see illustrative examples."
        )
    )
    parser.add_argument(
        'input_path',
        nargs='?',
        help='Path to the source file (TIFF, PNG, JPEG, PDF, ...).',
    )
    parser.add_argument(
        '-o',
        '--output',
        dest='output_path',
        help='Optional path for the generated DICOM file (defaults to <input>.dcm).',
    )
    parser.add_argument(
        '--no-compression',
        action='store_true',
        help='Disable JPEG2000 compression for image-based conversions.',
    )
    parser.add_argument(
        '--demo',
        action='store_true',
        help='Run the interactive examples instead of converting a file.',
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.demo or args.input_path is None:
        run_examples()
        return

    try:
        convert_file(
            input_path=args.input_path,
            output_path=args.output_path,
            compression=not args.no_compression,
        )
    except FileNotFoundError as exc:
        parser.error(str(exc))
    except UnsupportedFileTypeError as exc:
        parser.error(str(exc))
    except ValueError as exc:
        parser.error(f"Failed to parse metadata from filename: {exc}")


def run_examples() -> None:
    print("\n" + "=" * 60)
    print("BFD9000 DICOM - Converter Demonstrations")
    print("=" * 60)
    example_simple_conversion()
    example_multi_series_cephalograms()
    example_different_file_types()
    example_compression_options()
    example_query_converter()
    example_without_saving()
    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)


def example_simple_conversion():
    """
    Example 1: Simple conversion using the router.

    The router automatically picks the right converter based on file extension.
    """
    print("\n" + "="*60)
    print("Example 1: Simple Automatic Conversion")
    print("="*60)

    # Create metadata
    _metadata = RadiographMetadata(
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
    print("\nPA Ceph:")
    print(f"  - Instance: {pa_metadata.instance_number}")
    print(f"  - Orientation: {pa_metadata.patient_orientation}")
    print("\nLateral Ceph:")
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

    _metadata = RadiographMetadata(
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
        except UnsupportedFileTypeError as exc:
            print(f"✗ {filename:20s} → {exc}")


def example_without_saving():
    """
    Example 6: Convert without saving (for testing or inspection).

    Shows how to get a Dataset without saving to disk.
    """
    print("\n" + "="*60)
    print("Example 6: Convert Without Saving")
    print("="*60)

    _metadata = RadiographMetadata(
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
    main()
