"""
Importer dedicado do export-contract (skeleton seguro).

Princípios de segurança:
- **dry-run por padrão** (`apply=False`): só classifica, nunca escreve.
- **`apply=True` exige allowlist** (`allow=(...)`); sem allowlist → `apply_blocked`, nada escrito.
- **modo `create-only`**: na escrita, só insere `would_create`; nunca faz update.
- **never-overwrite de campos protegidos**: se um registro existe e diverge num campo protegido
  (`Solicitacao.status`, `Formacao.data_formacao`, `Acompanhamento.data_acompanhamento/realizado`),
  classifica como `protected_diff` e deixa para decisão humana (nunca sobrescreve).

Primeira fatia implementada (master, baixo risco): `dat_area`, `municipio`, `projeto_geral`.
Demais entidades → `not_implemented` (contagem reportada, sem processamento).

NÃO importa dados reais por padrão. Sem PII no relatório (só counts/nomes de entidade).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false

from __future__ import annotations

import csv
import json
import os
import re
import unicodedata
from typing import Any

from django.db import transaction

from apps.core.models import DATArea, Municipio, ProjetoGeral
from apps.core.services.export_contract_projeto_resolver import build_projeto_index, resolve_projeto_export

# Campos protegidos por entidade — NUNCA sobrescrever em update (decisão humana).
PROTECTED_FIELDS: dict[str, set[str]] = {
    "solicitacao": {"status"},
    "formacao": {"data_formacao"},
    "acompanhamento": {"data_acompanhamento", "realizado"},
}

# Ordem canônica (master → operacional). IMPLEMENTED = fatia atual.
ENTITY_ORDER = [
    "municipio",
    "projeto_geral",
    "projeto",
    "produto",
    "colecao",
    "usuario",
    "gerencia",
    "equipe_gerencia",
    "tipo_evento",
    "dat_area",
    "dat_coordenador",
    "solicitacao",
    "participation",
    "availability_block",
    "deslocamento",
    "dat_registro",
    "dat_cadastro",
    "dat_acao",
    "dat_compra",
    "plano_formacao",
    "formacao",
    "acompanhamento",
    "prova",
]
IMPLEMENTED = {"dat_area", "municipio", "projeto_geral"}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", (s or "").strip())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).upper()


def _cmp(v: Any) -> str:
    """Forma comparável canônica (bool/None/str) para detectar diferença de campo."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None:
        return ""
    return str(v).strip().casefold()


def _to_bool(v: Any) -> bool:
    return str(v).strip().casefold() in {"true", "1", "yes", "sim", "t"}


def diff_and_classify(
    existing: dict[str, Any] | None, export: dict[str, Any], protected: set[str]
) -> tuple[str, list[str]]:
    """
    Classifica um registro comparando o estado existente (ou None) com o do export.

    Returns (status, campos):
      - would_create   : não existe.
      - would_skip_same: existe e idêntico nos campos comparados.
      - protected_diff : existe e diverge em campo protegido (NUNCA sobrescrever).
      - would_update   : existe e diverge só em campos não-protegidos.
    """
    if existing is None:
        return "would_create", []
    diffs = [k for k in export if _cmp(existing.get(k)) != _cmp(export.get(k))]
    if not diffs:
        return "would_skip_same", []
    prot = sorted(k for k in diffs if k in protected)
    if prot:
        return "protected_diff", prot
    return "would_update", sorted(diffs)


