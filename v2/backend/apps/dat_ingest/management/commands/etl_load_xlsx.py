"""
ETL Command: Load .xlsx files to staging tables
"""

import os
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.dat_ingest.models import ImportLog, StgMunicipio, StgProjeto, StgTipoEvento, StgUsuario
from apps.dat_ingest.services.loaders import (
    compute_file_hash,
    load_workbook_index,
    parse_municipios,
    parse_projetos,
    parse_tipos_evento,
    parse_usuarios,
)


class Command(BaseCommand):
    help = "Load .xlsx files from DATA_IMPORT_DIR to staging tables (idempotent via SHA256)"

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

        if not directory.exists():
            self.stdout.write(self.style.ERROR(f"Directory not found: {directory}"))
            return

        files = load_workbook_index(directory)
        if not files:
            self.stdout.write(self.style.WARNING(f"No .xlsx files found in {directory}"))
            return

        self.stdout.write(f"Found {len(files)} .xlsx files")

        for filepath in files:
            self._process_file(filepath, dry_run=dry_run, only=only)

    @transaction.atomic
    def _process_file(self, filepath: Path, dry_run: bool = False, only: str = None):
        """Process single Excel file"""
        digest = compute_file_hash(filepath)

        # Check if already processed
        if ImportLog.objects.filter(file=str(filepath), sha256=digest, ok=True).exists():
            self.stdout.write(self.style.SUCCESS(f"[SKIP] {filepath.name} (already processed)"))
            return

        self.stdout.write(f"\n[PROCESSING] {filepath.name}")

        # Create log entry
        log = ImportLog.objects.create(file=str(filepath), sha256=digest)
        total_rows = 0

        try:
            # Process each entity type
            if only is None or only == "usuarios":
                usuarios = parse_usuarios(filepath)
                if usuarios:
                    if not dry_run:
                        for u in usuarios:
                            StgUsuario.objects.create(**u)
                    self.stdout.write(f"  ✓ Usuarios: {len(usuarios)} rows")
                    total_rows += len(usuarios)

            if only is None or only == "municipios":
                municipios = parse_municipios(filepath)
                if municipios:
                    if not dry_run:
                        for m in municipios:
                            StgMunicipio.objects.create(**m)
                    self.stdout.write(f"  ✓ Municipios: {len(municipios)} rows")
                    total_rows += len(municipios)

            if only is None or only == "projetos":
                projetos = parse_projetos(filepath)
                if projetos:
                    if not dry_run:
                        for p in projetos:
                            StgProjeto.objects.create(**p)
                    self.stdout.write(f"  ✓ Projetos: {len(projetos)} rows")
                    total_rows += len(projetos)

            if only is None or only == "tipos":
                tipos = parse_tipos_evento(filepath)
                if tipos:
                    if not dry_run:
                        for t in tipos:
                            StgTipoEvento.objects.create(**t)
                    self.stdout.write(f"  ✓ Tipos Evento: {len(tipos)} rows")
                    total_rows += len(tipos)

            if not dry_run:
                log.rows_processed = total_rows
                log.rows_success = total_rows
                log.mark_finished(success=True)

            self.stdout.write(self.style.SUCCESS(f"[OK] {filepath.name} - {total_rows} rows total"))

        except Exception as e:
            if not dry_run:
                log.mark_finished(success=False, error=str(e))
            self.stdout.write(self.style.ERROR(f"[ERROR] {filepath.name}: {e}"))
            raise
