"""Tests for TIFF converter and Bolton Brush utilities."""
import unittest
import json
import os
from unittest.mock import patch, MagicMock
import numpy as np
from bfd9000_dicom.converters import (
    TIFFConverter,
    extract_bolton_brush_data_from_filename,
    load_radiograph_metadata_from_json,
)
from bfd9000_dicom.models import RadiographMetadata, PatientSex
from bfd9000_dicom.converters.base import ConversionError

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
        patient_id, patient_sex, patient_age = extract_bolton_brush_data_from_filename(file_path)
        
        self.assertEqual(patient_id, "B0013")
        self.assertEqual(patient_sex, "M")
        self.assertEqual(patient_age, "217M")

    def test_extract_bolton_brush_data_edge_cases(self):
        """Test filename parsing with different formats."""
        # Test female patient
        patient_id, patient_sex, patient_age = extract_bolton_brush_data_from_filename("B00202F015y08m.jpg")
        self.assertEqual(patient_id, "B0020")
        self.assertEqual(patient_sex, "F")
        self.assertEqual(patient_age, "188M")  # 15*12 + 8 = 188 months

    @patch('PIL.Image.open')
    @patch('bfd9000_dicom.converters.tiff.TIFFConverter._validate_input_file')
    def test_tiff_converter_convert_basic(self, mock_validate, mock_image_open):
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

    def test_load_radiograph_metadata_from_json(self):
        """Test loading RadiographMetadata from JSON file."""
        # Create proper DICOM JSON format
        json_data = {
            "00100020": {"vr": "LO", "Value": ["B0013"]},        # PatientID
            "00100040": {"vr": "CS", "Value": ["M"]},           # PatientSex
            "00101010": {"vr": "AS", "Value": ["217M"]},        # PatientAge
            "00100010": {"vr": "PN", "Value": ["Test^Patient"]}, # PatientName
            "0020000D": {"vr": "UI", "Value": ["1.2.3.4.5"]},   # StudyInstanceUID
            "0020000E": {"vr": "UI", "Value": ["1.2.3.4.6"]},   # SeriesInstanceUID
            "00200013": {"vr": "IS", "Value": ["1"]},           # InstanceNumber
            "00200020": {"vr": "CS", "Value": ["PA"]},          # PatientOrientation
            "00209161": {"vr": "CS", "Value": ["R"]}            # ImageLaterality
        }
        
        # Mock file operations
        with patch('builtins.open', create=True) as mock_open:
            mock_file = MagicMock()
            mock_file.__enter__.return_value = mock_file
            mock_file.read.return_value = json.dumps(json_data)
            mock_open.return_value = mock_file
            
            metadata = load_radiograph_metadata_from_json("test.json")
            
            self.assertEqual(metadata.patient_id, "B0013")
            self.assertEqual(metadata.patient_sex, PatientSex.M)
            self.assertEqual(metadata.patient_age, "217M")
            self.assertEqual(metadata.patient_name, "Test^Patient")
            self.assertEqual(metadata.patient_orientation, "PA")
            self.assertEqual(metadata.image_laterality, "R")


if __name__ == '__main__':
    unittest.main()