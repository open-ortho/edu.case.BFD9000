"""Storage backend abstraction for media files.

Backends use URIs to identify stored files:
  - Box:   ``box://<file_id>``
  - Local: relative path from ``MEDIA_ROOT``

Usage::

    # Download an existing file by its stored uri
    stream, filename = Storage(uri).download(uri)

    # Upload a new file (
    uri = Storage().upload(file_obj, "patient/scan/image.tif")
    uris = Storage().list("patient/scan/")
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from os import PathLike
from pathlib import Path
import shutil
from typing import IO, Iterator, Optional

from box_sdk_gen import FileBaseTypeField
from box_sdk_gen.schemas.folder_mini import FolderBaseTypeField
from django.conf import settings

logger = logging.getLogger(__name__)


# ── Box client helpers ────────────────────────────────────────────────────────

@dataclass
class _ItemData:
    id: str
    type: FolderBaseTypeField | FileBaseTypeField


# avoid repeated API calls. (parent_id, name) -> _ItemData | None
_box_item_cache: dict[tuple[str, str], _ItemData | None] = {}


def _get_box_client():
    """Return an authenticated Box client.

    Authentication precedence: developer token > JWT > OAuth.

    For OAuth, the token must have been obtained previously via the
    ``/box/oauth/start/`` → ``/box/oauth/callback/`` flow and will be
    loaded from the file-backed token storage configured by
    ``BOX_TOKEN_STORAGE_PATH``.
    """
    from BFD9000.settings import (
        BOX_DEVELOPER_TOKEN,
        BOX_JWT_CONFIG_FILE,
        BOX_OAUTH_CLIENT_ID,
        BOX_OAUTH_CLIENT_SECRET,
        BOX_TOKEN_STORAGE_PATH,
    )
    from box_sdk_gen import BoxClient, BoxJWTAuth, BoxOAuth, JWTConfig, OAuthConfig
    from box_sdk_gen.box.developer_token_auth import BoxDeveloperTokenAuth
    from box_sdk_gen.box.token_storage import FileTokenStorage

    if BOX_DEVELOPER_TOKEN:
        auth = BoxDeveloperTokenAuth(token=BOX_DEVELOPER_TOKEN)
    elif BOX_JWT_CONFIG_FILE:
        jwt_config = JWTConfig.from_config_file(config_file_path=BOX_JWT_CONFIG_FILE)
        auth = BoxJWTAuth(config=jwt_config)  # pyright: ignore[reportArgumentType]
    elif BOX_OAUTH_CLIENT_ID and BOX_OAUTH_CLIENT_SECRET:
        token_storage = FileTokenStorage(filename=BOX_TOKEN_STORAGE_PATH)
        auth = BoxOAuth(
            OAuthConfig(
                client_id=BOX_OAUTH_CLIENT_ID,
                client_secret=BOX_OAUTH_CLIENT_SECRET,
                token_storage=token_storage,
            )
        )
    else:
        raise RuntimeError(
            "Box authentication is not configured. Set BOX_DEVELOPER_TOKEN, "
            "BOX_JWT_CONFIG_FILE, or BOX_OAUTH_CLIENT_ID + BOX_OAUTH_CLIENT_SECRET."
        )
    return BoxClient(auth=auth)


def _get_item_by_name(client, folder_id: str, name: str) -> _ItemData | None:
    """Look up a file or folder by name within a Box folder, with caching."""
    cache_key = (folder_id, name)
    if cache_key in _box_item_cache:
        result = _box_item_cache[cache_key]
        logger.debug(
            "Cache hit (%s): %s in folder %s",
            "not found" if result is None else result.id,
            name,
            folder_id,
        )
        return result

    try:
        items = client.folders.get_folder_items(folder_id)
        while True:
            for item in items.entries or []:
                if item.name == name:
                    logger.debug("Found item by name: %s %s (type: %s)", item.id, name, item.type)
                    data = _ItemData(id=item.id, type=item.type)
                    _box_item_cache[cache_key] = data
                    return data
            if items.next_marker is None:
                break
            items = client.folders.get_folder_items(folder_id, marker=items.next_marker)

        logger.debug("Item not found (caching negative result): %s in folder %s", name, folder_id)
        _box_item_cache[cache_key] = None
    except Exception as exc:
        logger.error("Box API error getting item by name: %s", exc, exc_info=True)

    return None


def _get_or_create_folder(client, parent_folder_id: str, folder_name: str) -> str | None:
    """Return the ID of a Box folder, creating it if it does not exist."""
    from box_sdk_gen import BoxAPIError, CreateFolderParent

    try:
        item = _get_item_by_name(client, parent_folder_id, folder_name)
        if item is None:
            subfolder = client.folders.create_folder(
                name=folder_name,
                parent=CreateFolderParent(id=parent_folder_id),
            )
            logger.debug("Created Box folder: %s (ID: %s)", folder_name, subfolder.id)
            _box_item_cache[(parent_folder_id, folder_name)] = _ItemData(id=subfolder.id, type=FolderBaseTypeField.FOLDER)
            return subfolder.id
        if item.type == FolderBaseTypeField.FOLDER:
            return item.id
        logger.error("Item '%s' exists but is not a folder (type: %s)", folder_name, item.type)
        return None
    except BoxAPIError as exc:
        logger.error("Box API error creating folder %s: %s", folder_name, exc, exc_info=True)
        return None
    except Exception as exc:
        logger.error("Error creating folder %s: %s", folder_name, exc, exc_info=True)
        return None


# ── Abstract interface ────────────────────────────────────────────────────────

class StorageBackend(ABC):
    """Abstract interface for a file storage backend."""

    @abstractmethod
    def upload(self, file: IO[bytes], path: PathLike[str]) -> str:
        """Upload *file* to the given relative *path* and return a storage uri."""

    @abstractmethod
    def list(self, path: PathLike[str]) -> Iterator[str]:
        """Yield storage uris for every file found under *path*."""

    @abstractmethod
    def download(self, uri: str) -> tuple[IO[bytes], str]:
        """Download the resource identified by *uri*; return ``(stream, filename)``."""

    @abstractmethod
    def error(self) -> Optional[str]:
        """Returns ``None`` if the storage backend is alive and reachable, and a string error message otherwise."""


# ── Concrete backends ─────────────────────────────────────────────────────────

class BoxStorageBackend(StorageBackend):
    """Box.com storage backend.  uris use the ``box://<file_id>`` scheme."""

    SCHEME = "box://"

    def upload(self, file: IO[bytes], path: PathLike[str]) -> str:
        """Upload *file* to Box, mirroring the directory structure of *path*.

        Handles preflight checks and 409 conflicts (file already exists → delete
        and retry).  Raises ``NotImplementedError`` for files larger than 50 MB
        until chunked upload is implemented.

        Returns a ``box://<file_id>`` uri.
        """
        from BFD9000.settings import BOX_FOLDER_ID
        from box_sdk_gen import BoxAPIError
        from box_sdk_gen.managers.uploads import (
            PreflightFileUploadCheckParent,
            UploadFileAttributes,
            UploadFileAttributesParentField,
        )

        client = _get_box_client()
        parts = Path(path)
        file_name = parts.name
        current_folder_id = BOX_FOLDER_ID or "0"

        for folder_name in parts.parent.parts:
            fid = _get_or_create_folder(client, current_folder_id, folder_name)
            if fid is None:
                raise RuntimeError(f"Failed to create/navigate to Box folder: {folder_name}")
            current_folder_id = fid

        # Determine file size for preflight check (best-effort on seekable streams).
        file_size = 0
        try:
            pos = file.tell()
            file.seek(0, 2)
            file_size = file.tell()
            file.seek(pos)
        except (AttributeError, OSError):
            pass

        if file_size > 50_000_000:
            logger.warning("Chunked uploads (> 50 MB) are not yet implemented.")

        # Preflight check; retry up to 3 times on 409 (file exists → delete first).
        upload_url = None
        for _ in range(3):
            try:
                upload_url = client.uploads.preflight_file_upload_check(
                    name=file_name,
                    size=file_size,
                    parent=PreflightFileUploadCheckParent(id=current_folder_id),
                )
                break
            except BoxAPIError as exc:
                if exc.response_info.status_code == 409:
                    logger.debug("File already exists in Box; deleting %s …", file_name)
                    file_id = exc.response_info.context_info["conflicts"]["id"]  # pyright: ignore[reportOptionalSubscript]
                    client.files.delete_file_by_id(file_id)
                    _box_item_cache.pop((current_folder_id, file_name), None)
                else:
                    raise exc

        if upload_url is None:
            raise RuntimeError("Multiple 409 responses received during Box preflight check.")

        result = client.uploads.upload_file(
            attributes=UploadFileAttributes(
                name=file_name,
                parent=UploadFileAttributesParentField(id=current_folder_id),
            ),
            file=file,  # type: ignore[arg-type]
        )
        uploaded_file = result.entries[0]  # pyright: ignore[reportOptionalSubscript]
        logger.debug("Uploaded %s to Box (ID: %s)", path, uploaded_file.id)
        return f"{self.SCHEME}{uploaded_file.id}"

    def list(self, path: PathLike[str]) -> Iterator[str]:
        """Yield ``box://<file_id>`` uris for every file under *path* in Box."""
        from BFD9000.settings import BOX_FOLDER_ID

        client = _get_box_client()
        current_folder_id = BOX_FOLDER_ID or "0"

        for folder_name in Path(path).parts:
            item = _get_item_by_name(client, current_folder_id, folder_name)
            if item is None or item.type != FolderBaseTypeField.FOLDER:
                return
            current_folder_id = item.id

        items = client.folders.get_folder_items(current_folder_id)
        while True:
            for item in items.entries or []:
                if item.type == FileBaseTypeField.FILE:
                    yield f"{self.SCHEME}{item.id}"
            if items.next_marker is None:
                break
            items = client.folders.get_folder_items(current_folder_id, marker=items.next_marker)

    def download(self, uri: str) -> tuple[IO[bytes], str]:
        """Download the Box file identified by *uri*; return ``(stream, filename)``."""
        client = _get_box_client()
        file_id = uri[len(self.SCHEME):]
        file_info = client.files.get_file_by_id(file_id)
        stream = client.downloads.download_file(file_id)
        if stream is None:
            raise RuntimeError(f"Box returned no content for file id {file_id}")
        return stream, file_info.name  # type: ignore[return-value]

    def error(self) -> Optional[str]:
        """Return a string error message if the storage backend is alive and reachable, or ``None`` otherwise."""
        from BFD9000.settings import (
            BOX_DEVELOPER_TOKEN,
            BOX_JWT_CONFIG_FILE,
            BOX_OAUTH_CLIENT_ID,
            BOX_OAUTH_CLIENT_SECRET,
            BOX_FOLDER_ID
        )
        
        if not BOX_FOLDER_ID:
            return "BOX_FOLDER_ID is not configured"
        if (
            not BOX_DEVELOPER_TOKEN
            and not BOX_JWT_CONFIG_FILE
            and not (BOX_OAUTH_CLIENT_ID and BOX_OAUTH_CLIENT_SECRET)
        ):
            return "No Box authentication configured"
        client = _get_box_client()
        if BOX_OAUTH_CLIENT_ID and BOX_OAUTH_CLIENT_SECRET:
            if client.auth.retrieve_token():
                return None
            return "OAuth 2.0: no active token"
        return None


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage backend.  uris are paths relative to ``MEDIA_ROOT``."""

    def upload(self, file: IO[bytes], path: PathLike[str]) -> str:
        """Write *file* to *path* (relative to ``MEDIA_ROOT``) and return the path as a uri."""
        dest = Path(settings.MEDIA_ROOT) / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as f:
            f.write(file.read())
        return str(path)

    def list(self, path: PathLike[str]) -> Iterator[str]:
        """Yield relative paths for every file under *path* within ``MEDIA_ROOT``."""
        root = Path(settings.MEDIA_ROOT) / path
        if not root.exists():
            return
        yield from (
            str(p.relative_to(settings.MEDIA_ROOT))
            for p in root.rglob("*")
            if p.is_file()
        )

    def download(self, uri: str) -> tuple[IO[bytes], str]:
        """Open the local file at *uri* (relative to ``MEDIA_ROOT``); return ``(stream, filename)``."""
        full_path = Path(settings.MEDIA_ROOT) / uri
        return open(full_path, "rb"), full_path.name
        
    def error(self) -> Optional[str]:
        """Return an error if running low on disk space (< 5GiB), or ``None`` otherwise. This error is technically nonfatal."""
        try:
            total, used, free = shutil.disk_usage(settings.MEDIA_ROOT)
            if free < 5 * 1024 * 1024 * 1024:  # less than 5 GB
                return f"Disk space running low (free: {free / 1024 / 1024:2f} MiB)"
        except Exception as exc:
            return f"Error checking disk space: {exc}"
        return None


class Storage(StorageBackend):
    """Upload backend that tries Box first and falls back to local storage on failure.

    ``download`` and ``list`` delegate to the backend matching the uri scheme,
    so uris produced by either backend continue to resolve correctly.
    """

    def upload(self, file: IO[bytes], path: PathLike[str], fallback: bool = False) -> str:
        """Try Box; on any error reset the stream and write locally instead."""
        try:
            return BoxStorageBackend().upload(file, path)
        except Exception as exc:
            if fallback:
                logger.warning("Box upload failed, falling back to local storage (%s)", exc)
                file.seek(0)
                return LocalStorageBackend().upload(file, path)
            else:
                logger.error("Box upload failed, fallback=False (%s)", exc)
                raise exc

    def list(self, path: PathLike[str]) -> Iterator[str]:
        """Yield uris from both backends merged."""
        try:
            yield from BoxStorageBackend().list(path)
        except Exception:
            pass
        yield from LocalStorageBackend().list(path)

    def download(self, uri: str) -> tuple[IO[bytes], str]:
        """Delegate to whichever backend owns this uri."""
        if uri.startswith(BoxStorageBackend.SCHEME):
            return BoxStorageBackend().download(uri)
        return LocalStorageBackend().download(uri)
        
    def error(self) -> Optional[str]:
        """Return the errors for each backend."""
        e = ""
        box = BoxStorageBackend().error()
        if box:
            e += f"Box: {box}\n"
        local = LocalStorageBackend().error()
        if local:
            e += f"Local: {local}\n"
        return e or None
