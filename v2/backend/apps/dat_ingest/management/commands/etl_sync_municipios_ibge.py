"""
ETL de Municípios (IBGE CSV) -> core.Municipio

Pipeline robusto:
1) Carrega dados para staging (StgMunicipioReferencia) com fonte 'ibge'
2) Faz upsert seguro em core.Municipio respeitando unicidade de nome
3) Gera relatório ETL padronizado
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false, reportReturnType=false, reportGeneralTypeIssues=false

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction
from django.utils import timezone

from apps.core.models import Municipio
from apps.core.schemas.etl_report import ETLError, ETLMetrics, ETLReport
from apps.core.services.normalize import norm_text
from apps.dat_ingest.models import StgMunicipioReferencia


def _split_nome_uf(raw: str) -> tuple[str, str | None]:
    """Separa 'Cidade - UF' ou 'Cidade (UF)' em (nome, uf)."""
    if not raw:
        return ("", None)

    txt = str(raw).strip()
    txt = txt.replace("–", "-").replace("—", "-").replace("/", "-")
    txt = re.sub(r"\s+", " ", txt)

    m = re.match(r"^(?P<nome>.+?)\s*-\s*(?P<uf>[A-Za-z]{2})$", txt)
    if not m:
        m = re.match(r"^(?P<nome>.+?)\s*\((?P<uf>[A-Za-z]{2})\)\s*$", txt)

    if m:
        return (m.group("nome").strip(), m.group("uf").upper())

    return (txt, None)


class Command(BaseCommand):
    help = "ETL de municípios (IBGE CSV) com staging + upsert seguro em core.Municipio"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--file",
            type=str,
            required=True,
            help="Caminho do CSV do IBGE (separador ';')",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simula execução sem writes no banco",
        )
        parser.add_argument(
            "--stage-only",
            action="store_true",
            help="Carrega apenas staging (sem upsert em core)",
        )
        parser.add_argument(
            "--truncate-stage",
            action="store_true",
            help="Limpa staging da fonte antes de carregar",
        )
        parser.add_argument(
            "--activate-default",
            action="store_true",
            help="Cria municípios novos como ativo=True (default: False)",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        self.file_path = Path(options["file"])
        self.dry_run = bool(options["dry_run"])
        self.stage_only = bool(options["stage_only"])
        self.truncate_stage = bool(options["truncate_stage"])
        self.activate_default = bool(options["activate_default"])

        if not self.file_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {self.file_path}")

        start = timezone.now()
        errors: list[ETLError] = []
        warnings: list[str] = []

        self.stdout.write(f"🚀 ETL Municípios IBGE (dry_run={self.dry_run})")
        self.stdout.write(f"   File: {self.file_path}")

        records = self._load_records(errors, warnings)
        total_records = len(records)

        if total_records == 0:
            self.stdout.write(self.style.WARNING("Nenhum registro válido encontrado."))
            return

        with transaction.atomic():
            if self.truncate_stage:
                StgMunicipioReferencia.objects.filter(fonte="ibge").delete()

            created_stage = self._load_staging(records)

            created_core = 0
            updated_core = 0
            skipped_core = 0

            if not self.stage_only:
                created_core, updated_core, skipped_core = self._upsert_core(errors, warnings)

            if self.dry_run:
                self.stdout.write("   [DRY-RUN] Rollback transaction")
                transaction.set_rollback(True)

        end = timezone.now()

        metrics = ETLMetrics(
            total_processed=total_records,
            created=created_core,
            updated=updated_core,
            skipped=skipped_core,
            errors=len(errors),
        )
        status = "success" if not errors else "partial_success"
        report = ETLReport(
            command="etl_sync_municipios_ibge",
            start_time=start,
            end_time=end,
            status=status,
            metrics=metrics,
            filters={
                "file": str(self.file_path),
                "stage_only": str(self.stage_only),
                "activate_default": str(self.activate_default),
            },
            errors=errors,
            warnings=warnings,
        )

        report_path = Path(settings.BASE_DIR) / "out_etl" / "etl_municipios_ibge_report.json"
        report.save_to_file(str(report_path))

        self.stdout.write(self.style.SUCCESS("\n✅ ETL concluído!"))
        self.stdout.write(f"   Staging: {created_stage} carregados")
        if not self.stage_only:
            self.stdout.write(f"   Core: {created_core} criados, {updated_core} atualizados, {skipped_core} ignorados")
        self.stdout.write(f"   Relatório: {report_path}")

    def _load_records(self, errors: list[ETLError], warnings: list[str]) -> list[dict[str, Any]]:
        """Carrega e normaliza registros do CSV IBGE."""
        raw_rows: list[list[str]] = []

        try:
            with self.file_path.open("r", encoding="latin-1") as f:
                reader = csv.reader(f, delimiter=";")
                _ = next(reader, None)  # header
                raw_rows = list(reader)
        except Exception as exc:
            errors.append(
                ETLError(error_type=exc.__class__.__name__, message=str(exc), timestamp=timezone.now().isoformat())
            )
            return []

        seen: set[tuple[str, str]] = set()
        records: list[dict[str, Any]] = []

        for idx, row in enumerate(raw_rows, start=2):  # start=2 por conta do header
            uf = (row[0] if len(row) > 0 else "").strip().upper()
            nome = (row[1] if len(row) > 1 else "").strip()
            alt = (row[2] if len(row) > 2 else "").strip()

            if (not nome or not uf) and alt:
                nome_alt, uf_alt = _split_nome_uf(alt)
                nome = nome or nome_alt
                uf = uf or (uf_alt or "")

            if not nome or not uf:
                warnings.append(f"Linha {idx}: municipio/UF ausente")
                continue

            key = (norm_text(nome), uf)
            if key in seen:
                continue
            seen.add(key)

            records.append(
                {
                    "codigo_externo": "",
                    "nome": nome,
                    "uf": uf,
                    "fonte": "ibge",
                    "src": self.file_path.name,
                    "rownum": idx,
                }
            )

        return records

    def _load_staging(self, records: list[dict[str, Any]]) -> int:
        objs = [StgMunicipioReferencia(**r) for r in records]
        StgMunicipioReferencia.objects.bulk_create(objs, batch_size=1000)
        return len(objs)

    def _upsert_core(self, errors: list[ETLError], warnings: list[str]) -> tuple[int, int, int]:
        """Upsert seguro em core.Municipio respeitando unicidade de nome."""
        created = 0
        updated = 0
        skipped = 0
        existing = {(norm_text(m.nome), m.uf.upper()) for m in Municipio.objects.all()}
        stg_qs = StgMunicipioReferencia.objects.filter(fonte="ibge")

        for stg in stg_qs:
            key = (norm_text(stg.nome), stg.uf.upper())
            if key in existing:
                # Não altera ativos existentes
                skipped += 1
                continue

            if not self.dry_run:
                obj = Municipio.objects.create(
                    nome=stg.nome,
                    uf=stg.uf,
                    ativo=self.activate_default,
                )
                existing.add(key)

            created += 1

        return created, updated, skipped
