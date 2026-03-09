"""Background worker for uploading media files."""

import logging
import time
from pathlib import Path

from box_sdk_gen import BoxAPIError, BoxClient, BoxJWTAuth, CreateFolderParent, FileBaseTypeField, FolderBaseTypeField, JWTConfig, WebLinkBaseTypeField
from box_sdk_gen.box.developer_token_auth import BoxDeveloperTokenAuth
from box_sdk_gen.managers.uploads import (
    PreflightFileUploadCheckParent,
    UploadFileAttributes,
    UploadFileAttributesParentField,
)
from django.conf import settings
from dataclasses import dataclass

from BFD9000.settings import (
    BOX_DEVELOPER_TOKEN,
    BOX_FOLDER_ID,
    BOX_JWT_CONFIG_FILE,
)

logger = logging.getLogger(__name__)

# Cache for folder/file lookups: {(parent_folder_id, item_name): (item_id, item_type) | None}
# This persists across multiple file uploads within the same worker session
# Using dynamic programming to avoid repeated API calls
@dataclass
class ItemData:
    id: str
    type: FileBaseTypeField | FolderBaseTypeField | WebLinkBaseTypeField

_item_cache: dict[tuple[str, str], ItemData | None] = {}


def _get_box_client() -> BoxClient:
    """Get an authenticated Box client."""
    if BOX_JWT_CONFIG_FILE:
        jwt_config = JWTConfig.from_config_file(config_file_path=BOX_JWT_CONFIG_FILE)
        auth = BoxJWTAuth(config=jwt_config)  # pyright: ignore[reportArgumentType]
    elif BOX_DEVELOPER_TOKEN:
        auth = BoxDeveloperTokenAuth(token=BOX_DEVELOPER_TOKEN)
    else:
        raise RuntimeError(
            "Box authentication is not configured. Set BOX_DEVELOPER_TOKEN or "
            "BOX_JWT_CONFIG_FILE to enable Box client authentication."
        )

    return BoxClient(auth=auth)


def media_upload_worker():
    if not BOX_DEVELOPER_TOKEN and not BOX_JWT_CONFIG_FILE:
        logger.error("worker cannot start: neither envar BOX_DEVELOPER_TOKEN nor BOX_JWT_CONFIG_FILE is set")
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
    """Process all files in the media/uploads directory for upload."""
    media_root = Path(settings.MEDIA_ROOT).joinpath("uploads")

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
        logger.debug(f"Handling media file: {file_path}")
        # Attempt to upload the file
        if upload_file(file_path):
            # Delete the file after successful upload
            file_path.unlink()
            logger.debug(f"Deleted local file: {file_path}")

            # Prune parent directory if empty
            prune_empty_directory(file_path.parent)
            return True
        else:
            return False
    except Exception as e:
        logger.error(f"Error handling file {file_path}: {e}", exc_info=True)
        return False


def upload_file(file_path: Path) -> bool:
    """
    Upload a file to Box.com, creating folder structure as needed, and deleting the file if it already exists.

    The folder structure in Box will mirror the structure relative to MEDIA_ROOT.
    For example: /media/patient123/scan001/image.jpg -> BOX_FOLDER_ID/patient123/scan001/image.jpg
    """
    try:
        client = _get_box_client()
        media_root = Path(settings.MEDIA_ROOT)

        # Get the relative path from MEDIA_ROOT
        relative_path = file_path.relative_to(media_root)
        folder_parts = relative_path.parent.parts
        file_name = file_path.name

        # Navigate/create folder structure starting from root folder
        current_folder_id = BOX_FOLDER_ID or "0"

        for folder_name in folder_parts:
            current_folder_id = _get_or_create_folder(client, current_folder_id, folder_name)
            if not current_folder_id:
                logger.error(f"Failed to create/navigate to folder: {folder_name}")
                return False

        file_size = file_path.stat().st_size

        # Preflight check: verify the file will be accepted before uploading
        upload_url = None
        for _ in range(3):
            try:
                upload_url = client.uploads.preflight_file_upload_check(
                    name=file_name,
                    size=file_size,
                    parent=PreflightFileUploadCheckParent(id=current_folder_id),
                )
                break
            except BoxAPIError as e:
                if e.response_info.status_code == 409:
                    logger.debug(f"File already exists! deleting {file_name}...")
                    file_id = e.response_info.context_info['conflicts']['id']  # pyright: ignore[reportOptionalSubscript]
                    client.files.delete_file_by_id(file_id)

                    # Invalidate cache for this file
                    cache_key = (current_folder_id, file_name)
                    if cache_key in _item_cache:
                        del _item_cache[cache_key]
                        logger.debug(f"Invalidated cache for deleted file: {file_name}")
                else:
                    logger.error(f"Preflight check failed: {e}")
                    return False
        if upload_url is None:
            raise RuntimeError("Internal Error: multiple 409 responses recieved when trying to upload file.")

        # Upload the file
        with open(file_path, 'rb') as file_stream:
            if file_size > 50_000_000:
                session_id = upload_url.upload_url.rsplit('?', 1)[1]  # pyright: ignore[reportOptionalMemberAccess]
                raise NotImplementedError("TODO: implement chunked uploads for files > 50MB")
                # https://developer.box.com/reference/put-files-upload-sessions-id
            else:
                result = client.uploads.upload_file(
                    attributes=UploadFileAttributes(
                        name=file_name,
                        parent=UploadFileAttributesParentField(id=current_folder_id),
                    ),
                    file=file_stream,
                )
                uploaded_file = result.entries[0]  # pyright: ignore[reportOptionalSubscript]

            logger.debug(f"Uploaded {file_path} to Box (ID: {uploaded_file.id})")
            return True

    except BoxAPIError as e:
        logger.error(f"Box API error uploading {file_path}: {e}", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"Error uploading {file_path}: {e}", exc_info=True)
        return False

