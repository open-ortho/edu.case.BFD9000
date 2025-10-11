"""Filename metadata extractor infrastructure."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Sequence, Union


@dataclass(frozen=True)
class MetadataExtractionResult:
    """Structured data returned by filename extractors."""

    patient_id: str
    patient_sex: str
    patient_age: str
    image_type: Optional[str] = None
    collection: Optional[str] = None
    source: Optional[Path] = None


class MetadataExtractionError(ValueError):
    """Raised when filename metadata cannot be parsed or validated."""


class FilenameMetadataExtractor(ABC):
    """Base class for filename-driven metadata extractors."""

    #: Identifier for the source collection supported by the extractor.
    collection: str = "unknown"

    @abstractmethod
    def supports(self, file_path: Path) -> bool:
        """Return ``True`` when this extractor can handle *file_path*."""

    @abstractmethod
    def extract(self, file_path: Path) -> MetadataExtractionResult:
        """Parse and validate metadata from *file_path*."""


class ExtractorRegistry:
    """Registry of available filename metadata extractors."""

    def __init__(self, extractors: Sequence[FilenameMetadataExtractor]):
        self._extractors = tuple(extractors)

    @property
    def extractors(self) -> Sequence[FilenameMetadataExtractor]:
        """Return the registered extractors (immutable)."""

        return self._extractors

    def iter_for_collection(self, collection: Optional[str]) -> Iterable[FilenameMetadataExtractor]:
        """Yield extractors matching *collection* (or all when ``None``)."""

        for extractor in self._extractors:
            if collection is None or extractor.collection == collection:
                yield extractor

    def extract(
        self,
        file_path: Union[str, Path],
        *,
        collection: Optional[str] = None,
    ) -> MetadataExtractionResult:
        """Extract metadata using the first matching extractor in the registry."""

        path = Path(file_path)
        attempted = []
        for extractor in self.iter_for_collection(collection):
            if not extractor.supports(path):
                continue
            try:
                return extractor.extract(path)
            except MetadataExtractionError as exc:  # pragma: no cover - re-raised below
                attempted.append(f"{extractor.collection}: {exc}")
                raise

        if collection is not None:
            raise MetadataExtractionError(
                f"No filename extractor registered for collection '{collection}'."
            )
        raise MetadataExtractionError(
            f"No filename extractor could handle '{path.name}'."
        )
