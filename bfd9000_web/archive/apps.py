"""Django app configuration for the archive app."""

from django.apps import AppConfig


class ArchiveConfig(AppConfig):
    """Configure default settings for the archive app."""
    default_auto_field = "django.db.models.BigAutoField"  # pyright: ignore[reportAssignmentType]
    name = "archive"