class ExportContractImporter:
    """Importer dry-run-first do export-contract. Veja docstring do módulo."""

    def __init__(
        self, path: str, *, mode: str = "create-only", apply: bool = False, allow: tuple[str, ...] = ()
    ) -> None:
        self.path = path
        self.mode = mode
        self.apply = apply
        self.allow = tuple(allow)
        self._pidx = None

    # ── resolver de Projeto (delegação ao módulo mergeado na #1372) ──
    def resolve_projeto(self, raw_name: str) -> int | None:
        if self._pidx is None:
            self._pidx = build_projeto_index()
        res = resolve_projeto_export(raw_name, index=self._pidx)
        return res.projeto.id if res.status == "matched" and res.projeto else None

    def _load(self, name: str) -> list[dict[str, str]]:
        fp = os.path.join(self.path, f"{name}.csv")
        if not os.path.exists(fp):
            return []
        with open(fp, encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def _read_manifest(self) -> dict[str, Any]:
        fp = os.path.join(self.path, "manifest.json")
        if not os.path.exists(fp):
            return {}
        with open(fp, encoding="utf-8") as f:
            return json.load(f)

    # ── handlers da fatia implementada ──
    def _classify_master(self, name: str) -> dict[str, int]:
        rows = self._load(name)
        tally = {k: 0 for k in ("would_create", "would_update", "would_skip_same", "protected_diff", "would_reject")}
        protected = PROTECTED_FIELDS.get(name, set())

        if name == "dat_area":
            # DATArea não tem campo comparável vindo do export (export traz só nome/descricao;
            # 'descricao' não existe no model). → existência decide create vs skip.
            idx = {_norm(n) for n in DATArea.objects.values_list("nome", flat=True)}
            for r in rows:
                nome = (r.get("nome") or "").strip()
                if not nome:
                    tally["would_reject"] += 1
                    continue
                existing = {} if _norm(nome) in idx else None
                st, _ = diff_and_classify(existing, {}, protected)
                tally[st] += 1

        elif name == "municipio":
            idx = {
                (_norm(n), (u or "").upper()): {"ativo": a}
                for n, u, a in Municipio.objects.values_list("nome", "uf", "ativo")
            }
            for r in rows:
                nome = (r.get("nome") or "").strip()
                if not nome:
                    tally["would_reject"] += 1
                    continue
                key = (_norm(nome), (r.get("uf") or "").upper())
                st, _ = diff_and_classify(idx.get(key), {"ativo": _to_bool(r.get("ativo"))}, protected)
                tally[st] += 1

        elif name == "projeto_geral":
            idx = {_norm(n): {"usa_avaliar": a} for n, a in ProjetoGeral.objects.values_list("nome", "usa_avaliar")}
            for r in rows:
                nome = (r.get("nome") or "").strip()
                if not nome:
                    tally["would_reject"] += 1
                    continue
                st, _ = diff_and_classify(
                    idx.get(_norm(nome)), {"usa_avaliar": _to_bool(r.get("usa_avaliar"))}, protected
                )
                tally[st] += 1

        tally["export_rows"] = len(rows)
        return tally

    def run(self) -> dict[str, Any]:
        manifest = self._read_manifest()
        apply_blocked = bool(self.apply) and not self.allow

        por_entidade: dict[str, Any] = {}
        for name in ENTITY_ORDER:
            fp = os.path.join(self.path, f"{name}.csv")
            if not os.path.exists(fp):
                continue
            if name in IMPLEMENTED:
                por_entidade[name] = self._classify_master(name)
            else:
                por_entidade[name] = {"status": "not_implemented", "export_rows": len(self._load(name))}

        # ── escrita (create-only) — só se apply + allowlist; NÃO exercida no skeleton ──
        applied: dict[str, int] = {}
        if self.apply and self.allow and self.mode == "create-only":
            applied = self._apply_create_only()

        return {
            "phase": "EXPORT_CONTRACT_IMPORTER",
            "mode": self.mode,
            "apply": self.apply,
            "apply_blocked": apply_blocked,
            "allow": list(self.allow),
            "manifest": manifest,
            "por_entidade": por_entidade,
            "applied": applied,
            "protected_fields": {k: sorted(v) for k, v in PROTECTED_FIELDS.items()},
        }

    def _apply_create_only(self) -> dict[str, int]:
        """Cria SOMENTE would_create das entidades em allow (create-only). Transacional."""
        applied: dict[str, int] = {}
        with transaction.atomic():
            for name in self.allow:
                if name not in IMPLEMENTED:
                    continue
                created = 0
                for r in self._load(name):
                    nome = (r.get("nome") or "").strip()
                    if not nome:
                        continue
                    if name == "dat_area" and not DATArea.objects.filter(nome__iexact=nome).exists():
                        DATArea.objects.create(nome=nome)
                        created += 1
                    elif name == "municipio":
                        uf = (r.get("uf") or "").upper()
                        if not Municipio.objects.filter(nome__iexact=nome, uf=uf).exists():
                            Municipio.objects.create(nome=nome, uf=uf, ativo=_to_bool(r.get("ativo")))
                            created += 1
                    elif name == "projeto_geral" and not ProjetoGeral.objects.filter(nome__iexact=nome).exists():
                        ProjetoGeral.objects.create(nome=nome, usa_avaliar=_to_bool(r.get("usa_avaliar")))
                        created += 1
                applied[name] = created
        return applied
