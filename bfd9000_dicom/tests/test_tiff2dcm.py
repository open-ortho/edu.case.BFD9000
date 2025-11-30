"""Tests for TIFF converter and Bolton Brush utilities."""
import unittest
import json
import os
from unittest.mock import patch, MagicMock
import numpy as np
from bfd9000_dicom.converters import TIFFConverter
from bfd9000_dicom.extractors import extract_metadata_from_filename
from bfd9000_dicom.models import RadiographMetadata, PatientSex

# Get the correct path to test.dcm.json
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
DCMJSONFILE = os.path.join(TEST_DIR, 'test.dcm.json')


class TestTIFFConverter(unittest.TestCase):
    """Test TIFF converter functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.metadata = RadiographMetadata(
            patient_id="B0013",
            patient_sex=PatientSex.M,
            patient_age="217M"
        )

    def test_extract_bolton_brush_data_from_filename(self):
        """Test metadata extraction from Bolton Brush filename format."""
        # Test the example from the old test
        file_path = "./Downloads/B0013LM18y01m.tif"
        result = extract_metadata_from_filename(file_path)

        self.assertEqual(result.patient_id, "B0013")
        self.assertEqual(result.patient_sex, "M")
        self.assertEqual(result.patient_age, "217M")
        self.assertEqual(result.image_type, "L")

    def test_extract_bolton_brush_data_edge_cases(self):
        """Test filename parsing with different formats."""
        # Test female patient
        result = extract_metadata_from_filename("B00202F015y08m.jpg")
        self.assertEqual(result.patient_id, "B0020")
        self.assertEqual(result.patient_sex, "F")
        self.assertEqual(result.patient_age, "188M")  # 15*12 + 8 = 188 months
        self.assertEqual(result.image_type, "2")

    @patch('PIL.Image.open')
    @patch('bfd9000_dicom.converters.tiff.TIFFConverter._validate_input_file')
    def test_tiff_converter_convert_basic(self, _mock_validate, mock_image_open):
        """Test basic TIFF conversion functionality."""
        # Mock the image
        mock_img = MagicMock()
        mock_img.mode = 'L'  # Grayscale
        mock_img.seek = MagicMock()
        mock_img.info = {'dpi': (300, 300)}
        mock_image_open.return_value.__enter__.return_value = mock_img
        
        # Mock numpy array
        with patch('numpy.array') as mock_array:
            mock_array.return_value = MagicMock()
            mock_array.return_value.shape = (100, 100)
            mock_array.return_value.dtype = np.uint16  # Use 16-bit which is supported
            mock_array.return_value.tobytes.return_value = b'test_data'
            
            # Mock the dataset creation
            with patch.object(self.metadata, 'to_dataset') as mock_to_dataset:
                mock_ds = MagicMock()
                mock_to_dataset.return_value = mock_ds
                
                # Test the conversion
                result = TIFFConverter.convert(
                    metadata=self.metadata,
                    input_path="test.tiff",
                    output_path=None,
                    compression=False
                )
                
                # Verify the conversion was attempted
                self.assertIsNotNone(result)

    def test_tiff_converter_validation_error(self):
        """Test TIFF converter handles file not found."""
        with self.assertRaises(FileNotFoundError):
            TIFFConverter.convert(
                metadata=self.metadata,
                input_path="nonexistent.tiff",
                output_path=None,
                compression=False
            )