""" PoC package to convert BBGSC TIFFs into JPEG2000 encapsulated DICOMs.

The module is purposely divided into modules with division of concerns, so that it may facilitate re-use and inclusion in the BFD9000 API.
"""
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

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
