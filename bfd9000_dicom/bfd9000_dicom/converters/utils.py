"""
Utility functions for Bolton Brush specific conversions.
"""
import os
from typing import Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from bfd9000_dicom.models import RadiographMetadata


def extract_bolton_brush_data_from_filename(file_path: str) -> Tuple[str, str, str, str]:
    """
    Extract patient data from Bolton Brush filename format.

    Filename format: BXXXXYSAADBBM.ext expanded: BXXXX Y S AA D BB M.ext
    Where:
        BXXXX = patient ID (B0001, etc.) - 5 chars
        Y = image type (L, P, etc.) - 1 char
        S = patient sex (M=Male, F=Female) - 1 char
        AA = zero padded number of years (00-99) - 2 chars
        D = delimiter 'y' - 1 char
        BB = zero padded number of months (01-12) - 2 chars
        M = delimiter 'm' - 1 char
        AADBMM = patient age in format f'{number_of_years:02d}y{number_of_months:02d}m' - 6 chars

    Args:
        file_path: Path to the file

    Returns:
        Tuple of (patient_id, patient_sex, patient_age_formatted, image_type)

    Example:
        "B0001LM16y05m.tiff" -> ("B0001", "M", "197M", "L")
    """
    file_name = os.path.basename(file_path)

    # Extract data from file name
    patient_id = file_name[0:5]  # BXXXX
    image_type = file_name[5]   # Y
    patient_sex = file_name[6]  # S
    patient_age = file_name[7:13]  # AABBMM format with y and m

    # Parse age from format 'AAyBB' or 'AAyBBm' (e.g., '15y08' or '18y01m') to total months 'nnnM'
    # Split on 'y' to get years and months parts
    if 'y' in patient_age:
        years_part, months_part = patient_age.split('y')
        # Remove 'm' suffix if present
        months_part = months_part.rstrip('m')
        years = int(years_part)
        months = int(months_part)
    else:
        # Fallback for other formats
        years = int(patient_age[:2])
        months = int(patient_age[2:4])

    total_months = years * 12 + months

    # Format total months as zero-padded string 'nnnM'
    formatted_age = f"{total_months:03d}M"

    return patient_id, patient_sex, formatted_age, image_type
