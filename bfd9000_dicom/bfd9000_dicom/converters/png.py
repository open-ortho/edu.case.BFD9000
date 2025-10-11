"""
PNG to DICOM converter.

Handles conversion of PNG images to DICOM format with pixel data.
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


class PNGConverter(BaseConverter):
    """
    Converter for PNG images to DICOM format.
    
    PNG files are raster images that can contain grayscale or RGB data.
    The converter handles color space conversion and optional compression.
    """
    
    @staticmethod
    def convert(
        metadata: BaseDICOMMetadata,
        input_path: str,
        output_path: Optional[str] = None,
        compression: bool = True
    ) -> Dataset:
        """
        Convert a PNG image to DICOM format.
        
        Args:
            metadata: DICOM metadata DTO
            input_path: Path to input PNG file
            output_path: Optional path to save DICOM file
            compression: If True, use JPEG2000 lossless. If False, uncompressed.
        
        Returns:
            Complete DICOM Dataset with pixel data
            
        Raises:
            ConversionError: If PNG cannot be processed
        """
        # Validate input
        input_file = PNGConverter._validate_input_file(input_path)
        
        try:
            # Get base dataset from metadata
            ds = metadata.to_dataset()
            
            # Load and process PNG image
            with Image.open(input_file) as img:
                # Extract DPI if available
                dpi_info = img.info.get('dpi')
                if dpi_info:
                    dpi_horizontal, dpi_vertical = dpi_info
                    pixel_spacing = PNGConverter._dpi_to_pixel_spacing(
                        dpi_horizontal, dpi_vertical
                    )
                    if not hasattr(ds, 'PixelSpacing') or not ds.PixelSpacing:
                        ds.PixelSpacing = pixel_spacing
                        ds.NominalScannedPixelSpacing = pixel_spacing
                        ds.PixelSpacingCalibrationType = "GEOMETRY"
                
                # Convert color modes
                mode = img.mode
                if mode in ['RGBA', 'P']:
                    img = img.convert('RGB')
                elif mode == 'LA':
                    img = img.convert('L')
                elif mode not in ['L', 'RGB']:
                    raise ConversionError(f"Unsupported PNG mode: {mode}")
                
                # Convert to numpy array (PNG is typically 8-bit)
                img_array = np.array(img)
                
                # Add pixel data
                PNGConverter._add_pixel_data(ds, img_array, compression)
            
            # Save if output path provided
            if output_path:
                PNGConverter._save_dataset(ds, output_path)
                logger.info(f"Saved DICOM file: {output_path}")
            
            return ds
            
        except Exception as e:
            logger.error(f"Error converting PNG {input_path}: {e}")
            raise ConversionError(f"Failed to convert PNG: {e}") from e
    
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
        
        # PNG is typically 8-bit
        bits_allocated = 8 if img_array.dtype == np.uint8 else 16
        ds.PixelRepresentation = 0
        ds.BitsAllocated = bits_allocated
        ds.BitsStored = bits_allocated
        ds.HighBit = bits_allocated - 1
        
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
