"""
ETL Command: Orchestrator (etl_load_xlsx → etl_upsert_core)
"""

from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run full ETL pipeline: load xlsx → upsert to SSOT (idempotent)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dir",
            type=str,
            default=getattr(settings, "DATA_IMPORT_DIR", "/app/data/csv-import"),
            help="Directory with .xlsx files",
        )
        parser.add_argument("--dry-run", action="store_true", help="Simulate without writing to DB")
        parser.add_argument(
            "--only",
            choices=["usuarios", "municipios", "projetos", "tipos"],
            help="Process only specific entity type",
        )

    def handle(self, *args, **options):
        directory = Path(options["dir"])
        dry_run = options["dry_run"]
        only = options["only"]

        if dry_run:
            self.stdout.write(self.style.WARNING("\n[DRY-RUN MODE] No changes will be saved\n"))

        if not directory.exists():
            self.stdout.write(self.style.ERROR(f"Directory not found: {directory}"))
            return

        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write(self.style.SUCCESS("ETL PIPELINE START"))
        self.stdout.write(self.style.SUCCESS("=" * 80))

        # Step 1: Load .xlsx → staging tables
        self.stdout.write(
            self.style.SUCCESS("\n[STEP 1/2] Loading .xlsx files to staging tables...")
        )
        call_command(
            "etl_load_xlsx",
            dir=str(directory),
            dry_run=dry_run,
            only=only,
        )

        # Step 2: Upsert staging → SSOT tables
        self.stdout.write(
            self.style.SUCCESS("\n[STEP 2/2] Upserting staging → SSOT tables...")
        )
        call_command(
            "etl_upsert_core",
            dry_run=dry_run,
            only=only,
        )

        self.stdout.write(self.style.SUCCESS("\n" + "=" * 80))
        self.stdout.write(self.style.SUCCESS("ETL PIPELINE COMPLETE"))
        self.stdout.write(self.style.SUCCESS("=" * 80))
