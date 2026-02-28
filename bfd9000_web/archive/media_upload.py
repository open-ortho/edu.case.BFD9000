"""Background worker for uploading media files."""

import logging
import time
from pathlib import Path

from BFD9000.settings import BOX_ACCESS_TOKEN, BOX_FOLDER_ID
from django.conf import settings

logger = logging.getLogger(__name__)


def media_upload_worker():
    if not BOX_ACCESS_TOKEN:
        logger.error("worker cannot start: envar BOX_ACCESS_TOKEN is not set")
        return
    if not BOX_FOLDER_ID:
        logger.error("worker cannot start: envar BOX_FOLDER_ID is not set")
        return

    time.sleep(5)

    while True:
        try:
            files_processed = process_media_files()
            if files_processed > 0:
                logger.info(f"Processed {files_processed} media file(s)")
        except Exception as e:
            # Log errors but keep the worker running
            logger.error(f"Error in media upload worker: {e}", exc_info=True)
        time.sleep(60)  # Check every minute


def process_media_files() -> int:
    """Process all files in the media directory for upload."""
    media_root = Path(settings.MEDIA_ROOT)

    if not media_root.exists():
        return 0

    # Find all image files in media directory
    image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"}
    files_processed = 0

    for file_path in media_root.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in image_extensions:
            if handle_media_file(file_path):
                files_processed += 1

    return files_processed


def handle_media_file(file_path: Path) -> bool:
    """Handle a single media file: upload, delete, and prune directory."""
    try:
        # Attempt to upload the file
        if upload_file(file_path):
            logger.info(f"Successfully uploaded: {file_path}")
            # Delete the file after successful upload
            file_path.unlink()
            logger.debug(f"Deleted local file: {file_path}")

            # Prune parent directory if empty
            prune_empty_directory(file_path.parent)
            return True
        else:
            logger.debug(f"Upload failed (expected): {file_path}")
            return False
    except Exception as e:
        logger.error(f"Error handling file {file_path}: {e}", exc_info=True)
        return False


def upload_file(file_path: Path) -> bool:
    """
    Upload a file to remote storage.

    TODO: Implement actual upload logic
    Currently returns False to prevent any deletions.
    """
    # Placeholder - always fails for now
    logger.debug(f"Upload attempted for {file_path} (not implemented)")
    return False


def prune_empty_directory(directory: Path):
    """Remove directory if it's empty, recursively prune parent directories."""
    media_root = Path(settings.MEDIA_ROOT)

    if directory == media_root or not directory.exists():
        return

    if not any(directory.iterdir()):
        directory.rmdir()
        # Recursively prune parent
        prune_empty_directory(directory.parent)
