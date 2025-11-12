"""
ETL Command: Import AcaoControle from CSV/XLSX

Usage:
    python manage.py etl_import_acoes_controle /path/to/file.csv --dry-run
    python manage.py etl_import_acoes_controle /path/to/file.xlsx
"""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false

from __future__ import annotations

from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.core.services.controle_acoes_import import import_acoes_controle


class Command(BaseCommand):
    help = "Import AcaoControle from CSV/XLSX (idempotent via external_hash)"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "file_path",
            type=str,
            help="Path to CSV or XLSX file with AcaoControle data",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate without writing to DB",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        file_path = Path(options["file_path"])
        dry_run = options["dry_run"]

        # Validate file exists
        if not file_path.exists():
            raise CommandError(f"File not found: {file_path}")

        # Validate file extension
        if file_path.suffix.lower() not in [".csv", ".xlsx", ".xls"]:
            raise CommandError(f"Unsupported file format: {file_path.suffix}. Use .csv, .xlsx, or .xls")

        # Display header
        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write(self.style.SUCCESS("IMPORT ACOES CONTROLE"))
        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write(f"File: {file_path}")

        if dry_run:
            self.stdout.write(self.style.WARNING("[DRY-RUN MODE] No changes will be saved\n"))

        # Run import
        try:
            report = import_acoes_controle(str(file_path), dry_run=dry_run)
        except Exception as e:
            raise CommandError(f"Import failed: {e}")

        # Display results
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("IMPORT STATISTICS"))
        self.stdout.write("=" * 80)

        stats = report["stats"]
        self.stdout.write(self.style.SUCCESS(f"✓ Created:   {stats['created']}"))
        self.stdout.write(self.style.SUCCESS(f"✓ Updated:   {stats['updated']}"))
        self.stdout.write(self.style.SUCCESS(f"○ Unchanged: {stats['unchanged']}"))

        skipped = stats["skipped"]
        total_skipped = sum(skipped.values())

        if total_skipped > 0:
            self.stdout.write(self.style.WARNING(f"\n⚠ Total Skipped: {total_skipped}"))
            if skipped["municipio"] > 0:
                self.stdout.write(self.style.WARNING(f"  - Município not found: {skipped['municipio']}"))
            if skipped["projeto"] > 0:
                self.stdout.write(self.style.WARNING(f"  - Projeto not found: {skipped['projeto']}"))
            if skipped["coordenador"] > 0:
                self.stdout.write(self.style.WARNING(f"  - Coordenador not found: {skipped['coordenador']}"))
            if skipped["dates"] > 0:
                self.stdout.write(self.style.WARNING(f"  - Invalid dates: {skipped['dates']}"))
            if skipped["other"] > 0:
                self.stdout.write(self.style.WARNING(f"  - Other errors: {skipped['other']}"))

        # Pendências summary
        pendencias = report["pendencias"]
        total_pendencias = sum(len(v) for v in pendencias.values())

        if total_pendencias > 0:
            self.stdout.write(self.style.WARNING(f"\n⚠ Total Pendências: {total_pendencias}"))
            if pendencias["municipios"]:
                self.stdout.write(self.style.WARNING(f"  - Municípios: {len(pendencias['municipios'])}"))
            if pendencias["projetos"]:
                self.stdout.write(self.style.WARNING(f"  - Projetos: {len(pendencias['projetos'])}"))
            if pendencias["coordenadores"]:
                self.stdout.write(self.style.WARNING(f"  - Coordenadores: {len(pendencias['coordenadores'])}"))
            if pendencias["outros"]:
                self.stdout.write(self.style.WARNING(f"  - Outros: {len(pendencias['outros'])}"))

        # Report file location
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("REPORT"))
        self.stdout.write("=" * 80)
        self.stdout.write(f"Full report saved to: out_etl/import_acoes_controle_report.json")

        if dry_run:
            self.stdout.write(self.style.WARNING("\n[DRY-RUN] No changes were committed to the database"))

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("IMPORT COMPLETE"))
        self.stdout.write("=" * 80 + "\n")
