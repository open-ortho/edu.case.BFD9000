"""Tests for radiograph converter."""
import unittest
import json
import os
from bfd9000_dicom.converters.radiograph import (
    RadiographConverter,
    extract_and_convert_data,
    build_dicom_without_image,
    load_dataset_from_file
)

# Get the correct path to test.dcm.json
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
DCMJSONFILE = os.path.join(TEST_DIR, 'test.dcm.json')


class TestRadiographConverter(unittest.TestCase):
    """Test radiograph TIFF to DICOM conversion."""

    file_path = "./Downloads/B0013LM18y01m.tif"

    def test_extract_data_from_filename(self):
        """Test metadata extraction from Bolton Brush filename format."""
        a, b, c, d = extract_and_convert_data(self.file_path)
        self.assertEqual(a, "B0013")
        self.assertEqual(b, "L")
        self.assertEqual(c, "M")
        self.assertEqual(d, "217M")

    @unittest.skip("Skipped - requires actual file")
    def test_build_dicom(self):
        """Test building DICOM dataset without image data."""
        ds = build_dicom_without_image(self.file_path)
        with open('./test.dcm.json', 'w', encoding='utf-8') as json_file:
            json.dump(ds.to_json_dict(), json_file, indent=4)

    def test_load_dataset_from_json(self):
        """Test loading DICOM dataset from JSON file."""
        ds = load_dataset_from_file(DCMJSONFILE)
        print(ds)