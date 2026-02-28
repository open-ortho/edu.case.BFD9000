"""Utilities for media processing and transformations."""

from io import BytesIO
import os
from typing import Optional, Any, Dict

from django.conf import settings
from PIL import Image


def get_bits_per_sample(img: Image.Image) -> Optional[int]:
    """Best-effort extraction of TIFF bits-per-sample."""
    tag_v2 = getattr(img, "tag_v2", None)
    if tag_v2 is None:
        return None
    bits = tag_v2.get(258)
    if bits is None:
        return None
    if isinstance(bits, tuple):
        return int(max(bits))
    return int(bits)


def resize_image_for_preview(img: Image.Image, max_dim: int = 1024) -> Image.Image:
    """Resize while preserving aspect ratio for display/preview."""
    width, height = img.size
    largest = max(width, height)
    if largest <= max_dim:
        return img
    scale = max_dim / float(largest)
    new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
    # Prefer NEAREST for 16-bit, else high-quality LANCZOS
    resample = Image.Resampling.NEAREST if img.mode.startswith("I;16") else Image.Resampling.LANCZOS
    return img.resize(new_size, resample)


def apply_transform_ops(img: Image.Image, ops: list[Dict[str, Any]]) -> Image.Image:
    """Apply ordered rotate/flip operations (e.g., for Record preview)."""
    transformed = img.copy()
    for op in ops:
        degrees = int(op.get('rotation', 0)) % 360
        if degrees:
            transformed = transformed.rotate(-degrees, expand=True)
        if bool(op.get('flip', False)):
            transformed = transformed.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    return transformed


def convert_tiff_to_png_bytes(upload) -> bytes:
    """Convert TIFF to PNG, preserving 16-bit grayscale if needed."""
    from PIL import Image  # ensure correct import in this helper
    with Image.open(upload) as img:
        bits_per_sample = get_bits_per_sample(img)
        high_bit_gray = bits_per_sample in {12, 16} or img.mode in {"I;16", "I;16L", "I;16B"}
        if high_bit_gray:
            gray = img
            if gray.mode == "I;16B":
                gray = gray.convert("I")
            elif gray.mode not in {"I;16", "I;16L", "I"}:
                gray = gray.convert("I")
            if bits_per_sample == 12:
                if gray.mode != "I":
                    gray = gray.convert("I")
            png_image = gray.convert("I;16")
            png_image = resize_image_for_preview(png_image)
        else:
            png_image = resize_image_for_preview(img.convert("RGB"))
        buf = BytesIO()
        png_image.save(buf, format="PNG", optimize=True)
        return buf.getvalue()


def generate_thumbnail_jpeg_bytes(
    fileobj, filename: str, transform_ops: Optional[list[Dict[str, Any]]] = None
) -> Optional[bytes]:
    """
    Unified thumbnail generator with transform_ops and TIFF PNG workflow.
    - For TIFF: converts to PNG bytes, reloads PNG as PIL, then continues.
    - For PNG/JPEG: loads via PIL.
    - For 3D/file types (stl, ply, obj): returns None.
    Returns:
        Bytes for JPEG thumbnail, or None (3D or unsupported)
    """
    ext = os.path.splitext(filename)[1].lower().lstrip('.')
    raster_types = {"png", "tif", "tiff", "jpeg", "jpg"}
    non_raster_types = {"stl", "ply", "obj"}
    if ext in non_raster_types:
        return None
    if ext not in raster_types:
        return None
    try:
        fileobj.seek(0)
        img: Image.Image
        if ext in {"tif", "tiff"}:
            png_bytes = convert_tiff_to_png_bytes(fileobj)
            img = Image.open(BytesIO(png_bytes))
        else:
            img = Image.open(fileobj)
        if transform_ops:
            img = apply_transform_ops(img, transform_ops)
        return _render_thumbnail_from_raster(img)
    except Exception:
        pass
    return None

def _render_thumbnail_from_raster(img: Image.Image) -> Optional[bytes]:
    """
    Create JPEG thumbnail bytes with project thumbnail compression policy. 
    Target: 300x300 px, ~20KB, hard 100KB limit (from settings)
    """
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

