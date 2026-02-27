from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand

from archive.management.importers.bolton import BoltonImporter


class Command(BaseCommand):
    help = "Import Bolton subjects and identifiers from BoltonSubjects2.xlsx"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--file",
            default="BoltonSubjects2.xlsx",
            help="Path to BoltonSubjects2.xlsx",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse and validate without writing to the database",
        )
        parser.add_argument(
            "--include-names",
            action="store_true",
            help="Populate first/last names when available",
        )

    def handle(self, *args, **options) -> None:
        importer = BoltonImporter(
            dry_run=options["dry_run"],
            include_names=options["include_names"],
            stdout=self.stdout,
            stderr=self.stderr,
        )
        importer.run(Path(options["file"]).expanduser().resolve())
