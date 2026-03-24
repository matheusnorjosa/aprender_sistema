"""
Sincroniza core_municipio_referencia a partir da API oficial do IBGE.

Comportamento:
- Default em DRY-RUN (sem writes)
- `--apply` persiste alterações
- Fonte padrão `ibge` (customizável)
- Aceita payload IBGE em `view=nivelado` e payload legado com estrutura aninhada
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false

from __future__ import annotations

import gzip
import json
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from urllib.request import Request, urlopen

from django.core.management.base import BaseCommand
from django.db import IntegrityError, transaction

from apps.core.models import MunicipioReferencia

if TYPE_CHECKING:
    from argparse import ArgumentParser


IBGE_API_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios?orderBy=nome&view=nivelado"
IBGE_CODE_RE = re.compile(r"^\d{7}$")


@dataclass(frozen=True)
class IBGEMunicipioRow:
    codigo_externo: str
    nome: str
    uf: str


def _extract_row(payload: dict[str, Any]) -> IBGEMunicipioRow | None:
    """
    Extrai (codigo, nome, uf) de dois formatos de payload:
    - Nivelado: municipio-id, municipio-nome, UF-sigla
    - Legado: id, nome, microrregiao.mesorregiao.UF.sigla
    """
    codigo = str(payload.get("municipio-id") or payload.get("id") or "").strip()
    nome = str(payload.get("municipio-nome") or payload.get("nome") or "").strip()

    uf = str(payload.get("UF-sigla") or "").strip().upper()
    if not uf:
        microrregiao = payload.get("microrregiao") or {}
        mesorregiao = microrregiao.get("mesorregiao") if isinstance(microrregiao, dict) else {}
        uf_obj = mesorregiao.get("UF") if isinstance(mesorregiao, dict) else {}
        uf = str(uf_obj.get("sigla") if isinstance(uf_obj, dict) else "").strip().upper()

    if not codigo or not nome or len(uf) != 2:
        return None
    if not IBGE_CODE_RE.fullmatch(codigo):
        return None

    return IBGEMunicipioRow(codigo_externo=codigo, nome=nome, uf=uf)


class Command(BaseCommand):
    """Sincroniza Município Referência com dados do IBGE."""

    help = "Sincroniza core_municipio_referencia com API do IBGE (default DRY-RUN)."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Persiste alterações no banco. Sem --apply roda em dry-run.",
        )
        parser.add_argument(
            "--fonte",
            type=str,
            default="ibge",
            help="Valor do campo fonte em MunicipioReferencia (default: ibge).",
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default=60,
            help="Timeout HTTP em segundos (default: 60).",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Exibe exemplos de linhas inválidas e conflitos.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        apply_changes = bool(options.get("apply", False))
        source = str(options.get("fonte", "ibge")).strip() or "ibge"
        timeout = int(options.get("timeout", 60))
        verbose = bool(options.get("verbose", False))

        rows_raw = self._fetch_rows(timeout=timeout)
        parsed_rows: list[IBGEMunicipioRow] = []
        invalid_rows = 0

        for payload in rows_raw:
            if not isinstance(payload, dict):
                invalid_rows += 1
                continue
            row = _extract_row(payload)
            if row is None:
                invalid_rows += 1
                continue
            parsed_rows.append(row)

        dedup_by_code: dict[str, IBGEMunicipioRow] = {}
        for row in parsed_rows:
            dedup_by_code[row.codigo_externo] = row

        deduped = list(dedup_by_code.values())

        created = 0
        updated = 0
        unchanged = 0
        conflicts = 0
        conflict_examples: list[str] = []

        def apply_upsert() -> None:
            nonlocal created, updated, unchanged, conflicts

            for row in deduped:
                current = MunicipioReferencia.objects.filter(fonte=source, codigo_externo=row.codigo_externo).first()
                if current:
                    changed = False
                    if current.nome != row.nome:
                        current.nome = row.nome
                        changed = True
                    if current.uf != row.uf:
                        current.uf = row.uf
                        changed = True
                    if current.ativo is False:
                        current.ativo = True
                        changed = True
                    if changed:
                        current.save(update_fields=["nome", "uf", "ativo"])
                        updated += 1
                    else:
                        unchanged += 1
                    continue

                by_name_uf = MunicipioReferencia.objects.filter(fonte=source, nome=row.nome, uf=row.uf).first()
                if by_name_uf:
                    # Mesmo município por nome/UF, mas código mudou.
                    if by_name_uf.codigo_externo == row.codigo_externo:
                        if by_name_uf.ativo is False:
                            by_name_uf.ativo = True
                            by_name_uf.save(update_fields=["ativo"])
                            updated += 1
                        else:
                            unchanged += 1
                        continue

                    try:
                        by_name_uf.codigo_externo = row.codigo_externo
                        if by_name_uf.ativo is False:
                            by_name_uf.ativo = True
                            by_name_uf.save(update_fields=["codigo_externo", "ativo"])
                        else:
                            by_name_uf.save(update_fields=["codigo_externo"])
                        updated += 1
                    except IntegrityError:
                        conflicts += 1
                        if len(conflict_examples) < 10:
                            conflict_examples.append(f"{row.nome}/{row.uf} -> {row.codigo_externo}")
                    continue

                try:
                    MunicipioReferencia.objects.create(
                        fonte=source,
                        codigo_externo=row.codigo_externo,
                        nome=row.nome,
                        uf=row.uf,
                        ativo=True,
                    )
                    created += 1
                except IntegrityError:
                    conflicts += 1
                    if len(conflict_examples) < 10:
                        conflict_examples.append(f"{row.nome}/{row.uf} -> {row.codigo_externo}")

        if apply_changes:
            with transaction.atomic():
                apply_upsert()
        else:
            created = 0
            updated = 0
            unchanged = 0
            conflicts = 0
            existing_by_code = set(
                MunicipioReferencia.objects.filter(fonte=source).values_list("codigo_externo", flat=True)
            )
            for row in deduped:
                if row.codigo_externo in existing_by_code:
                    unchanged += 1
                else:
                    created += 1

        mode = "APPLY" if apply_changes else "DRY-RUN"
        self.stdout.write(f"[{mode}] Sync Municípios IBGE")
        self.stdout.write(f"source={source} | timeout={timeout}s")
        self.stdout.write(f"total_api={len(rows_raw)}")
        self.stdout.write(f"invalid_rows={invalid_rows}")
        self.stdout.write(f"valid_rows={len(parsed_rows)}")
        self.stdout.write(f"deduped_by_code={len(deduped)}")
        self.stdout.write(f"created={created}")
        self.stdout.write(f"updated={updated}")
        self.stdout.write(f"unchanged={unchanged}")
        self.stdout.write(f"conflicts={conflicts}")
        self.stdout.write(f"total_db_source={MunicipioReferencia.objects.filter(fonte=source).count()}")

        if verbose and conflict_examples:
            self.stdout.write("conflict_examples:")
            for item in conflict_examples:
                self.stdout.write(f"  - {item}")

    def _fetch_rows(self, *, timeout: int) -> list[Any]:
        req = Request(
            IBGE_API_URL,
            headers={
                "Accept-Encoding": "gzip",
                "User-Agent": "aprender-sistema/1.0",
            },
        )
        with urlopen(req, timeout=timeout) as response:
            raw = response.read()
            if (response.headers.get("Content-Encoding") or "").lower() == "gzip":
                raw = gzip.decompress(raw)

        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, list):
            raise ValueError("Payload inesperado da API do IBGE: esperado list.")
        return payload
