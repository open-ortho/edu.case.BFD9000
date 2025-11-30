"""
Converter router - automatically selects the right converter based on file type.

This module provides the main public API for conversions, automatically
routing to the appropriate converter based on file extension.
"""
import logging
from pathlib import Path
from typing import Optional, Type
from pydicom.dataset import Dataset

from bfd9000_dicom.models import BaseDICOMMetadata
from .base import BaseConverter, UnsupportedFileTypeError
from .tiff import TIFFConverter
from .png import PNGConverter
from .jpeg import JPEGConverter
from .pdf import PDFConverter
from .stl import STLConverter

logger = logging.getLogger(__name__)


# Mapping of file extensions to converter classes
CONVERTER_MAP = {
    # TIFF variants
    '.tif': TIFFConverter,
    '.tiff': TIFFConverter,
    
    # PNG
    '.png': PNGConverter,
    
    # JPEG variants
    '.jpg': JPEGConverter,
    '.jpeg': JPEGConverter,
    
    # PDF
    '.pdf': PDFConverter,
    
    # STL (3D models)
    '.stl': STLConverter,
    # '.obj': OBJConverter,  # Future: Wavefront OBJ format
}


def get_converter_for_file(file_path: str) -> Type[BaseConverter]:
    """
    Get the appropriate converter class for a file based on its extension.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Converter class for the file type
        
    Raises:
        UnsupportedFileTypeError: If no converter exists for this file type
    """
    path = Path(file_path)
    extension = path.suffix.lower()
    
    converter = CONVERTER_MAP.get(extension)
    if converter is None:
        supported = ', '.join(CONVERTER_MAP.keys())
        raise UnsupportedFileTypeError(
            f"Unsupported file type: {extension}. "
            f"Supported types: {supported}"
        )
    
    return converter


def convert_to_dicom(
    metadata: BaseDICOMMetadata,
    input_path: str,
    output_path: Optional[str] = None,
    compression: bool = True
) -> Dataset:
    """
    Convert any supported file type to DICOM format.
    
    This is the main public API for conversions. It automatically detects
    the file type and routes to the appropriate converter.
    
    Args:
        metadata: DICOM metadata DTO (any subclass of BaseDICOMMetadata)
        input_path: Path to input file (TIFF, PNG, JPEG, PDF, STL, etc.)
        output_path: Optional path to save DICOM file. If None, doesn't save.
        compression: If True, use JPEG2000 lossless for images.
                    If False, use uncompressed encoding.
                    (Ignored for PDF/STL which have their own encoding)
    
    Returns:
        Complete DICOM Dataset ready to save or use
        
    Raises:
        UnsupportedFileTypeError: If file type is not supported
        ConversionError: If conversion fails
        
    Example:
        >>> from bfd9000_dicom import RadiographMetadata, PatientSex
        >>> from bfd9000_dicom.converters import convert_to_dicom
        >>> 
        >>> metadata = RadiographMetadata(
        ...     patient_id="B0013",
        ...     patient_sex=PatientSex.M,
        ...     patient_age="217M"
        ... )
        >>> 
        >>> # Automatically picks TIFFConverter
        >>> ds = convert_to_dicom(metadata, "xray.tiff", "output.dcm")
        >>> 
        >>> # Automatically picks PNGConverter
        >>> ds = convert_to_dicom(metadata, "xray.png", "output.dcm")
        >>> 
        >>> # Automatically picks PDFConverter
        >>> from bfd9000_dicom import DocumentMetadata
        >>> doc_meta = DocumentMetadata(
        ...     patient_id="B0013",
        ...     patient_sex=PatientSex.M,
        ...     patient_age="217M",
        ...     document_title="Consent Form"
        ... )
        >>> ds = convert_to_dicom(doc_meta, "consent.pdf", "consent.dcm")
    """
    # Get the appropriate converter
    converter_class = get_converter_for_file(input_path)
    
    logger.info(
        f"Converting {input_path} using {converter_class.__name__} "
        f"(compression={compression})"
    )
    
    # Perform conversion
    return converter_class.convert(
        metadata=metadata,
        input_path=input_path,
        output_path=output_path,
        compression=compression
    )
