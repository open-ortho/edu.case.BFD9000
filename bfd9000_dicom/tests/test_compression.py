"""Tests for core compression utilities."""
import unittest
import numpy as np
from bfd9000_dicom.converters.compression import (
    is_valid_jpeg2000_codestream,
    get_codestream,
    get_encapsulated_jpeg2k_pixel_data,
)


class TestCompression(unittest.TestCase):
    """Test JPEG2000 compression utilities."""

    def test_is_valid_jpeg2000_codestream_valid(self):
        """Test validation of valid JPEG2000 codestream."""
        # Valid JPEG2000 codestream starts with SOC (0xFF4F) and ends with EOC (0xFFD9)
        valid_stream = b'\xFF\x4F' + b'\x00' * 10 + b'\xFF\xD9'
        self.assertTrue(is_valid_jpeg2000_codestream(valid_stream))

    def test_is_valid_jpeg2000_codestream_invalid(self):
        """Test validation of invalid JPEG2000 codestream."""
        # Invalid stream - wrong markers
        invalid_stream = b'\xFF\x00' + b'\x00' * 10 + b'\xFF\x00'
        self.assertFalse(is_valid_jpeg2000_codestream(invalid_stream))

    def test_get_codestream_valid(self):
        """Test extraction of codestream from JP2 container."""
        # Create a mock JP2 with embedded codestream
        jp2_data = b'\x00' * 20 + b'\xFF\x4F' + b'\x00' * 10 + b'\xFF\xD9' + b'\x00' * 5
        codestream = get_codestream(jp2_data)
        self.assertEqual(codestream[:2], b'\xFF\x4F')
        self.assertEqual(codestream[-2:], b'\xFF\xD9')

    def test_get_codestream_missing_start(self):
        """Test error handling when codestream start is missing."""
        jp2_data = b'\x00' * 50
        with self.assertRaises(ValueError) as context:
            get_codestream(jp2_data)
        self.assertIn("start signature not found", str(context.exception))

    @unittest.skip("Requires imagecodecs library and may be slow")
    def test_get_encapsulated_jpeg2k_pixel_data(self):
        """Test full compression pipeline."""
        # Create a simple test image
        img_array = np.random.randint(0, 255, (100, 100), dtype=np.uint8)
        pixel_data = get_encapsulated_jpeg2k_pixel_data(img_array)
        self.assertIsNotNone(pixel_data)


if __name__ == '__main__':
    unittest.main()
