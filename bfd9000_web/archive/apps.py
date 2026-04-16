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
        if 'runserver' in sys.argv:
            if self._is_main_process():
                self._start_background_task()
        # are we in production (gunicorn)?
        elif os.path.basename(sys.argv[0]) == 'gunicorn':
            self._start_background_task()
        else:
            logger.info("Background tasks not started: conditions have not been met (runserver, gunicorn)")

    def _is_main_process(self):
        """Check if this is the main process (development only)."""
        return os.environ.get('RUN_MAIN') == 'true'

    def _start_background_task(self):
        """Start the background media upload thread."""
        from archive.media_upload import media_upload_worker

        thread = threading.Thread(target=media_upload_worker, daemon=True)
        thread.start()
