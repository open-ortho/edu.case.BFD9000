"""
Converters package for various image modalities to DICOM format.

This package contains specialized converters for different types of medical imaging
and documentation formats:
- Radiographs (TIFF/PNG scanned X-rays)
- Surface models (STL files)
- Documents (PDF files)
- Photographs (JPEG/PNG visible light images)
"""

from .radiograph import RadiographConverter
from .surface import SurfaceConverter
from .document import DocumentConverter
from .photograph import PhotographConverter

__all__ = [
    'RadiographConverter',
    'SurfaceConverter',
    'DocumentConverter',
    'PhotographConverter',
]
