"""Background worker for uploading local media files to Box storage."""

import logging
import time
from pathlib import Path
from typing import List

from django.conf import settings

from archive.models import DigitalRecord
from .storage import BoxStorageBackend

logger = logging.getLogger(__name__)


def media_upload_worker():
    from BFD9000.settings import (
        BOX_DEVELOPER_TOKEN,
        BOX_FOLDER_ID,
        BOX_JWT_CONFIG_FILE,
        BOX_OAUTH_CLIENT_ID,
        BOX_OAUTH_CLIENT_SECRET,
    )

    if not BOX_DEVELOPER_TOKEN and not BOX_JWT_CONFIG_FILE and not (BOX_OAUTH_CLIENT_ID and BOX_OAUTH_CLIENT_SECRET):
        logger.error(
            "worker cannot start: no Box authentication configured "
            "(set BOX_DEVELOPER_TOKEN, BOX_JWT_CONFIG_FILE, or BOX_OAUTH_CLIENT_ID + BOX_OAUTH_CLIENT_SECRET)"
        )
        return
    if not BOX_FOLDER_ID:
        logger.error("worker cannot start: BOX_FOLDER_ID is not set")
        return

    time.sleep(5)

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
    media_root = Path(settings.MEDIA_ROOT).joinpath("uploads")

    if not media_root.exists():
        return 0

    image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"}
    files_processed: List[Path] = []

    for file_path in media_root.rglob("*"):
        if (
            file_path.exists()
            and file_path.is_file()
            and file_path.suffix.lower() in image_extensions
        ):
            if handle_media_file(file_path):
                files_processed.append(file_path)

    for path in files_processed:
        path.unlink()
        logger.debug("Deleted local file: %s", path)
        prune_empty_directory(path.parent)

    return len(files_processed)


def handle_media_file(file_path: Path) -> bool:
    """Upload *file_path* to Box and update the matching ``DigitalRecord`` link.

    Returns ``True`` on success, ``False`` on any error (logged; worker continues).
    """
    try:
        logger.debug("Handling media file: %s", file_path)
        relative_path = file_path.relative_to(Path(settings.MEDIA_ROOT).joinpath("uploads"))

        qs = DigitalRecord.objects.filter(source_file=str(relative_path))
        count = qs.count()
        if count != 1:
            logger.error(
                "Expected 1 record for %s, found %d; skipping DB update", relative_path, count
            )
            return False

        with open(file_path, "rb") as f:
            link = BoxStorageBackend().upload(f, str(relative_path))

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
