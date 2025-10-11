"""
Radiograph converter for TIFF/PNG scanned X-ray images to DICOM.

This module handles conversion of scanned radiographic images (e.g., from film scanners)
into DICOM Secondary Capture format with appropriate metadata.
"""
import json
import logging
from pydicom.dataset import Dataset
from pydicom.uid import SecondaryCaptureImageStorage, generate_uid
from bfd9000_dicom.core.dicom_builder import build_file_meta, add_common_bolton_brush_tags, add_image_module
from bfd9000_dicom.core.utils import extract_metadata_from_filename

logger = logging.getLogger(__name__)


class RadiographConverter:
    """
    Converter for radiographic images (TIFF/PNG) to DICOM format.
    
    This converter is designed for scanned film radiographs, particularly
    those from the Bolton Brush Growth Study collection.
    """
    
    @staticmethod
    def build_dicom_without_image(file_path) -> Dataset:
        """
        Build a DICOM dataset with metadata but without pixel data.
        
        Args:
            file_path: Path to the image file (used for metadata extraction)
            
        Returns:
            Dataset: DICOM dataset with metadata
        """
        # Create the DICOM Dataset
        ds = Dataset()
        ds.file_meta = build_file_meta()
        ds.PatientID, image_type, ds.PatientSex, ds.PatientAge = extract_metadata_from_filename(
            file_path)
        ds.StudyInstanceUID = generate_uid()
        ds.SeriesInstanceUID = generate_uid()
        ds.SOPInstanceUID = generate_uid()
        ds.SOPClassUID = SecondaryCaptureImageStorage

        ds.StudyID = '1'

        ds.SeriesNumber = '1'
        ds.InstanceNumber = '1'
        ds.ImageComments = 'Converted from TIFF'

        # Additional DICOM attributes to address missing elements
        ds.AccessionNumber = ''  # Use the actual accession number

        # Conditional elements (only necessary under certain conditions)
        # These should be set based on the actual image and its metadata, and may be omitted if not applicable.
        ds.ImageLaterality = 'U'
        ds.PatientOrientation = 'AF'
        return ds

    @staticmethod
    def load_dataset_from_file(json_file_path) -> Dataset:
        """
        Load a DICOM dataset from a JSON file.
        
        Args:
            json_file_path: Path to JSON file containing DICOM metadata
            
        Returns:
            Dataset: DICOM dataset loaded from JSON
        """
        with open(json_file_path, 'r') as file:
            json_data = json.load(file)
        ds = Dataset.from_json(json_data)
        ds.file_meta = build_file_meta()
        return ds

    @staticmethod
    def convert(tiff_path, dicom_path, dicom_json=None, with_compression=True):
        """
        Convert a TIFF radiograph to DICOM format.
        
        Args:
            tiff_path: Path to input TIFF file
            dicom_path: Path where DICOM file should be saved
            dicom_json: Optional path to JSON file with DICOM metadata
            with_compression: Whether to use JPEG2000 compression (default: True)
            
        Raises:
            ValueError: If the dataset cannot be created
        """
        # Create and populate DICOM dataset with image data and metadata
        if dicom_json:
            ds = RadiographConverter.load_dataset_from_file(dicom_json)
        else:
            ds = RadiographConverter.build_dicom_without_image(tiff_path)

        ds = add_image_module(ds, tiff_path, with_compression)

        if ds is None:
            raise ValueError("DICOM dataset (ds) is None before calling add_common_bolton_brush_tags.")
        add_common_bolton_brush_tags(ds)

        # Save the DICOM file
        ds.save_as(dicom_path, write_like_original=False)
        print(f"Saved DICOM file at {dicom_path}")


# Backward compatibility alias
convert_tiff_to_dicom = RadiographConverter.convert
build_dicom_without_image = RadiographConverter.build_dicom_without_image
load_dataset_from_file = RadiographConverter.load_dataset_from_file
