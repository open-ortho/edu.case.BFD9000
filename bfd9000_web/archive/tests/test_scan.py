"""Tests for scan page TIFF preview conversion."""

import io
from unittest.mock import patch

from PIL import Image
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse


class ScanTiffPreviewTests(TestCase):
    """Validate TIFF-to-PNG preview conversion behavior."""

    def setUp(self):
        self.user = User.objects.create_user(username='scanuser', password='testpassword')
        self.client.force_login(self.user)

    def _build_16bit_tiff(self, values, size):
        image = Image.new('I;16', size)
        image.putdata(values)
        buf = io.BytesIO()
        image.save(buf, format='TIFF')
        return buf.getvalue()

    def test_tiff_preview_supports_16bit_grayscale(self):
        """Endpoint should convert 16-bit grayscale TIFF into PNG."""
        payload = self._build_16bit_tiff([0, 1024, 2048, 65535], (2, 2))
        upload = SimpleUploadedFile('scan.tiff', payload, content_type='image/tiff')

        response = self.client.post(reverse('archive:scan_tiff_preview'), {'file': upload})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/png')

        converted = Image.open(io.BytesIO(response.content))
        self.assertEqual(converted.mode, 'I;16')

    def test_tiff_preview_handles_12bit_metadata_with_16bit_png_output(self):
        """
        Simulate 12-bit TIFF metadata and verify 16-bit PNG output.

        Pillow cannot reliably emit true 12-bit TIFF pixel data; it normalizes to 16-bit,
        so this test patches bits-per-sample detection to exercise the 12-bit code path.
        """
        payload = self._build_16bit_tiff([0, 4095], (2, 1))
        upload = SimpleUploadedFile('scan.tif', payload, content_type='image/tiff')

        with patch('archive.views._get_bits_per_sample', return_value=12):
            response = self.client.post(reverse('archive:scan_tiff_preview'), {'file': upload})

        self.assertEqual(response.status_code, 200)
        converted = Image.open(io.BytesIO(response.content))
        self.assertEqual(converted.mode, 'I;16')
        self.assertEqual(converted.getpixel((1, 0)), 4095)
