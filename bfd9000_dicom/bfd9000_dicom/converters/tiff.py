"""
TIFF to DICOM converter.

Handles conversion of TIFF images to DICOM format with pixel data.
Supports both compressed (JPEG2000 lossless) and uncompressed encoding.
"""
import logging
from typing import Optional
import numpy as np
from PIL import Image
from pydicom.dataset import Dataset
from pydicom.uid import ExplicitVRLittleEndian, JPEG2000Lossless

from bfd9000_dicom.models import BaseDICOMMetadata
from bfd9000_dicom.converters.compression import get_encapsulated_jpeg2k_pixel_data
from .base import BaseConverter, ConversionError

logger = logging.getLogger(__name__)


class TIFFConverter(BaseConverter):
    """
    Converter for TIFF images to DICOM format.
    
    Handles grayscale and RGB TIFF images, with optional JPEG2000 compression.
    Extracts DPI information for pixel spacing metadata.
    """
    
    @staticmethod
    def convert(
        metadata: BaseDICOMMetadata,
        input_path: str,
        output_path: Optional[str] = None,
        compression: bool = True
    ) -> Dataset:
        """
        Convert a TIFF image to DICOM format.
        
        Args:
            metadata: DICOM metadata DTO
            input_path: Path to input TIFF file
            output_path: Optional path to save DICOM file
            compression: If True, use JPEG2000 lossless. If False, uncompressed.
        
        Returns:
            Complete DICOM Dataset with pixel data
            
        Raises:
            ConversionError: If TIFF cannot be processed
        """
        # Validate input
        input_file = TIFFConverter._validate_input_file(input_path)
        
        try:
            # Get base dataset from metadata
            ds = metadata.to_dataset()
            
            # Load and process TIFF image
            with Image.open(input_file) as img:
                img.seek(0)
                
                # Extract DPI information if available
                dpi_info = img.info.get('dpi')
                if dpi_info:
                    dpi_horizontal, dpi_vertical = dpi_info
                    pixel_spacing = TIFFConverter._dpi_to_pixel_spacing(
                        dpi_horizontal, dpi_vertical
                    )
                    # Add pixel spacing to dataset if not already set
                    if not hasattr(ds, 'PixelSpacing') or not ds.PixelSpacing:
                        ds.PixelSpacing = pixel_spacing
                        ds.NominalScannedPixelSpacing = pixel_spacing
                        ds.PixelSpacingCalibrationType = "GEOMETRY"
                
                # Convert color modes to standard formats
                mode = img.mode
                if mode in ['RGBA', 'P']:
                    img = img.convert('RGB')
                elif mode == 'LA':
                    img = img.convert('L')
                elif mode not in ['L', 'RGB', 'I;16']:
                    raise ConversionError(f"Unsupported image mode: {mode}")
                
                # Convert to numpy array
                if compression:
                    img_array = np.array(img)
                else:
                    # For uncompressed, explicitly use uint16 if 16-bit
                    img_array = np.array(img, dtype=np.uint16 if mode == 'I;16' else None)
                
                # Add pixel data to dataset
                TIFFConverter._add_pixel_data(ds, img_array, compression)
            
            # Save if output path provided
            if output_path:
                TIFFConverter._save_dataset(ds, output_path)
                logger.info(f"Saved DICOM file: {output_path}")
            
            return ds
            
        except Exception as e:
            logger.error(f"Error converting TIFF {input_path}: {e}")
            raise ConversionError(f"Failed to convert TIFF: {e}") from e
    
    @staticmethod
    def _add_pixel_data(ds: Dataset, img_array: np.ndarray, compression: bool) -> None:
        """
        Add pixel data to DICOM dataset with appropriate encoding.
        
        Args:
            ds: DICOM Dataset to add pixel data to
            img_array: Numpy array containing pixel data
            compression: Whether to use JPEG2000 compression
        """
        # Determine bit depth
        if img_array.dtype == np.uint8:
            bits_allocated = 8
        elif img_array.dtype == np.uint16:
            bits_allocated = 16
        else:
            raise ConversionError(f"Unsupported bit depth: {img_array.dtype}")
        
        # Set image dimensions
        if len(img_array.shape) == 2:
            # Grayscale
            ds.Rows, ds.Columns = img_array.shape
            ds.SamplesPerPixel = 1
            ds.PhotometricInterpretation = "MONOCHROME2"
        elif len(img_array.shape) == 3:
            # RGB
            ds.Rows, ds.Columns, _ = img_array.shape
            ds.SamplesPerPixel = 3
            ds.PhotometricInterpretation = "RGB"
            ds.PlanarConfiguration = 0  # Interleaved
        else:
            raise ConversionError(f"Unsupported image shape: {img_array.shape}")
        
        # Set bit depth attributes
        ds.PixelRepresentation = 0  # Unsigned
        ds.BitsAllocated = bits_allocated
        ds.BitsStored = bits_allocated
        ds.HighBit = bits_allocated - 1
        
        # Encode pixel data
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
        """
        Convert DPI to DICOM pixel spacing (mm/pixel).
        
        Args:
            dpi_horizontal: Horizontal DPI
            dpi_vertical: Vertical DPI (defaults to horizontal if not provided)
        
        Returns:
            List of [row_spacing, column_spacing] in mm
        """
        if dpi_vertical is None:
            dpi_vertical = dpi_horizontal
        
        # Convert DPI to mm/pixel: 1 inch = 25.4 mm
        row_spacing = 25.4 / dpi_vertical
        column_spacing = 25.4 / dpi_horizontal
        
        return [f"{row_spacing:.6f}", f"{column_spacing:.6f}"]
