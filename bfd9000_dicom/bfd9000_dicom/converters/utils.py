"""
Utility functions for Bolton Brush specific conversions.
"""
import os
from typing import Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from bfd9000_dicom.models import RadiographMetadata


def extract_bolton_brush_data_from_filename(file_path: str) -> Tuple[str, str, str]:
    """
    Extract patient data from Bolton Brush filename format.
    
    Filename format: BXXXXXYZZZZZZ.ext
    Where:
        BXXXXX = patient ID (B00001, etc.)
        Y = patient sex (1=Male, 2=Female)
        ZZZZZZ = patient age in 'AAyBBm' format
    
    Args:
        file_path: Path to the file
        
    Returns:
        Tuple of (patient_id, patient_sex, patient_age_formatted)
        
    Example:
        "B00013123006.tiff" -> ("B00013", "M", "2306M")
    """
    file_name = os.path.basename(file_path)
    
    # Extract data from file name
    patient_id = file_name[0:6]  # BXXXXX
    patient_sex_code = file_name[6]  # 1 or 2
    patient_age = file_name[7:13]  # AAYBBM format
    
    # Convert sex code to DICOM format
    patient_sex = "M" if patient_sex_code == "1" else "F"
    
    # Parse age from format 'AAyBBm' (e.g., '23y02m') to total months 'nnnM'
    years = int(patient_age[:2])
    months = int(patient_age[3:5])
    total_months = years * 12 + months
    
    # Format total months as zero-padded string 'nnnM'
    formatted_age = f"{total_months:03d}M"
    
    return patient_id, patient_sex, formatted_age


def load_radiograph_metadata_from_json(json_file_path: str) -> 'RadiographMetadata':
    """
    Load RadiographMetadata from a JSON file.
    
    This provides backward compatibility with the old conversion workflow
    that stored DICOM metadata as JSON.
    
    Args:
        json_file_path: Path to JSON file containing DICOM metadata
        
    Returns:
        RadiographMetadata instance
    """
    import json
    from pydicom.dataset import Dataset
    from bfd9000_dicom.models import RadiographMetadata, PatientSex, ModalityType
    
    with open(json_file_path, 'r') as file:
        json_data = json.load(file)
    
    # Convert JSON to temporary dataset to extract values
    temp_ds = Dataset.from_json(json_data)
    
    # Map JSON values to RadiographMetadata
    # This is a best-effort mapping - not all fields may be present
    metadata = RadiographMetadata(
        patient_id=getattr(temp_ds, 'PatientID', 'UNKNOWN'),
        patient_sex=PatientSex(getattr(temp_ds, 'PatientSex', 'U')),
        patient_age=getattr(temp_ds, 'PatientAge', '000M'),
        patient_name=getattr(temp_ds, 'PatientName', None),
        study_instance_uid=getattr(temp_ds, 'StudyInstanceUID', None),
        series_instance_uid=getattr(temp_ds, 'SeriesInstanceUID', None),
        instance_number=getattr(temp_ds, 'InstanceNumber', '1'),
        patient_orientation=getattr(temp_ds, 'PatientOrientation', ''),
        image_laterality=getattr(temp_ds, 'ImageLaterality', 'U'),
    )
    
    return metadata