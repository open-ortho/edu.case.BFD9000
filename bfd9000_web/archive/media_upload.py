"""Background worker for uploading local media files to Box storage."""

import logging
import time
from pathlib import Path

from django.conf import settings

from archive.models import DigitalRecord
from .storage import BoxStorageBackend

logger = logging.getLogger(__name__)


def media_upload_worker():
    # wait for box to become available
    for i in range(3):
        e = BoxStorageBackend().error()
        if e:
            if i == 2:
                logger.error(f"Failed to connect to Box, exiting: {e}")
                return
            logger.info(f"Could not connect to Box, retrying in 60 seconds: {e}")
            time.sleep(60)
        else:
            break
    
    logger.info("Connected to Box. Starting media upload worker...")

    while True:
        try:
            files_processed = process_media_files()
            if files_processed > 0:
                logger.info("Processed %d media file(s)", files_processed)
        except Exception as exc:
            logger.error("Error in media upload worker: %s", exc, exc_info=True)
        time.sleep(60)


def process_media_files() -> int:
    """Upload all pending files from the local media/uploads directory to Box."""
    media_root = settings.MEDIA_ROOT

    if not media_root.exists():
        return 0

    image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"}

    uploads_dir = media_root / "uploads"
    if not uploads_dir.exists():
        return 0

    count = 0
    for file_path in uploads_dir.rglob("*"):
        if (
            file_path.exists()
            and file_path.is_file()
            and file_path.suffix.lower() in image_extensions
            and handle_media_file(file_path)
        ):
            file_path.unlink()
            logger.debug("Deleted local file: %s", file_path)
            prune_empty_directory(file_path.parent)
            count += 1

    return count


def handle_media_file(file_path: Path) -> bool:
    """Upload *file_path* to Box and update the matching ``DigitalRecord`` link.

    Returns ``True`` on success, ``False`` on any error (logged; worker continues).
    """
    try:
        logger.debug("Handling media file: %s", file_path)
        relative_path = file_path.relative_to(settings.MEDIA_ROOT)

        qs = DigitalRecord.objects.filter(source_file=str(relative_path))
        count = qs.count()
        if count != 1:
            logger.error(
                "Expected 1 record for %s, found %d; skipping DB update", relative_path, count
            )
            return False

        with open(file_path, "rb") as f:
            link = BoxStorageBackend().upload(f, relative_path)

        qs.update(source_file=link)
        return True
    except Exception as exc:
        logger.error("Error handling file %s: %s", file_path, exc, exc_info=True)
        return False


def prune_empty_directory(directory: Path):
    """Remove *directory* if empty, then recurse into its parent."""
    media_root = Path(settings.MEDIA_ROOT)

    if directory == media_root or not directory.exists():
        return

    if not any(directory.iterdir()):
        directory.rmdir()
        prune_empty_directory(directory.parent)
