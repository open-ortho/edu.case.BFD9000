"""
BFD9000 DICOM - Bolton File Dicomizer 9000

A package to convert various image formats into DICOM format with appropriate
metadata. The package is organized with clear separation of concerns:

- models: Data transfer objects (DTOs) for DICOM metadata
- converters: Specialized converters for different imaging modalities
- core: Core utilities for DICOM building and compression

This facilitates re-use and inclusion in the BFD9000 API.
"""
import logging

# Import models for easy access
from .models import (
    BaseDICOMMetadata,
    RadiographMetadata,
    SurfaceMetadata,
    DocumentMetadata,
    PhotographMetadata,
    PatientSex,
    ModalityType,
    ConversionType,
    BurnedInAnnotation,
)

# Import converters
from .converters import (
    RadiographConverter,
    SurfaceConverter,
    DocumentConverter,
    PhotographConverter,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Exception classes
class TIFF2DICOMError(Exception):
    """Base class for exceptions in this module."""
    pass


class UnsupportedImageModeError(TIFF2DICOMError):
    """Exception raised for unsupported image modes."""
    def __init__(self, mode):
        self.mode = mode
        self.message = f"Unsupported image mode {mode}."
        super().__init__(self.message)


class UnsupportedBitDepthError(TIFF2DICOMError):
    """Exception raised for unsupported bit depths."""
    def __init__(self, bit_depth):
        self.bit_depth = bit_depth
        self.message = f"Unsupported bit depth {bit_depth}."
        super().__init__(self.message)


class InvalidJPEG2000CodestreamError(TIFF2DICOMError):
    """Exception raised for invalid JPEG 2000 codestreams."""
    def __init__(self, path):
        self.path = path
        self.message = f"Invalid JPEG 2000 codestream for {path}."
        super().__init__(self.message)


# Public API
__all__ = [
    # Models
    'BaseDICOMMetadata',
    'RadiographMetadata',
    'SurfaceMetadata',
    'DocumentMetadata',
    'PhotographMetadata',
    # Enums
    'PatientSex',
    'ModalityType',
    'ConversionType',
    'BurnedInAnnotation',
    # Converters
    'RadiographConverter',
    'SurfaceConverter',
    'DocumentConverter',
    'PhotographConverter',
    # Exceptions
    'TIFF2DICOMError',
    'UnsupportedImageModeError',
    'UnsupportedBitDepthError',
    'InvalidJPEG2000CodestreamError',
    # Utilities
    'logger',
]
