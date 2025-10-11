"""Tests for converter modules."""
import unittest
from unittest.mock import patch, MagicMock
from bfd9000_dicom.converters import (
    convert_to_dicom,
    get_converter_for_file,
    TIFFConverter,
    PNGConverter,
    JPEGConverter,
    PDFConverter,
    STLConverter,
    UnsupportedFileTypeError,
)
from bfd9000_dicom.models import RadiographMetadata, PatientSex


class TestConverters(unittest.TestCase):
    """Test converter classes for various file types."""

    def setUp(self):
        """Set up test fixtures."""
        self.metadata = RadiographMetadata(
            patient_id="B0013",
            patient_sex=PatientSex.M,
            patient_age="217M"
        )

    def test_get_converter_for_file_tiff(self):
        """Test converter selection for TIFF files."""
        converter = get_converter_for_file("test.tiff")
        self.assertEqual(converter, TIFFConverter)

        converter = get_converter_for_file("test.TIFF")
        self.assertEqual(converter, TIFFConverter)

    def test_get_converter_for_file_png(self):
        """Test converter selection for PNG files."""
        converter = get_converter_for_file("test.png")
        self.assertEqual(converter, PNGConverter)

    def test_get_converter_for_file_jpeg(self):
        """Test converter selection for JPEG files."""
        converter = get_converter_for_file("test.jpg")
        self.assertEqual(converter, JPEGConverter)

        converter = get_converter_for_file("test.jpeg")
        self.assertEqual(converter, JPEGConverter)

    def test_get_converter_for_file_pdf(self):
        """Test converter selection for PDF files."""
        converter = get_converter_for_file("test.pdf")
        self.assertEqual(converter, PDFConverter)

    def test_get_converter_for_file_stl(self):
        """Test converter selection for STL files."""
        converter = get_converter_for_file("test.stl")
        self.assertEqual(converter, STLConverter)

    def test_get_converter_for_unsupported_file(self):
        """Test converter selection raises error for unsupported files."""
        with self.assertRaises(UnsupportedFileTypeError):
            get_converter_for_file("test.txt")

    @patch('bfd9000_dicom.converters.tiff.TIFFConverter.convert')
    def test_convert_to_dicom_tiff(self, mock_convert):
        """Test convert_to_dicom function routes to TIFF converter."""
        mock_convert.return_value = MagicMock()

        result = convert_to_dicom(
            metadata=self.metadata,
            input_path="test.tiff",
            output_path="output.dcm",
            compression=True
        )

        mock_convert.assert_called_once_with(
            metadata=self.metadata,
            input_path="test.tiff",
            output_path="output.dcm",
            compression=True
        )

    def test_convert_to_dicom_unsupported_file(self):
        """Test convert_to_dicom raises error for unsupported files."""
        with self.assertRaises(UnsupportedFileTypeError):
            convert_to_dicom(
                metadata=self.metadata,
                input_path="test.txt",
                output_path="output.dcm"
            )

    def test_tiff_converter_has_convert_method(self):
        """Test that TIFFConverter has required convert method."""
        self.assertTrue(hasattr(TIFFConverter, 'convert'))
        self.assertTrue(callable(TIFFConverter.convert))

    def test_png_converter_has_convert_method(self):
        """Test that PNGConverter has required convert method."""
        self.assertTrue(hasattr(PNGConverter, 'convert'))
        self.assertTrue(callable(PNGConverter.convert))

    def test_jpeg_converter_has_convert_method(self):
        """Test that JPEGConverter has required convert method."""
        self.assertTrue(hasattr(JPEGConverter, 'convert'))
        self.assertTrue(callable(JPEGConverter.convert))

    def test_pdf_converter_has_convert_method(self):
        """Test that PDFConverter has required convert method."""
        self.assertTrue(hasattr(PDFConverter, 'convert'))
        self.assertTrue(callable(PDFConverter.convert))

    def test_stl_converter_has_convert_method(self):
        """Test that STLConverter has required convert method."""
        self.assertTrue(hasattr(STLConverter, 'convert'))
        self.assertTrue(callable(STLConverter.convert))


if __name__ == '__main__':
    unittest.main()
