"""Utilities for media processing and transformations."""

from io import BytesIO
import os
from typing import Optional

from django.conf import settings
from PIL import Image


def generate_thumbnail_jpeg_bytes(fileobj, filename: str, transform_ops: Optional[list[str]] = None) -> Optional[bytes]:
    """
    Unified thumbnail generator:
    - For supported raster formats (png, tif/tiff, jpeg/jpg): returns JPEG thumbnail bytes
    - For 3D/file types (stl, ply, obj): returns None
    - For unknown types: returns None

    Args:
        fileobj: file-like object
        filename: source filename or path used to detect extension
        transform_ops: optional transform operations (reserved for future use)
    Returns:
        Bytes for JPEG thumbnail, or None (3D or unsupported)
    """
    del transform_ops

    ext = os.path.splitext(filename)[1].lower().lstrip('.')
    raster_types = {"png", "tif", "tiff", "jpeg", "jpg"}
    non_raster_types = {"stl", "ply", "obj"}

    if ext in non_raster_types:
        return None
    if ext not in raster_types:
        return None
    try:
        fileobj.seek(0) # pyright: ignore[reportUnknownMemberType]
        with Image.open(fileobj) as img:
            return _render_thumbnail_from_raster(img)
    except Exception:
        pass
    return None

def _render_thumbnail_from_raster(img: Image.Image) -> Optional[bytes]:
    """Create JPEG thumbnail bytes with target and hard-limit controls."""
    max_width: int = int(getattr(settings, 'THUMBNAIL_MAX_WIDTH', 300))
    max_height: int = int(getattr(settings, 'THUMBNAIL_MAX_HEIGHT', 300))
    target_bytes: int = int(getattr(settings, 'THUMBNAIL_TARGET_BYTES', 20 * 1024))
    hard_max_bytes: int = int(getattr(settings, 'THUMBNAIL_HARD_MAX_BYTES', 100 * 1024))
    default_quality: int = int(getattr(settings, 'THUMBNAIL_DEFAULT_QUALITY', 75))
    min_quality: int = int(getattr(settings, 'THUMBNAIL_MIN_QUALITY', 40))

    processed: Image.Image = img.copy()
    if processed.mode not in ('RGB', 'RGBA'):
        processed = processed.convert('RGB')
    elif processed.mode == 'RGBA':
        processed = processed.convert('RGB')

    processed.thumbnail((max_width, max_height))

    quality = default_quality
    best_fit: Optional[bytes] = None
    while quality >= min_quality:
        out = BytesIO()
        processed.save(out, format='JPEG', quality=quality, optimize=True)
        payload = out.getvalue()
        if len(payload) <= target_bytes:
            return payload
        if len(payload) <= hard_max_bytes:
            best_fit = payload
        quality -= 5

    return best_fit

