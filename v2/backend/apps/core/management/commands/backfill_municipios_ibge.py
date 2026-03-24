"""
Backfill de ibge_code em core_municipio a partir de core_municipio_referencia.

Regras:
- Só avalia municípios sem ibge_code (null ou string vazia)
- Match por (UF + nome normalizado)
- Aceita apenas códigos de 7 dígitos na referência
- Só aplica update quando há match único e sem conflito de unicidade
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from typing import TYPE_CHECKING, Any

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from apps.core.models import Municipio, MunicipioReferencia

if TYPE_CHECKING:
    from argparse import ArgumentParser


IBGE_CODE_RE = re.compile(r"^\d{7}$")


def _normalize_name(value: str) -> str:
    """Normaliza nome para comparação determinística sem acentos/case."""
    base = unicodedata.normalize("NFKD", value.strip())
    without_accents = "".join(char for char in base if not unicodedata.combining(char))
    normalized_spaces = " ".join(without_accents.split())
    return normalized_spaces.casefold()


class Command(BaseCommand):
    """Backfill de ibge_code usando Município Referência (fonte configurável)."""

    help = "Preenche core_municipio.ibge_code a partir de core_municipio_referencia (match por nome+UF)."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Persiste updates no banco. Sem --apply, roda em dry-run.",
        )
        parser.add_argument(
            "--fonte",
            type=str,
            default="ibge",
            help="Fonte da tabela de referência (default: ibge).",
        )
        parser.add_argument(
            "--uf",
            type=str,
            help="Filtra municípios de uma UF específica (ex: CE).",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Limita quantidade de municípios candidatos (útil para teste controlado).",
        )
        parser.add_argument(
            "--include-inactive-ref",
            action="store_true",
            help="Inclui referências inativas no match (default: apenas ativo=True).",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Exibe exemplos de ambiguidades, conflitos e sem match.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        apply_changes = bool(options.get("apply", False))
        fonte = str(options.get("fonte", "ibge")).strip()
        uf_filter = str(options.get("uf") or "").strip().upper()
        limit = options.get("limit")
        include_inactive_ref = bool(options.get("include_inactive_ref", False))
        verbose = bool(options.get("verbose", False))

        missing_ibge_qs = Municipio.objects.filter(Q(ibge_code__isnull=True) | Q(ibge_code="")).order_by("uf", "nome")
        if uf_filter:
            missing_ibge_qs = missing_ibge_qs.filter(uf__iexact=uf_filter)
        if limit:
            missing_ibge_qs = missing_ibge_qs[: int(limit)]

        municipios_alvo = list(missing_ibge_qs)

        referencia_qs = MunicipioReferencia.objects.filter(fonte=fonte)
        if not include_inactive_ref:
            referencia_qs = referencia_qs.filter(ativo=True)
        referencias = list(referencia_qs.only("nome", "uf", "codigo_externo"))

        ref_codes_by_key: dict[tuple[str, str], set[str]] = defaultdict(set)
        invalid_ref_code_count = 0
        for ref in referencias:
            code = (ref.codigo_externo or "").strip()
            if not IBGE_CODE_RE.fullmatch(code):
                invalid_ref_code_count += 1
                continue
            key = (ref.uf.strip().upper(), _normalize_name(ref.nome))
            ref_codes_by_key[key].add(code)

        existing_codes: dict[str, set[int]] = defaultdict(set)
        for municipio_id, ibge_code in Municipio.objects.exclude(
            Q(ibge_code__isnull=True) | Q(ibge_code="")
        ).values_list(
            "id",
            "ibge_code",
        ):
            if ibge_code:
                existing_codes[ibge_code].add(int(municipio_id))

        updates: list[tuple[Municipio, str]] = []
        ambiguous_examples: list[str] = []
        no_match_examples: list[str] = []
        conflict_examples: list[str] = []

        matched_unique = 0
        ambiguous = 0
        no_match = 0
        conflicts = 0

        for municipio in municipios_alvo:
            key = (municipio.uf.strip().upper(), _normalize_name(municipio.nome))
            candidate_codes = sorted(ref_codes_by_key.get(key, set()))

            if not candidate_codes:
                no_match += 1
                if len(no_match_examples) < 10:
                    no_match_examples.append(f"{municipio.nome}/{municipio.uf}")
                continue

            if len(candidate_codes) > 1:
                ambiguous += 1
                if len(ambiguous_examples) < 10:
                    ambiguous_examples.append(f"{municipio.nome}/{municipio.uf} -> {', '.join(candidate_codes)}")
                continue

            candidate_code = candidate_codes[0]
            owners = existing_codes.get(candidate_code, set())
            if owners and (municipio.id not in owners):
                conflicts += 1
                if len(conflict_examples) < 10:
                    conflict_examples.append(f"{municipio.nome}/{municipio.uf} -> {candidate_code}")
                continue

            matched_unique += 1
            updates.append((municipio, candidate_code))

        if apply_changes and updates:
            with transaction.atomic():
                for municipio, code in updates:
                    municipio.ibge_code = code
                    municipio.save(update_fields=["ibge_code"])
            updated = len(updates)
        else:
            updated = 0

        mode = "APPLY" if apply_changes else "DRY-RUN"
        self.stdout.write(f"[{mode}] Backfill de IBGE em Municípios")
        self.stdout.write(f"fonte={fonte} | uf={uf_filter or 'ALL'}")
        self.stdout.write(f"referencias_lidas={len(referencias)}")
        self.stdout.write(f"referencias_codigo_invalido={invalid_ref_code_count}")
        self.stdout.write(f"municipios_alvo_sem_ibge={len(municipios_alvo)}")
        self.stdout.write(f"match_unico={matched_unique}")
        self.stdout.write(f"sem_match={no_match}")
        self.stdout.write(f"ambiguos={ambiguous}")
        self.stdout.write(f"conflitos_codigo_existente={conflicts}")
        self.stdout.write(f"would_update={len(updates)}")
        self.stdout.write(self.style.SUCCESS(f"updated={updated}"))

        if verbose:
            if no_match_examples:
                self.stdout.write("exemplos_sem_match:")
                for item in no_match_examples:
                    self.stdout.write(f"  - {item}")
            if ambiguous_examples:
                self.stdout.write("exemplos_ambiguos:")
                for item in ambiguous_examples:
                    self.stdout.write(f"  - {item}")
            if conflict_examples:
                self.stdout.write("exemplos_conflitos:")
                for item in conflict_examples:
                    self.stdout.write(f"  - {item}")
