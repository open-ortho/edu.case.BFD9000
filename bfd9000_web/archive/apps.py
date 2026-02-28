"""Django app configuration for the archive app."""

import logging
import os
import sys
import threading

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class ArchiveConfig(AppConfig):
    """Configure default settings for the archive app."""
    default_auto_field = "django.db.models.BigAutoField"  # pyright: ignore[reportAssignmentType]
    name = "archive"

    def ready(self):
        """Initialize the archive app and start background tasks."""
        # Guard against running twice in development (autoreloader issue)
        if not self._is_reloader_process():
            self._start_background_task()

    def _is_reloader_process(self):
        """Check if this is the reloader process (development only)."""
        return 'runserver' in sys.argv and os.environ.get('RUN_MAIN') != 'true'

    def _start_background_task(self):
        """Start the background media upload thread."""
        from archive.media_upload import media_upload_worker

        thread = threading.Thread(target=media_upload_worker, daemon=True)
        thread.start()
