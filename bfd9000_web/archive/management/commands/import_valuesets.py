from __future__ import annotations

from typing import Any
from django.core.management.base import BaseCommand, CommandError
from archive.management.importers.valuesets import import_valueset
from archive.constants import VALUESET_EXPAND_URLS

class Command(BaseCommand):
    help = "Import FHIR ValueSet expansions. Use --all or provide --slug and --expand-url."

    def add_arguments(self, parser) -> None:
        parser.add_argument('--slug', type=str, help='Internal ValueSet slug')
        parser.add_argument('--expand-url', type=str, help='FHIR $expand URL')
        parser.add_argument('--all', action='store_true', help='Import all valuesets from constants mapping')

    def handle(self, *args: Any, **options: Any) -> None:
        if options.get('all'):
            if not VALUESET_EXPAND_URLS:
                raise CommandError('No valuesets configured in VALUESET_EXPAND_URLS.')
            for slug, expand_url in VALUESET_EXPAND_URLS.items():
                count = import_valueset(expand_url=expand_url, slug=slug)
                self.stdout.write(self.style.SUCCESS(
                    f"Imported {count} codings into ValueSet '{slug}'."
                ))
            return

        slug = options.get('slug')
        expand_url = options.get('expand_url')
        if not slug or not expand_url:
            raise CommandError('Use --all or provide both --slug and --expand-url.')
        count = import_valueset(expand_url=expand_url, slug=slug)
        self.stdout.write(self.style.SUCCESS(
            f"Imported {count} codings into ValueSet '{slug}'."
        ))
