"""
ETL de Municípios de Referência (fonte externa)

Pipeline robusto:
1) Carrega dados para staging (StgMunicipioReferencia)
2) Faz upsert em core.MunicipioReferencia
3) Gera relatório ETL padronizado
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false, reportReturnType=false, reportGeneralTypeIssues=false

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandParser
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.core.models import Municipio, MunicipioReferencia
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
    help = "ETL de municípios de referência (fonte externa) com staging + upsert"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--file",
            type=str,
            required=True,
            help="Caminho do arquivo JSON/CSV com municípios",
        )
        parser.add_argument(
            "--source",
            type=str,
            default="sistemasaprender",
            help="Identificador da fonte externa (default: sistemasaprender)",
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

    def handle(self, *args: Any, **options: Any) -> None:
        self.file_path = Path(options["file"])
        self.source = options["source"].strip() or "sistemasaprender"
        self.dry_run = bool(options["dry_run"])
        self.stage_only = bool(options["stage_only"])
        self.truncate_stage = bool(options["truncate_stage"])

        if not self.file_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {self.file_path}")

        start = timezone.now()
        errors: list[ETLError] = []
        warnings: list[str] = []

        self.stdout.write(f"🚀 ETL Municípios Referência (source={self.source}, dry_run={self.dry_run})")
        self.stdout.write(f"   File: {self.file_path}")

        records = self._load_records(errors, warnings)
        total_records = len(records)

        if total_records == 0:
            self.stdout.write(self.style.WARNING("Nenhum registro válido encontrado."))
            return

        with transaction.atomic():
            if self.truncate_stage:
                StgMunicipioReferencia.objects.filter(fonte=self.source).delete()

            created_stage = self._load_staging(records)

            created_core = 0
            updated_core = 0
            skipped_core = 0
            matched_core = 0

            if not self.stage_only:
                created_core, updated_core, skipped_core, matched_core = self._upsert_core(errors, warnings)

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
            command="etl_sync_municipios_referencia",
            start_time=start,
            end_time=end,
            status=status,
            metrics=metrics,
            filters={
                "source": self.source,
                "file": str(self.file_path),
                "stage_only": str(self.stage_only),
            },
            errors=errors,
            warnings=warnings,
        )

        report_path = Path(settings.BASE_DIR) / "out_etl" / "etl_municipios_referencia_report.json"
        report.save_to_file(str(report_path))

        self.stdout.write(self.style.SUCCESS("\n✅ ETL concluído!"))
        self.stdout.write(f"   Staging: {created_stage} carregados")
        if not self.stage_only:
            self.stdout.write(f"   Core: {created_core} criados, {updated_core} atualizados, {skipped_core} ignorados")
            self.stdout.write(f"   Match com Municipios (core): {matched_core} de {total_records}")
        self.stdout.write(f"   Relatório: {report_path}")

    def _load_records(self, errors: list[ETLError], warnings: list[str]) -> list[dict[str, Any]]:
        """Carrega e normaliza registros do arquivo."""
        ext = self.file_path.suffix.lower()
        raw_rows: list[dict[str, Any]] = []

        try:
            if ext == ".json":
                with self.file_path.open("r", encoding="utf-8") as f:
                    payload = json.load(f)
                if isinstance(payload, dict):
                    raw_rows = payload.get("municipios") or payload.get("dados") or []
                elif isinstance(payload, list):
                    raw_rows = payload
            elif ext == ".csv":
                with self.file_path.open("r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    raw_rows = list(reader)
            else:
                raise ValueError("Formato não suportado (use JSON ou CSV)")
        except Exception as exc:
            errors.append(
                ETLError(error_type=exc.__class__.__name__, message=str(exc), timestamp=timezone.now().isoformat())
            )
            return []

        seen: set[tuple[str, str, str]] = set()
        records: list[dict[str, Any]] = []

        for idx, row in enumerate(raw_rows, start=1):
            nome_raw = (
                row.get("nome_completo")
                or row.get("municipio")
                or row.get("nome")
                or row.get("Município")
                or ""
            )
            uf_raw = row.get("uf") or row.get("UF")
            codigo_raw = row.get("codigo_ibge") or row.get("codigo") or row.get("id") or ""

            nome, uf = _split_nome_uf(str(nome_raw))
            if uf_raw and not uf:
                uf = str(uf_raw).strip().upper()

            nome = str(nome).strip()
            if not nome or not uf:
                warnings.append(f"Linha {idx}: municipio/UF ausente")
                continue

            codigo_externo = str(codigo_raw).strip()
            if not codigo_externo:
                warnings.append(f"Linha {idx}: codigo_externo ausente")

            key = (norm_text(nome), uf.upper(), codigo_externo)
            if key in seen:
                continue
            seen.add(key)

            records.append(
                {
                    "codigo_externo": codigo_externo,
                    "nome": nome,
                    "uf": uf.upper(),
                    "fonte": self.source,
                    "src": self.file_path.name,
                    "rownum": idx,
                }
            )

        return records

    def _load_staging(self, records: list[dict[str, Any]]) -> int:
        """Carrega registros no staging."""
        objs = [StgMunicipioReferencia(**r) for r in records]
        StgMunicipioReferencia.objects.bulk_create(objs, batch_size=1000)
        return len(objs)

    def _upsert_core(
        self, errors: list[ETLError], warnings: list[str]
    ) -> tuple[int, int, int, int]:
        """Upsert em core.MunicipioReferencia."""
        created = 0
        updated = 0
        skipped = 0

        stg_qs = StgMunicipioReferencia.objects.filter(fonte=self.source)
        core_keys = {(norm_text(m.nome), m.uf.upper()) for m in Municipio.objects.all()}
        matched_core = 0

        for stg in stg_qs:
            if (norm_text(stg.nome), stg.uf.upper()) in core_keys:
                matched_core += 1

            if not stg.codigo_externo:
                skipped += 1
                continue

            try:
                obj, was_created = MunicipioReferencia.objects.update_or_create(
                    fonte=stg.fonte,
                    codigo_externo=stg.codigo_externo,
                    defaults={
                        "nome": stg.nome,
                        "uf": stg.uf.upper(),
                        "ativo": True,
                    },
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
            except IntegrityError as exc:
                skipped += 1
                errors.append(
                    ETLError(
                        error_type="IntegrityError",
                        message=f"{stg.nome}-{stg.uf} ({stg.codigo_externo}): {exc}",
                        timestamp=timezone.now().isoformat(),
                    )
                )
            except Exception as exc:
                skipped += 1
                errors.append(
                    ETLError(
                        error_type=exc.__class__.__name__,
                        message=f"{stg.nome}-{stg.uf} ({stg.codigo_externo}): {exc}",
                        timestamp=timezone.now().isoformat(),
                    )
                )

        missing_core = len(stg_qs) - matched_core
        if missing_core > 0:
            warnings.append(f"{missing_core} municípios não encontrados na base core (Municipio)")

        return created, updated, skipped, matched_core
