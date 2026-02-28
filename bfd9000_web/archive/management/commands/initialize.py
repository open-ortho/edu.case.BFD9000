"""Project initialization command for local development setup."""

from __future__ import annotations

import os
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import BaseCommand, CommandError, call_command


class Command(BaseCommand):
    """Run migrate, create superuser, and import seed subject datasets."""

    help = "Initialize DB: migrate, createsuperuser, import_subjects"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--skip-migrate",
            action="store_true",
            help="Skip running migrate",
        )
        parser.add_argument(
            "--skip-superuser",
            action="store_true",
            help="Skip running createsuperuser",
        )
        parser.add_argument(
            "--skip-import",
            action="store_true",
            help="Skip running import_subjects",
        )
        parser.add_argument(
            "--non-interactive",
            action="store_true",
            help="Run createsuperuser with --noinput (requires env/options)",
        )

        parser.add_argument("--superuser-username", default=None)
        parser.add_argument("--superuser-email", default=None)
        parser.add_argument("--superuser-password", default=None)

        parser.add_argument(
            "--import-source",
            choices=["all", "bolton", "lancaster"],
            default="all",
            help="Which dataset importer(s) to run",
        )
        parser.add_argument(
            "--bolton-file",
            default=str(settings.BASE_DIR / "docs" / "collections_data" / "BoltonSubjects2.xlsx"),
            help="Path to BoltonSubjects2.xlsx",
        )
        parser.add_argument(
            "--lancaster-file",
            default=str(settings.BASE_DIR / "docs" / "collections_data" / "LancasterDemographic.csv"),
            help="Path to LancasterDemographic.csv",
        )
        parser.add_argument(
            "--include-names",
            action="store_true",
            help="Pass --include-names to import_subjects",
        )
        parser.add_argument(
            "--no-timepoints",
            action="store_true",
            help="Pass --no-timepoints to Bolton importer",
        )

    def handle(self, *args, **options) -> None:
        verbosity = int(options.get("verbosity", 1))

        if not options["skip_migrate"]:
            self.stdout.write(self.style.NOTICE("Running migrate..."))
            call_command("migrate", verbosity=verbosity)

        if not options["skip_superuser"]:
            self._run_createsuperuser(options, verbosity)

        if not options["skip_import"]:
            self._run_imports(options, verbosity)

        self.stdout.write(self.style.SUCCESS("Initialization complete."))

    def _run_createsuperuser(self, options: dict, verbosity: int) -> None:
        user_model = get_user_model()
        if user_model.objects.filter(is_superuser=True).exists():
            self.stdout.write(self.style.WARNING("Superuser already exists; skipping createsuperuser."))
            return

        non_interactive = bool(options.get("non_interactive"))
        if non_interactive:
            self._set_superuser_env(options)
            self.stdout.write(self.style.NOTICE("Running createsuperuser --noinput..."))
            try:
                call_command("createsuperuser", interactive=False, verbosity=verbosity)
            except CommandError as exc:
                raise CommandError(
                    "Failed to create superuser non-interactively. "
                    "Provide --superuser-username/--superuser-email/--superuser-password "
                    "or DJANGO_SUPERUSER_* environment variables."
                ) from exc
            return

        self.stdout.write(self.style.NOTICE("Running createsuperuser (interactive)..."))
        call_command("createsuperuser", verbosity=verbosity)

    def _set_superuser_env(self, options: dict) -> None:
        username = options.get("superuser_username")
        email = options.get("superuser_email")
        password = options.get("superuser_password")

        if username:
            os.environ["DJANGO_SUPERUSER_USERNAME"] = str(username)
        if email:
            os.environ["DJANGO_SUPERUSER_EMAIL"] = str(email)
        if password:
            os.environ["DJANGO_SUPERUSER_PASSWORD"] = str(password)

    def _run_imports(self, options: dict, verbosity: int) -> None:
        source = options["import_source"]
        include_names = bool(options.get("include_names"))

        if source in ("all", "bolton"):
            bolton_file = Path(options["bolton_file"]).expanduser().resolve()
            self.stdout.write(self.style.NOTICE(f"Importing Bolton subjects from {bolton_file}..."))
            call_command(
                "import_subjects",
                "bolton",
                file=str(bolton_file),
                include_names=include_names,
                no_timepoints=bool(options.get("no_timepoints")),
                verbosity=verbosity,
            )

        if source in ("all", "lancaster"):
            lancaster_file = Path(options["lancaster_file"]).expanduser().resolve()
            self.stdout.write(self.style.NOTICE(f"Importing Lancaster subjects from {lancaster_file}..."))
            call_command(
                "import_subjects",
                "lancaster",
                file=str(lancaster_file),
                include_names=include_names,
                verbosity=verbosity,
            )
