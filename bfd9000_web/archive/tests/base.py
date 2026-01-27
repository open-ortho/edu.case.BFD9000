"""
Base test classes with automatic media cleanup.
"""
import shutil
import tempfile
from pathlib import Path
from django.test import TestCase, override_settings
from rest_framework.test import APITestCase
from django.conf import settings


# Create a temporary directory for test media
TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix='bfd9000_test_media_')


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class CleanupTestCase(TestCase):
    """Base TestCase with automatic media cleanup."""

    @classmethod
    def tearDownClass(cls):
        """Clean up test media files after all tests in class complete."""
        super().tearDownClass()
        # Clean up the test media directory
        if Path(TEST_MEDIA_ROOT).exists():
            shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class CleanupAPITestCase(APITestCase):
    """Base APITestCase with automatic media cleanup."""

    @classmethod
    def tearDownClass(cls):
        """Clean up test media files after all tests in class complete."""
        super().tearDownClass()
        # Clean up the test media directory
        if Path(TEST_MEDIA_ROOT).exists():
            shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)