def _get_item_by_name(client: BoxClient, folder_id: str, name: str) -> ItemData | None:
    """
    Get an item (file or folder) by name within a parent folder.

    Uses dynamic programming (memoization) to cache results and avoid repeated API calls.
    Cache stores (item_id, item_type) tuples to minimize API queries.
    """
    cache_key = (folder_id, name)

    # Check cache first
    if cache_key in _item_cache:
        cached_data = _item_cache[cache_key]
        if cached_data is None:
            logger.debug(f"Cache hit (not found): {name} in folder {folder_id}")
            return None

        logger.debug(f"Cache hit: {name} -> {cached_data.id} (type: {cached_data.type})")

        # Create a minimal Item object from cached data
        # This avoids another API call to fetch the full item
        return cached_data

    # Cache miss - query Box API
    try:
        items = client.folders.get_folder_items(folder_id)

        while True:
            for item in items.entries or []:
                if item.name == name:
                    logger.debug(f"Found item by name: {item.id} {name} (type: {item.type})")
                    # Cache the result as ItemData object
                    data = ItemData(id=item.id, type=item.type)
                    _item_cache[cache_key] = data
                    return data
            if items.next_marker is None:
                break
            items = client.folders.get_folder_items(folder_id, marker=items.next_marker)

        # Item not found, cache the negative result
        logger.debug(f"Item not found (caching negative result): {name} in folder {folder_id}")
        _item_cache[cache_key] = None
    except BoxAPIError as e:
        logger.error(f"Box API error getting item by name: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Error getting item by name: {e}", exc_info=True)

    return None

def _get_or_create_folder(client: BoxClient, parent_folder_id: str, folder_name: str) -> str | None:
    """
    Get existing folder ID or create it if it doesn't exist.

    Uses cached results from _get_item_by_name and updates cache when creating new folders.
    """
    try:
        item = _get_item_by_name(client, parent_folder_id, folder_name)
        if item is None:
            # Folder doesn't exist, create it
            subfolder = client.folders.create_folder(name=folder_name, parent=CreateFolderParent(id=parent_folder_id))
            logger.debug(f"Created folder: {folder_name} (ID: {subfolder.id})")

            # Update cache with newly created folder
            cache_key = (parent_folder_id, folder_name)
            _item_cache[cache_key] = ItemData(id=subfolder.id, type=FolderBaseTypeField.FOLDER)

            return subfolder.id
        elif item.type == 'folder':
            return item.id
        else:
            logger.error(f"Item '{folder_name}' exists but is not a folder (type: {item.type})")
            return None
    except BoxAPIError as e:
        logger.error(f"Box API error creating folder {folder_name}: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Error creating folder {folder_name}: {e}", exc_info=True)
        return None


def prune_empty_directory(directory: Path):
    """Remove directory if it's empty, recursively prune parent directories."""
    media_root = Path(settings.MEDIA_ROOT)

    if directory == media_root or not directory.exists():
        return

    if not any(directory.iterdir()):
        directory.rmdir()
        # Recursively prune parent
        prune_empty_directory(directory.parent)
