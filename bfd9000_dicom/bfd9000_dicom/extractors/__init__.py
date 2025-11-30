"""Extractor package providing validated metadata from filenames."""

from pathlib import Path
from typing import Optional, Union

from bfd9000_dicom.extractors.base import (
    ExtractorRegistry,
    FilenameMetadataExtractor,
    MetadataExtractionError,
    MetadataExtractionResult,
)
from bfd9000_dicom.extractors.bolton_brush import BoltonBrushExtractor

_DEFAULT_REGISTRY = ExtractorRegistry((BoltonBrushExtractor(),))


def get_registry() -> ExtractorRegistry:
    """Return the default extractor registry."""

    return _DEFAULT_REGISTRY


def extract_metadata_from_filename(
    file_path: Union[str, Path],
    *,
    collection: Optional[str] = None,
    registry: Optional[ExtractorRegistry] = None,
) -> MetadataExtractionResult:
    """Extract metadata using the configured filename extractors."""

    active_registry = registry or _DEFAULT_REGISTRY
    return active_registry.extract(file_path, collection=collection)


__all__ = [
    'MetadataExtractionResult',
    'MetadataExtractionError',
    'FilenameMetadataExtractor',
    'ExtractorRegistry',
    'BoltonBrushExtractor',
    'get_registry',
    'extract_metadata_from_filename',
]
