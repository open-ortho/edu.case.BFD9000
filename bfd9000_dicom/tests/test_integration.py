"""Integration tests for the converter router and end-to-end functionality."""
import unittest
from unittest.mock import patch, MagicMock
from bfd9000_dicom.converters import convert_to_dicom
from bfd9000_dicom.models import RadiographMetadata, PatientSex
from bfd9000_dicom.converters import UnsupportedFileTypeError


class TestConverterIntegration(unittest.TestCase):
    """Integration tests for the converter router system."""

    def setUp(self):
        """Set up test fixtures."""
        self.metadata = RadiographMetadata(
            patient_id="B0013",
            patient_sex=PatientSex.M,
            patient_age="217M"
        )

    @patch('bfd9000_dicom.converters.tiff.TIFFConverter.convert')
    def test_convert_to_dicom_tiff_integration(self, mock_convert):
        """Test end-to-end TIFF conversion through router."""
        mock_ds = MagicMock()
        mock_convert.return_value = mock_ds

        result = convert_to_dicom(
            metadata=self.metadata,
            input_path="test.tiff",
            output_path="output.dcm",
            compression=True
        )

        self.assertEqual(result, mock_ds)
        mock_convert.assert_called_once_with(
            metadata=self.metadata,
            input_path="test.tiff",
            output_path="output.dcm",
            compression=True
        )

    @patch('bfd9000_dicom.converters.png.PNGConverter.convert')
    def test_convert_to_dicom_png_integration(self, mock_convert):
        """Test end-to-end PNG conversion through router."""
        mock_ds = MagicMock()
        mock_convert.return_value = mock_ds

        result = convert_to_dicom(
            metadata=self.metadata,
            input_path="test.png",
            output_path="output.dcm",
            compression=False
        )

        self.assertEqual(result, mock_ds)
        mock_convert.assert_called_once_with(
            metadata=self.metadata,
            input_path="test.png",
            output_path="output.dcm",
            compression=False
        )

    @patch('bfd9000_dicom.converters.jpeg.JPEGConverter.convert')
    def test_convert_to_dicom_jpeg_integration(self, mock_convert):
        """Test end-to-end JPEG conversion through router."""
        mock_ds = MagicMock()
        mock_convert.return_value = mock_ds

        result = convert_to_dicom(
            metadata=self.metadata,
            input_path="test.jpg",
            output_path=None,  # No output file
            compression=True
        )

        self.assertEqual(result, mock_ds)
        mock_convert.assert_called_once_with(
            metadata=self.metadata,
            input_path="test.jpg",
            output_path=None,
            compression=True
        )

    @patch('bfd9000_dicom.converters.pdf.PDFConverter.convert')
    def test_convert_to_dicom_pdf_integration(self, mock_convert):
        """Test end-to-end PDF conversion through router."""
        from bfd9000_dicom.models import DocumentMetadata

        doc_metadata = DocumentMetadata(
            patient_id="B0013",
            patient_sex=PatientSex.M,
            patient_age="217M",
            document_title="Test Document"
        )

        mock_ds = MagicMock()
        mock_convert.return_value = mock_ds

        result = convert_to_dicom(
            metadata=doc_metadata,
            input_path="test.pdf",
            output_path="output.dcm"
        )

        self.assertEqual(result, mock_ds)
        mock_convert.assert_called_once_with(
            metadata=doc_metadata,
            input_path="test.pdf",
            output_path="output.dcm",
            compression=True  # Default value
        )

    def test_convert_to_dicom_unsupported_extension(self):
        """Test that unsupported file extensions raise appropriate error."""
        with self.assertRaises(UnsupportedFileTypeError) as context:
            convert_to_dicom(
                metadata=self.metadata,
                input_path="test.txt",
                output_path="output.dcm"
            )

        self.assertIn("Unsupported file type", str(context.exception))
        self.assertIn(".txt", str(context.exception))

    def test_convert_to_dicom_case_insensitive_extensions(self):
        """Test that file extension matching is case insensitive."""
        with patch('bfd9000_dicom.converters.tiff.TIFFConverter.convert') as mock_convert:
            mock_ds = MagicMock()
            mock_convert.return_value = mock_ds

            # Test uppercase extension
            result = convert_to_dicom(
                metadata=self.metadata,
                input_path="test.TIFF",
                output_path="output.dcm"
            )

            mock_convert.assert_called_once()

    @patch('bfd9000_dicom.converters.tiff.TIFFConverter.convert')
    def test_convert_to_dicom_default_compression(self, mock_convert):
        """Test that compression defaults to True when not specified."""
        mock_ds = MagicMock()
        mock_convert.return_value = mock_ds

        result = convert_to_dicom(
            metadata=self.metadata,
            input_path="test.tiff",
            output_path="output.dcm"
            # compression not specified, should default to True
        )

        mock_convert.assert_called_once_with(
            metadata=self.metadata,
            input_path="test.tiff",
            output_path="output.dcm",
            compression=True
        )

    def test_convert_to_dicom_no_output_path(self):
        """Test conversion without saving to file."""
        with patch('bfd9000_dicom.converters.tiff.TIFFConverter.convert') as mock_convert:
            mock_ds = MagicMock()
            mock_convert.return_value = mock_ds

            result = convert_to_dicom(
                metadata=self.metadata,
                input_path="test.tiff",
                output_path=None
            )

            self.assertEqual(result, mock_ds)
            mock_convert.assert_called_once_with(
                metadata=self.metadata,
                input_path="test.tiff",
                output_path=None,
                compression=True
            )


class TestConverterWorkflow(unittest.TestCase):
    """Test complete conversion workflows."""

    def setUp(self):
        """Set up test fixtures."""
        self.metadata = RadiographMetadata(
            patient_id="B0013",
            patient_sex=PatientSex.M,
            patient_age="217M",
            is_bolton_brush_study=True
        )

    def test_bolton_brush_workflow(self):
        """Test a complete Bolton Brush workflow."""
        # This would be an integration test with actual files
        # For now, just test the metadata setup
        self.assertEqual(self.metadata.patient_name,
                         "B0013^Bolton Study Subject")
        self.assertEqual(self.metadata.modality.value, "RG")
        self.assertEqual(self.metadata.conversion_type.value, "DF")

        # Test orientation setting
        self.metadata.set_orientation_pa()
        self.assertEqual(self.metadata.patient_orientation, "PA")

    def test_metadata_to_dataset_conversion(self):
        """Test that metadata converts to proper DICOM dataset."""
        ds = self.metadata.to_dataset()

        # Check required DICOM fields are set
        self.assertEqual(ds.PatientID, "B0013")
        self.assertEqual(ds.PatientSex, "M")
        self.assertEqual(ds.PatientAge, "217M")
        self.assertEqual(ds.Modality, "RG")

        # Check Bolton Brush specific fields
        self.assertEqual(ds.ConversionType, "DF")
        self.assertEqual(ds.BurnedInAnnotation, "YES")


if __name__ == '__main__':
    unittest.main()
