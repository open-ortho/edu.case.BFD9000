"""Storage backend abstraction for media files.

Backends use URI-style links to identify stored files:
  - Box:   ``box://<file_id>``
  - Local: relative path from ``MEDIA_ROOT``

Usage::

    backend = get_backend(link)
    stream, filename = backend.download(link)

    link = backend.upload(file_obj, "patient/scan")
    links = backend.list("patient/scan/")
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import IO

from django.conf import settings


class StorageBackend(ABC):
    """Abstract interface for a file storage backend."""

    @abstractmethod
    def upload(self, file: IO[bytes], path: str) -> str:
        """Upload *file* to the given relative *path* and return a storage link."""

    @abstractmethod
    def list(self, path: str) -> list[str]:
        """Return storage links for every file found under *path*."""

    @abstractmethod
    def download(self, link: str) -> tuple[IO[bytes], str]:
        """Download the resource identified by *link*.

        Returns a ``(stream, filename)`` tuple.
        """


class BoxStorageBackend(StorageBackend):
    """Box.com storage backend.  Links use the ``box://<file_id>`` scheme."""

    SCHEME = "box://"

    def upload(self, file: IO[bytes], path: str) -> str:
        """Upload *file* to Box, mirroring the directory structure of *path*.

        Returns a ``box://<file_id>`` link.
        """
        from .media_upload import _get_box_client, _get_or_create_folder
        from box_sdk_gen.managers.uploads import (
            UploadFileAttributes,
            UploadFileAttributesParentField,
        )
        from BFD9000.settings import BOX_FOLDER_ID

        client = _get_box_client()
        parts = Path(path)
        folder_parts = parts.parent.parts
        file_name = parts.name

        current_folder_id = BOX_FOLDER_ID or "0"
        for folder_name in folder_parts:
            fid = _get_or_create_folder(client, current_folder_id, folder_name)
            if fid is None:
                raise RuntimeError(f"Failed to create/navigate to Box folder: {folder_name}")
            current_folder_id = fid

        result = client.uploads.upload_file(
            attributes=UploadFileAttributes(
                name=file_name,
                parent=UploadFileAttributesParentField(id=current_folder_id),
            ),
            file=file,  # type: ignore[arg-type]
        )
        uploaded_file = result.entries[0]  # pyright: ignore[reportOptionalSubscript]
        return f"{self.SCHEME}{uploaded_file.id}"

    def list(self, path: str) -> list[str]:
        """Return ``box://<file_id>`` links for every file under *path* in Box."""
        from .media_upload import _get_box_client, _get_item_by_name
        from BFD9000.settings import BOX_FOLDER_ID

        client = _get_box_client()
        current_folder_id = BOX_FOLDER_ID or "0"

        for folder_name in Path(path).parts:
            item = _get_item_by_name(client, current_folder_id, folder_name)
            if item is None or item.type != "folder":
                return []
            current_folder_id = item.id

        links: list[str] = []
        items = client.folders.get_folder_items(current_folder_id)
        while True:
            for item in items.entries or []:
                if item.type == "file":
                    links.append(f"{self.SCHEME}{item.id}")
            if items.next_marker is None:
                break
            items = client.folders.get_folder_items(current_folder_id, marker=items.next_marker)
        return links

    def download(self, link: str) -> tuple[IO[bytes], str]:
        """Download the Box file identified by *link*; return ``(stream, filename)``."""
        from .media_upload import download_file

        file_id = link[len(self.SCHEME):]
        return download_file(file_id)


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage backend.

    Links are paths relative to ``MEDIA_ROOT``.
    """

    def upload(self, file: IO[bytes], path: str) -> str:
        """Write *file* to *path* (relative to ``MEDIA_ROOT``) and return the path as a link."""
        dest = Path(settings.MEDIA_ROOT) / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as f:
            f.write(file.read())
        return path

    def list(self, path: str) -> list[str]:
        """Return relative paths for every file under *path* within ``MEDIA_ROOT``."""
        root = Path(settings.MEDIA_ROOT) / path
        if not root.exists():
            return []
        return [
            str(p.relative_to(settings.MEDIA_ROOT))
            for p in root.rglob("*")
            if p.is_file()
        ]

    def download(self, link: str) -> tuple[IO[bytes], str]:
        """Open the local file at *link* (relative to ``MEDIA_ROOT``); return ``(stream, filename)``."""
        full_path = Path(settings.MEDIA_ROOT) / link
        return open(full_path, "rb"), full_path.name


class DefaultStorageBackend(StorageBackend):
    """Upload backend that tries Box first and falls back to local storage on failure.

    ``download`` and ``list`` delegate to the backend matching the link scheme,
    so links produced by either backend continue to resolve correctly.
    """

    def upload(self, file: IO[bytes], path: str) -> str:
        """Try Box; on any error reset the stream and write locally instead."""
        import logging
        logger = logging.getLogger(__name__)
        try:
            return BoxStorageBackend().upload(file, path)
        except Exception as exc:
            logger.warning("Box upload failed (%s); falling back to local storage", exc)
            if hasattr(file, "seek"):
                file.seek(0)
            return LocalStorageBackend().upload(file, path)

    def list(self, path: str) -> list[str]:
        """Return links from both backends merged."""
        box_links = []
        try:
            box_links = BoxStorageBackend().list(path)
        except Exception:
            pass
        return box_links + LocalStorageBackend().list(path)

    def download(self, link: str) -> tuple[IO[bytes], str]:
        """Delegate to whichever backend owns this link."""
        return get_backend(link).download(link)


def get_backend(link: str) -> StorageBackend:
    """Return the backend that owns *link* (for download/list by known link)."""
    if link.startswith(BoxStorageBackend.SCHEME):
        return BoxStorageBackend()
    return LocalStorageBackend()


def get_upload_backend() -> StorageBackend:
    """Return the default backend for new uploads (Box with local fallback)."""
    return DefaultStorageBackend()
