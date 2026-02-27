"""
Base test classes with automatic media cleanup.
"""
import shutil
import tempfile
from pathlib import Path
from django.test import TestCase, override_settings
from rest_framework.test import APITestCase


class _CleanupMediaMixin:
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._media_root = tempfile.mkdtemp(prefix='bfd9000_test_media_')
        cls._override = override_settings(MEDIA_ROOT=cls._media_root)
        cls._override.enable()

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, '_override', None):
            cls._override.disable()
        if getattr(cls, '_media_root', None) and Path(cls._media_root).exists():
            shutil.rmtree(cls._media_root, ignore_errors=True)
        super().tearDownClass()


class CleanupTestCase(_CleanupMediaMixin, TestCase):
    """Base TestCase with automatic media cleanup."""


class CleanupAPITestCase(_CleanupMediaMixin, APITestCase):
    """Base APITestCase with automatic media cleanup."""
