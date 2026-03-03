from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand

from archive.management.importers.record_types import import_record_types


class Command(BaseCommand):
    help = "Import CWRU record type codes from FHIR ValueSet expansion"

    def handle(self, *args: Any, **options: Any) -> None:
        count = import_record_types()
        self.stdout.write(self.style.SUCCESS(
            f"Imported {count} record type codes into valueset 'record_types'."
        ))
