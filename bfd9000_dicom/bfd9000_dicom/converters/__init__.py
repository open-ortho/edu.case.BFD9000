"""
Converters package for converting binary files to DICOM format.

This package provides file-type-specific converters that handle the encoding
of binary data (images, documents, 3D models) into DICOM format. The converters
work with metadata DTOs from models.py to create complete DICOM datasets.

Architecture:
- Each file type (TIFF, PNG, JPEG, PDF, STL) has its own converter module
- Converters handle ONLY binary encoding, NOT metadata
- A router automatically selects the correct converter based on file extension
- All converters support a simple compression flag (True = JPEG2000 lossless, False = uncompressed)

Usage:
    from bfd9000_dicom import RadiographMetadata, PatientSex
    from bfd9000_dicom.converters import convert_to_dicom
    
    metadata = RadiographMetadata(
        patient_id="B0013",
        patient_sex=PatientSex.M,
        patient_age="217M"
    )
    
    # Router automatically picks the right converter
    convert_to_dicom(
        metadata=metadata,
        input_path="image.tiff",
        output_path="output.dcm",
        compression=True
    )
"""

from .router import convert_to_dicom, get_converter_for_file
from .tiff import TIFFConverter
from .png import PNGConverter
from .jpeg import JPEGConverter
from .pdf import PDFConverter
from .stl import STLConverter
from .utils import extract_bolton_brush_data_from_filename, load_radiograph_metadata_from_json
from .base import UnsupportedFileTypeError, ConversionError

__all__ = [
    'convert_to_dicom',
    'get_converter_for_file',
    'TIFFConverter',
    'PNGConverter',
    'JPEGConverter',
    'PDFConverter',
    'STLConverter',
    'extract_bolton_brush_data_from_filename',
    'load_radiograph_metadata_from_json',
    'UnsupportedFileTypeError',
    'ConversionError',
]
