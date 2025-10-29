"""
Management Command: load_tipos_evento
Extrai tipos de evento de arquivo de agenda e persiste em StgTipoEvento + TipoEvento.
"""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.core.models import TipoEvento
from apps.dat_ingest.models import StgTipoEvento
from apps.dat_ingest.services.loaders import extract_tipos_evento_from_agenda


class Command(BaseCommand):
    help = "Load tipos de evento from agenda file"

    def add_arguments(self, parser):
        parser.add_argument(
            "--agenda-file",
            type=str,
            required=True,
            help="Path to agenda Excel file",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate without writing to DB",
        )

    def handle(self, *args, **options):
        agenda_file = options["agenda_file"]
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.WARNING("[DRY-RUN MODE] No changes will be saved"))

        # Validate file exists
        filepath = Path(agenda_file)
        if not filepath.exists():
            raise CommandError(f"Agenda file not found: {agenda_file}")

        # Extract tipos from agenda
        self.stdout.write(f"Extracting tipos de evento from {filepath.name}...")
        tipos_data = extract_tipos_evento_from_agenda(filepath)
        self.stdout.write(f"Found {len(tipos_data)} unique tipos")

        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"[DRY-RUN] Would process {len(tipos_data)} tipos"))
            return

        # Load to staging
        created_stg = self._load_staging(tipos_data)
        self.stdout.write(f"Staging: {created_stg} StgTipoEvento records created")

        # Upsert to SSOT
        created, updated, unchanged = self._upsert_ssot()
        self.stdout.write(
            self.style.SUCCESS(
                f"SSOT: {created} created, {updated} updated, {unchanged} unchanged"
            )
        )

    @transaction.atomic
    def _load_staging(self, tipos_data: list[dict]) -> int:
        """Load tipos to StgTipoEvento (replace all)"""
        # Clear existing staging
        StgTipoEvento.objects.all().delete()

        # Bulk create
        stg_records = [
            StgTipoEvento(
                nome=tipo["nome"],
                descricao=tipo.get("descricao", ""),
                cor=tipo.get("cor", ""),
                src=tipo.get("src", ""),
                rownum=tipo.get("rownum", 0),
            )
            for tipo in tipos_data
        ]
        StgTipoEvento.objects.bulk_create(stg_records)
        return len(stg_records)

    @transaction.atomic
    def _upsert_ssot(self) -> tuple[int, int, int]:
        """
        Upsert TipoEvento by natural key: nome (case-insensitive, trimmed)
        Returns: (created, updated, unchanged)
        """
        created_count = 0
        updated_count = 0
        unchanged_count = 0

        stg_tipos = StgTipoEvento.objects.all()

        for stg in stg_tipos:
            # Natural key: nome (normalized)
            nome = stg.nome.strip()

            # Upsert
            obj, created = TipoEvento.objects.update_or_create(
                nome__iexact=nome,
                defaults={
                    "nome": nome,
                    "descricao": stg.descricao or "",
                    "cor": stg.cor or "",
                },
            )

            if created:
                created_count += 1
            elif obj.descricao != (stg.descricao or "") or obj.cor != (stg.cor or ""):
                updated_count += 1
            else:
                unchanged_count += 1

        return created_count, updated_count, unchanged_count
