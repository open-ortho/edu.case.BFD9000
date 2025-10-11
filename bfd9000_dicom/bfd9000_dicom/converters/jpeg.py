"""
JPEG to DICOM converter.

Handles conversion of JPEG images to DICOM format with pixel data.
"""
import logging
from typing import Optional
import numpy as np
from PIL import Image
from pydicom.dataset import Dataset
from pydicom.uid import ExplicitVRLittleEndian, JPEG2000Lossless

from bfd9000_dicom.models import BaseDICOMMetadata
from bfd9000_dicom.core.compression import get_encapsulated_jpeg2k_pixel_data
from .base import BaseConverter, ConversionError

logger = logging.getLogger(__name__)


class JPEGConverter(BaseConverter):
    """
    Converter for JPEG images to DICOM format.
    
    JPEG files are already compressed with lossy compression. This converter
    decodes the JPEG and re-encodes to DICOM format (either uncompressed or JPEG2000).
    
    Note: For photographs, consider using the original JPEG compression rather than
    re-encoding, which would require direct JPEG encapsulation (not yet implemented).
    """
    
    @staticmethod
    def convert(
        metadata: BaseDICOMMetadata,
        input_path: str,
        output_path: Optional[str] = None,
        compression: bool = True
    ) -> Dataset:
        """
        Convert a JPEG image to DICOM format.
        
        Args:
            metadata: DICOM metadata DTO
            input_path: Path to input JPEG file
            output_path: Optional path to save DICOM file
            compression: If True, use JPEG2000 lossless. If False, uncompressed.
        
        Returns:
            Complete DICOM Dataset with pixel data
            
        Raises:
            ConversionError: If JPEG cannot be processed
        """
        # Validate input
        input_file = JPEGConverter._validate_input_file(input_path)
        
        try:
            # Get base dataset from metadata
            ds = metadata.to_dataset()
            
            # Load and process JPEG image
            with Image.open(input_file) as img:
                # JPEG doesn't typically have DPI, but check anyway
                dpi_info = img.info.get('dpi')
                if dpi_info:
                    dpi_horizontal, dpi_vertical = dpi_info
                    pixel_spacing = JPEGConverter._dpi_to_pixel_spacing(
                        dpi_horizontal, dpi_vertical
                    )
                    if not hasattr(ds, 'PixelSpacing') or not ds.PixelSpacing:
                        ds.PixelSpacing = pixel_spacing
                
                # JPEG is typically RGB or grayscale
                mode = img.mode
                if mode == 'RGBA':
                    img = img.convert('RGB')
                elif mode not in ['L', 'RGB']:
                    raise ConversionError(f"Unsupported JPEG mode: {mode}")
                
                # Convert to numpy array (JPEG is 8-bit)
                img_array = np.array(img)
                
                # Add pixel data
                JPEGConverter._add_pixel_data(ds, img_array, compression)
            
            # Save if output path provided
            if output_path:
                JPEGConverter._save_dataset(ds, output_path)
                logger.info(f"Saved DICOM file: {output_path}")
            
            return ds
            
        except Exception as e:
            logger.error(f"Error converting JPEG {input_path}: {e}")
            raise ConversionError(f"Failed to convert JPEG: {e}") from e
    
    @staticmethod
    def _add_pixel_data(ds: Dataset, img_array: np.ndarray, compression: bool) -> None:
        """Add pixel data to DICOM dataset."""
        # Determine dimensions and color
        if len(img_array.shape) == 2:
            ds.Rows, ds.Columns = img_array.shape
            ds.SamplesPerPixel = 1
            ds.PhotometricInterpretation = "MONOCHROME2"
        elif len(img_array.shape) == 3:
            ds.Rows, ds.Columns, _ = img_array.shape
            ds.SamplesPerPixel = 3
            ds.PhotometricInterpretation = "RGB"
            ds.PlanarConfiguration = 0
        else:
            raise ConversionError(f"Unsupported image shape: {img_array.shape}")
        
        # JPEG is 8-bit
        ds.PixelRepresentation = 0
        ds.BitsAllocated = 8
        ds.BitsStored = 8
        ds.HighBit = 7
        
        # Encode
        if compression:
            ds.file_meta.TransferSyntaxUID = JPEG2000Lossless
            ds.PixelData = get_encapsulated_jpeg2k_pixel_data(img_array)
            logger.debug("Encoded with JPEG2000 lossless compression")
        else:
            ds.file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
            ds.PixelData = img_array.tobytes()
            logger.debug("Encoded as uncompressed pixel data")
    
    @staticmethod
    def _dpi_to_pixel_spacing(dpi_horizontal: float, dpi_vertical: Optional[float] = None) -> list:
        """Convert DPI to DICOM pixel spacing (mm/pixel)."""
        if dpi_vertical is None:
            dpi_vertical = dpi_horizontal
        
        row_spacing = 25.4 / dpi_vertical
        column_spacing = 25.4 / dpi_horizontal
        
        return [f"{row_spacing:.6f}", f"{column_spacing:.6f}"]
