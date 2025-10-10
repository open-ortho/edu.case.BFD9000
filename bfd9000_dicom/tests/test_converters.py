"""Tests for converter modules."""
import unittest
from bfd9000_dicom.converters import (
    RadiographConverter,
    SurfaceConverter,
    DocumentConverter,
    PhotographConverter,
)


class TestConverters(unittest.TestCase):
    """Test converter classes for various modalities."""

    def test_radiograph_converter_exists(self):
        """Test that RadiographConverter is available."""
        self.assertTrue(hasattr(RadiographConverter, 'convert'))
        self.assertTrue(hasattr(RadiographConverter, 'extract_metadata_from_filename'))

    def test_surface_converter_not_implemented(self):
        """Test that SurfaceConverter raises NotImplementedError."""
        with self.assertRaises(NotImplementedError):
            SurfaceConverter.convert('dummy.stl', 'output.dcm')

    def test_document_converter_not_implemented(self):
        """Test that DocumentConverter raises NotImplementedError."""
        with self.assertRaises(NotImplementedError):
            DocumentConverter.convert('dummy.pdf', 'output.dcm')

    def test_photograph_converter_not_implemented(self):
        """Test that PhotographConverter raises NotImplementedError."""
        with self.assertRaises(NotImplementedError):
            PhotographConverter.convert('dummy.jpg', 'output.dcm')


if __name__ == '__main__':
    unittest.main()
