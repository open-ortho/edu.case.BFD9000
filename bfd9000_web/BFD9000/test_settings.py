"""
Test-specific settings that override base settings.

This configuration ensures test media files are stored in a temporary
directory that gets cleaned up after tests complete.
"""
from .settings import *
import tempfile
# Use a temporary directory for media files during testing
MEDIA_ROOT = tempfile.mkdtemp(prefix='bfd9000_test_media_')

# Override storage to use the test media root
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {
            "location": MEDIA_ROOT,
        }
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
