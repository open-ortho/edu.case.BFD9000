"""Shared helpers for dataset importers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional

from django.core.management.base import CommandError

from archive.constants import SYSTEM_PROCEDURE
from archive.models import Coding, Collection, Identifier, Subject


@dataclass
class ImportStats:
    """Basic counters for import progress reporting."""
    subjects_created: int = 0
    subjects_updated: int = 0
    identifiers_created: int = 0
    identifiers_attached: int = 0
    rows_skipped: int = 0


class BaseImporter:
    """Common helper methods used across dataset importers."""
    def __init__(self, *, dry_run: bool, include_names: bool, stdout, stderr) -> None:
        self.dry_run = dry_run
        self.include_names = include_names
        self.stdout = stdout
        self.stderr = stderr

    def _get_or_create_collection(self, short_name: str, full_name: Optional[str] = None) -> Collection:
        full_name_value = full_name or short_name
        collection, _ = Collection.objects.get_or_create(
            short_name=short_name,
            defaults={"full_name": full_name_value},
        )
        return collection

    def _attach_identifier(
        self,
        subject: Subject,
        system: str,
        value: str,
        use: str,
        stats: ImportStats,
    ) -> None:
        identifier, created = Identifier.objects.get_or_create(
            system=system,
            value=value,
            defaults={"use": use},
        )
        if created:
            stats.identifiers_created += 1
        if not subject.identifiers.filter(pk=identifier.pk).exists():
            subject.identifiers.add(identifier)
            stats.identifiers_attached += 1

    def _map_gender(self, value: str) -> str:
        gender_map = {label[0].upper(): key for key, label in Subject.GENDER_CHOICES}
        normalized = value.strip().upper()
        return gender_map.get(normalized, "unknown")

    def _normalize_date(self, value) -> date:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if hasattr(value, "date"):
            return value.date()
        raw = str(value).strip()
        try:
            return datetime.fromisoformat(raw).date()
        except ValueError:
            pass
        try:
            return date.fromisoformat(raw)
        except ValueError as exc:
            raise CommandError(f"Invalid date format: {value}") from exc

    def _get_or_create_procedure(self) -> Coding:
        procedure, _ = Coding.objects.get_or_create(
            system=SYSTEM_PROCEDURE,
            code="historical-import-encounter",
            defaults={"display": "Historical imported encounter"},
        )
        return procedure

    def _cell_str(self, value) -> str:
        if value is None:
            return ""
        return str(value).strip()

    @staticmethod
    def _expand_two_digit_year(year: int) -> int:
        if year >= 30:
            return 1900 + year
        return 2000 + year

    @staticmethod
    def _midpoint_date_for_year(year: int) -> date:
        start = date(year, 1, 1)
        end = date(year + 1, 1, 1)
        midpoint_days = (end - start).days // 2
        return start + timedelta(days=midpoint_days)
