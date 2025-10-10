"""
Surface model converter for STL files to DICOM.

This module handles conversion of 3D surface models (STL format)
into DICOM Encapsulated STL Storage format.
"""
import logging

logger = logging.getLogger(__name__)


class SurfaceConverter:
    """
    Converter for 3D surface models (STL) to DICOM format.
    
    This converter is designed for 3D surface scans and models,
    such as facial scans or dental models.
    """
    
    @staticmethod
    def convert(stl_path, dicom_path, metadata=None):
        """
        Convert an STL surface model to DICOM format.
        
        Args:
            stl_path: Path to input STL file
            dicom_path: Path where DICOM file should be saved
            metadata: Optional SurfaceMetadata object with DICOM metadata
            
        Raises:
            NotImplementedError: This feature is not yet implemented
        """
        logger.warning("Surface conversion is not yet implemented")
        raise NotImplementedError(
            "STL to DICOM conversion is planned for future release. "
            "This will support DICOM Encapsulated STL Storage."
        )
