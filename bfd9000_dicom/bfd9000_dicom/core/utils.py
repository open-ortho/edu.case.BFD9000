""" Utility functions."""
import os
import logging

logger = logging.getLogger(__name__)

@staticmethod
def extract_metadata_from_filename(file_path: str) -> tuple:
    """
    Extract metadata from Bolton Brush filename format.
    
    Bolton Brush filenames follow pattern: B0013LM18y01m.tif
    - B0013: Patient ID
    - L: Image type
    - M: Sex
    - 18y01m: Age (18 years 1 month)
    
    Args:
        file_path: Path to the TIFF file
        
    Returns:
        tuple: (patient_id, image_type, patient_sex, formatted_age)
    """
    file_name = os.path.basename(file_path)
    # Extract data from file name
    patient_id = file_name[0:5]
    image_type = file_name[5]
    patient_sex = file_name[6]
    patient_age = file_name[7:13]  # Assume format is 'AAyBBm'

    # Parse age from format 'AAyBBm' (e.g., '23y02m') to total months 'nnnM'
    years = int(patient_age[:2])
    months = int(patient_age[3:5])
    total_months = years * 12 + months

    # Format total months as zero-padded string 'nnnM'
    formatted_age = f"{total_months:03}M"  # Zero-padded to 3 digits
    logger.debug(f"Patient Age: [{formatted_age}]")
    logger.debug(f"PatientId: [{patient_id}]")
    logger.debug(f"Image Type: [{image_type}]")
    logger.debug(f"PatientSex: [{patient_sex}]")

    return patient_id, image_type, patient_sex, formatted_age

