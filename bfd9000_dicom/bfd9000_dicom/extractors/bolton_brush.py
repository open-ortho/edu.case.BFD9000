"""Filename extractor for the Bolton Brush collection."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from bfd9000_dicom.extractors.base import (
    FilenameMetadataExtractor,
    MetadataExtractionError,
    MetadataExtractionResult,
)


_BOLTON_PATTERN = re.compile(
    r"^(?P<patient_id>B\d{4})(?P<image_type>[A-Z0-9])(?P<sex>[MFOU])(?P<years>\d{2,3})y(?P<months>\d{2})m?$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class BoltonBrushLimits:
    """Validation boundaries for Bolton Brush filename components."""

    minimum_patient_number: int = 1
    maximum_patient_number: int = 9999
    allowed_image_types: tuple[str, ...] = ("L", "P", "1", "2")
    allowed_patient_sex: tuple[str, ...] = ("M", "F")


class BoltonBrushExtractor(FilenameMetadataExtractor):
    """Parse Bolton Brush filename metadata with strict validation."""

    collection = "bolton_brush"

    def __init__(self, *, limits: Optional[BoltonBrushLimits] = None) -> None:
        self._limits = limits or BoltonBrushLimits()

    def supports(self, file_path: Path) -> bool:
        return bool(_BOLTON_PATTERN.match(file_path.stem))

    def extract(self, file_path: Path) -> MetadataExtractionResult:
        match = _BOLTON_PATTERN.match(file_path.stem)
        if not match:
            raise MetadataExtractionError(
                "Filename does not match Bolton Brush pattern 'BXXXXYSTT y TT m'."
            )

        patient_id = match.group('patient_id').upper()
        image_type = match.group('image_type').upper()
        patient_sex = match.group('sex').upper()
        years = int(match.group('years'))
        months = int(match.group('months'))

        self._validate_patient_id(patient_id)
        self._validate_image_type(image_type)
        self._validate_patient_sex(patient_sex)
        self._validate_age(years, months)

        total_months = years * 12 + months
        if total_months > 999:
            raise MetadataExtractionError(
                "Patient age exceeds DICOM AS representation limit (999 months)."
            )

        age_string = f"{total_months:03d}M"

        return MetadataExtractionResult(
            patient_id=patient_id,
            patient_sex=patient_sex,
            patient_age=age_string,
            image_type=image_type,
            collection=self.collection,
            source=file_path,
        )

    def _validate_patient_id(self, patient_id: str) -> None:
        number = int(patient_id[1:])
        if not (self._limits.minimum_patient_number <= number <= self._limits.maximum_patient_number):
            raise MetadataExtractionError(
                f"Patient ID '{patient_id}' outside expected range "
                f"B{self._limits.minimum_patient_number:04d}-B{self._limits.maximum_patient_number:04d}."
            )

    def _validate_image_type(self, image_type: str) -> None:
        if image_type not in self._limits.allowed_image_types:
            allowed = ', '.join(self._limits.allowed_image_types)
            raise MetadataExtractionError(
                f"Image type '{image_type}' is not permitted for the Bolton Brush collection. "
                f"Expected one of: {allowed}."
            )

    def _validate_patient_sex(self, patient_sex: str) -> None:
        if patient_sex not in self._limits.allowed_patient_sex:
            allowed = ', '.join(self._limits.allowed_patient_sex)
            raise MetadataExtractionError(
                f"Patient sex '{patient_sex}' is not valid for the Bolton Brush collection. "
                f"Expected one of: {allowed}."
            )

    @staticmethod
    def _validate_age(years: int, months: int) -> None:
        if not (0 <= months < 12):
            raise MetadataExtractionError("Months component must be between 00 and 11.")
        if years < 0:
            raise MetadataExtractionError("Years component must be non-negative.")
