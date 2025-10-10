"""
Photograph converter for JPEG/PNG images to DICOM.

This module handles conversion of visible light photographs
into DICOM Visible Light Photographic Image Storage format.
"""
import logging

logger = logging.getLogger(__name__)


class PhotographConverter:
    """
    Converter for photographs (JPEG/PNG) to DICOM format.
    
    This converter is designed for visible light photographs,
    such as clinical photography or intraoral photos.
    """
    
    @staticmethod
    def convert(image_path, dicom_path, metadata=None):
        """
        Convert a photograph to DICOM format.
        
        Args:
            image_path: Path to input image file (JPEG/PNG)
            dicom_path: Path where DICOM file should be saved
            metadata: Optional PhotographMetadata object with DICOM metadata
            
        Raises:
            NotImplementedError: This feature is not yet implemented
        """
        logger.warning("Photograph conversion is not yet implemented")
        raise NotImplementedError(
            "Photograph to DICOM conversion is planned for future release. "
            "This will support DICOM Visible Light Photographic Image Storage."
        )
