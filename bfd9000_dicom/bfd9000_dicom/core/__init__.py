"""
Core functionality for DICOM creation and manipulation.

This package contains the core building blocks for DICOM file generation:
- DICOM builder utilities
- Image compression utilities (JPEG2000)
"""

from .dicom_builder import (
    build_file_meta,
    add_common_bolton_brush_tags,
    add_image_module,
    dpi_to_dicom_spacing,
)
from .compression import (
    get_encapsulated_jpeg2k_pixel_data,
    is_valid_jpeg2000_codestream,
    get_codestream,
)

__all__ = [
    # DICOM builder functions
    'build_file_meta',
    'add_common_bolton_brush_tags',
    'add_image_module',
    'dpi_to_dicom_spacing',
    # Compression functions
    'get_encapsulated_jpeg2k_pixel_data',
    'is_valid_jpeg2000_codestream',
    'get_codestream',
]
