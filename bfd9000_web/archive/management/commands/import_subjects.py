"""Management command entrypoint for historical imports."""

from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from archive.constants import SYSTEM_IDENTIFIER_LANCASTER_SUBJECT
from archive.management.importers.bolton import BoltonImporter
from archive.management.importers.lancaster import LancasterImporter


class Command(BaseCommand):
    """Dispatch imports by dataset source."""
    help = "Import historical subjects from supported datasets"

    def add_arguments(self, parser) -> None:
        subparsers = parser.add_subparsers(dest="source", required=True)

        bolton = subparsers.add_parser("bolton", help="Import Bolton subjects")
        bolton.add_argument(
            "--file",
            default="BoltonSubjects2.xlsx",
            help="Path to BoltonSubjects2.xlsx",
        )
        bolton.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse and validate without writing to the database",
        )
        bolton.add_argument(
            "--include-names",
            action="store_true",
            help="Populate first/last names when available",
        )

        lancaster = subparsers.add_parser("lancaster", help="Import Lancaster subjects")
        lancaster.add_argument(
            "--file",
            default="LancasterDemographic.csv",
            help="Path to LancasterDemographic.csv",
        )
        lancaster.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse and validate without writing to the database",
        )
        lancaster.add_argument(
            "--include-names",
            action="store_true",
            help="Populate first/last names when available",
        )
        lancaster.add_argument(
            "--identifier-prefix",
            default="L",
            help="Prefix for formatted Lancaster identifiers",
        )
        lancaster.add_argument(
            "--identifier-width",
            type=int,
            default=8,
            help="Zero-padding width for Lancaster identifiers",
        )
        lancaster.add_argument(
            "--identifier-system",
            default=SYSTEM_IDENTIFIER_LANCASTER_SUBJECT,
            help="Identifier system URL for Lancaster subjects",
        )
        lancaster.add_argument(
            "--collection-short-name",
            default="Lancaster",
            help="Collection short name for Lancaster dataset",
        )
        lancaster.add_argument(
            "--collection-full-name",
            default="Lancaster",
            help="Collection full name for Lancaster dataset",
        )

    def handle(self, *args, **options) -> None:
        source = options.get("source")
        if source == "bolton":
            importer = BoltonImporter(
                dry_run=options["dry_run"],
                include_names=options["include_names"],
                stdout=self.stdout,
                stderr=self.stderr,
            )
            importer.run(Path(options["file"]).expanduser().resolve())
            return

        if source == "lancaster":
            importer = LancasterImporter(
                dry_run=options["dry_run"],
                include_names=options["include_names"],
                stdout=self.stdout,
                stderr=self.stderr,
                identifier_prefix=options["identifier_prefix"],
                identifier_width=options["identifier_width"],
                identifier_system=options["identifier_system"],
                collection_short_name=options["collection_short_name"],
                collection_full_name=options["collection_full_name"],
            )
            importer.run(Path(options["file"]).expanduser().resolve())
            return

        raise CommandError(f"Unknown import source: {source}")
