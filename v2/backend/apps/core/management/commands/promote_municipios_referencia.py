"""
Promote municipios from core_municipio_referencia into core_municipio.

Goal:
- make every reference municipio available to platform dropdowns
- keep the operation idempotent
- avoid duplicating rows when an equivalent municipio already exists
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from typing import TYPE_CHECKING, Any

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.models import Municipio, MunicipioReferencia
from apps.core.services.options_cache import invalidate_municipios_options_cache

if TYPE_CHECKING:
    from argparse import ArgumentParser


IBGE_CODE_RE = re.compile(r"^\d{7}$")


def _normalize_name(value: str) -> str:
    """Normalize names for deterministic matching without accents/case."""
    base = unicodedata.normalize("NFKD", value.strip())
    without_accents = "".join(char for char in base if not unicodedata.combining(char))
    normalized_spaces = " ".join(without_accents.split())
    return normalized_spaces.casefold()


class Command(BaseCommand):
    help = "Promove municipios da tabela de referencia para core_municipio."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Persiste alteracoes no banco. Sem --apply, roda em dry-run.",
        )
        parser.add_argument(
            "--fonte",
            type=str,
            default="ibge",
            help="Fonte da tabela de referencia (default: ibge).",
        )
        parser.add_argument(
            "--uf",
            type=str,
            help="Filtra municipios de uma UF especifica (ex: CE).",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Limita quantidade de referencias avaliadas (util para teste controlado).",
        )
        parser.add_argument(
            "--include-inactive-ref",
            action="store_true",
            help="Inclui referencias inativas. Default: somente ativo=True.",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Exibe exemplos de conflitos detectados.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        apply_changes = bool(options.get("apply", False))
        fonte = str(options.get("fonte", "ibge")).strip()
        uf_filter = str(options.get("uf") or "").strip().upper()
        limit = options.get("limit")
        include_inactive_ref = bool(options.get("include_inactive_ref", False))
        verbose = bool(options.get("verbose", False))

        referencia_base_qs = MunicipioReferencia.objects.filter(fonte=fonte).order_by("uf", "nome", "codigo_externo")
        if uf_filter:
            referencia_base_qs = referencia_base_qs.filter(uf__iexact=uf_filter)

        ignored_inactive_refs = 0
        if not include_inactive_ref:
            ignored_inactive_refs = referencia_base_qs.filter(ativo=False).count()

        referencia_qs = referencia_base_qs
        if not include_inactive_ref:
            referencia_qs = referencia_qs.filter(ativo=True)
        if limit:
            referencia_qs = referencia_qs[: int(limit)]

        referencias = list(referencia_qs.only("nome", "uf", "codigo_externo", "ativo"))
        municipios_existentes = list(Municipio.objects.all().only("id", "nome", "uf", "ibge_code", "ativo"))

        existing_by_code: dict[str, Municipio] = {}
        existing_by_key: dict[tuple[str, str], list[Municipio]] = defaultdict(list)
        for municipio in municipios_existentes:
            if municipio.ibge_code:
                existing_by_code[municipio.ibge_code] = municipio
            existing_by_key[(municipio.uf.strip().upper(), _normalize_name(municipio.nome))].append(municipio)

        to_create: list[Municipio] = []
        to_update: list[tuple[Municipio, list[str]]] = []

        invalid_ref_code_count = 0
        would_create = 0
        would_update = 0
        unchanged = 0
        code_owned_by_other = 0
        ambiguous_existing = 0
        mismatched_existing_code = 0

        code_conflict_examples: list[str] = []
        ambiguous_examples: list[str] = []
        mismatched_examples: list[str] = []

        for ref in referencias:
            code = (ref.codigo_externo or "").strip()
            if not IBGE_CODE_RE.fullmatch(code):
                invalid_ref_code_count += 1
                continue

            ref_name = ref.nome.strip()
            ref_uf = ref.uf.strip().upper()
            ref_key = (ref_uf, _normalize_name(ref_name))
            target = existing_by_code.get(code)

            if target is not None:
                target_key = (target.uf.strip().upper(), _normalize_name(target.nome))
                if target_key != ref_key:
                    code_owned_by_other += 1
                    if len(code_conflict_examples) < 10:
                        code_conflict_examples.append(
                            f"{ref_name}/{ref_uf} -> {code} (owner={target.nome}/{target.uf})"
                        )
                    continue
            else:
                candidates = existing_by_key.get(ref_key, [])
                if len(candidates) > 1:
                    ambiguous_existing += 1
                    if len(ambiguous_examples) < 10:
                        names = ", ".join(f"{item.nome}/{item.uf}" for item in candidates[:3])
                        ambiguous_examples.append(f"{ref_name}/{ref_uf} -> {names}")
                    continue
                if len(candidates) == 1:
                    target = candidates[0]
                    if target.ibge_code and target.ibge_code != code:
                        mismatched_existing_code += 1
                        if len(mismatched_examples) < 10:
                            mismatched_examples.append(f"{ref_name}/{ref_uf} -> ref={code} existing={target.ibge_code}")
                        continue

            if target is None:
                municipio = Municipio(
                    nome=ref_name,
                    uf=ref_uf,
                    ibge_code=code,
                    ativo=bool(ref.ativo),
                )
                to_create.append(municipio)
                would_create += 1
                existing_by_code[code] = municipio
                existing_by_key[ref_key].append(municipio)
                continue

            changed_fields: list[str] = []
            if target.ibge_code != code:
                target.ibge_code = code
                changed_fields.append("ibge_code")
            if target.ativo != bool(ref.ativo):
                target.ativo = bool(ref.ativo)
                changed_fields.append("ativo")

            if changed_fields:
                to_update.append((target, changed_fields))
                would_update += 1
            else:
                unchanged += 1

        created = 0
        updated = 0
        cache_invalidated = False

        if apply_changes and (to_create or to_update):
            with transaction.atomic():
                if to_create:
                    Municipio.objects.bulk_create(to_create, batch_size=1000)
                    created = len(to_create)
                if to_update:
                    for municipio, fields in to_update:
                        municipio.save(update_fields=fields)
                    updated = len(to_update)

            invalidate_municipios_options_cache()
            cache_invalidated = True

        mode = "APPLY" if apply_changes else "DRY-RUN"
        self.stdout.write(f"[{mode}] Promote Municipios Referencia")
        self.stdout.write(f"fonte={fonte} | uf={uf_filter or 'ALL'}")
        self.stdout.write(f"referencias_lidas={len(referencias)}")
        self.stdout.write(f"referencias_codigo_invalido={invalid_ref_code_count}")
        self.stdout.write(f"ignored_inactive_refs={ignored_inactive_refs}")
        self.stdout.write(f"would_create={would_create}")
        self.stdout.write(f"would_update={would_update}")
        self.stdout.write(f"unchanged={unchanged}")
        self.stdout.write(f"conflicts_code_owned_by_other={code_owned_by_other}")
        self.stdout.write(f"conflicts_ambiguous_existing={ambiguous_existing}")
        self.stdout.write(f"conflicts_mismatched_existing_code={mismatched_existing_code}")
        self.stdout.write(self.style.SUCCESS(f"created={created}"))
        self.stdout.write(self.style.SUCCESS(f"updated={updated}"))
        self.stdout.write(f"cache_invalidated={1 if cache_invalidated else 0}")
        self.stdout.write(f"total_db_target={Municipio.objects.count()}")

        if verbose:
            if code_conflict_examples:
                self.stdout.write("exemplos_code_owned_by_other:")
                for item in code_conflict_examples:
                    self.stdout.write(f"  - {item}")
            if ambiguous_examples:
                self.stdout.write("exemplos_ambiguous_existing:")
                for item in ambiguous_examples:
                    self.stdout.write(f"  - {item}")
            if mismatched_examples:
                self.stdout.write("exemplos_mismatched_existing_code:")
                for item in mismatched_examples:
                    self.stdout.write(f"  - {item}")
