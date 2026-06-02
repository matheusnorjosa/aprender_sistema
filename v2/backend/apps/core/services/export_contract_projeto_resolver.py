"""
Resolver de Projeto para o import do export-contract (Gap C).

O DB (catálogo de 123 projetos) é o SSOT. Este resolver mapeia o NOME de projeto que
vem do export-contract para um `Projeto` existente, fechando os resíduos de forma:

1. Regras determinísticas (aplicadas a ambos os lados via chave canônica):
   - `&` <-> `E`
   - remover hífen separador (`SUPERATIVAR - MATEMATICA 4` -> `SUPERATIVAR MATEMATICA 4`)
   - remover prefixo `PROJETO `
   - normalizar vírgula (`LER, OUVIR` <-> `LER OUVIR`)
2. Aliases ESCOPADOS por família (nunca regra global `Português -> Língua Portuguesa`):
   - `Superativar (Língua )Português N` -> `Superativar Linguagens N` (N in 3,4,5)
   - `ACerta Brasil Português` -> `ACerta Brasil Língua Portuguesa`
   - `Brincando e Aprendendo Professor` -> `Brincando e Aprendendo`

Ambiguidade (a chave canônica casa >1 projeto distinto) **falha explicitamente**
(`status="ambiguous"`), nunca escolhe um alvo no chute.

NÃO importa dados; só resolve nomes. Não tem efeito colateral.
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field

from apps.core.models import Projeto

# ── Aliases escopados (chave = nome NORMALIZADO de origem; valor = nome NORMALIZADO alvo) ──
# Apenas famílias confirmadas por decisão humana. NÃO é regra global.
_SCOPED_ALIASES: dict[str, str] = {
    # Superativar: "Português"/"Língua Portuguesa" N -> "Linguagens" N (rename de catálogo já aplicado)
    "SUPERATIVAR PORTUGUES 3": "SUPERATIVAR LINGUAGENS 3",
    "SUPERATIVAR PORTUGUES 4": "SUPERATIVAR LINGUAGENS 4",
    "SUPERATIVAR PORTUGUES 5": "SUPERATIVAR LINGUAGENS 5",
    "SUPERATIVAR LINGUA PORTUGUESA 3": "SUPERATIVAR LINGUAGENS 3",
    "SUPERATIVAR LINGUA PORTUGUESA 4": "SUPERATIVAR LINGUAGENS 4",
    "SUPERATIVAR LINGUA PORTUGUESA 5": "SUPERATIVAR LINGUAGENS 5",
    # ACerta Brasil: "Português" -> "Língua Portuguesa" (DB já tem o nome certo)
    "ACERTA BRASIL PORTUGUES": "ACERTA BRASIL LINGUA PORTUGUESA",
    # E1 (merge já aplicado no catálogo)
    "BRINCANDO E APRENDENDO PROFESSOR": "BRINCANDO E APRENDENDO",
}


@dataclass(frozen=True)
class ProjetoResolution:
    """Resultado da resolução. `status` in {matched, ambiguous, unmatched}."""

    status: str
    projeto: Projeto | None = None
    matched_via: str = ""  # "norm" | "alias" | "canon_rule"
    canonical_key: str = ""
    candidates: list[str] = field(default_factory=list)
    reason: str = ""


def _norm(s: str) -> str:
    """NFKD + remove acentos + colapsa espaços + UPPERCASE."""
    s = unicodedata.normalize("NFKD", (s or "").strip())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).upper()


def _canon_key(s: str) -> str:
    """Chave canônica determinística: norm + (& -> E) + remover hífen/vírgula + remover prefixo PROJETO."""
    s = _norm(s).replace("&", "E").replace(",", " ").replace("-", " ")
    s = re.sub(r"^PROJETO\s+", "", s)
    return re.sub(r"\s+", " ", s).strip()


@dataclass
class ProjetoIndex:
    """Índice do catálogo do DB para resolução em lote (construir 1x por import)."""

    by_norm: dict[str, list[Projeto]]
    by_canon: dict[str, list[Projeto]]


def build_projeto_index() -> ProjetoIndex:
    """Constrói o índice a partir do catálogo atual do DB (SSOT)."""
    by_norm: dict[str, list[Projeto]] = defaultdict(list)
    by_canon: dict[str, list[Projeto]] = defaultdict(list)
    for p in Projeto.objects.all():
        by_norm[_norm(p.nome)].append(p)
        by_canon[_canon_key(p.nome)].append(p)
    return ProjetoIndex(by_norm=dict(by_norm), by_canon=dict(by_canon))


def resolve_projeto_export(raw_name: str, *, index: ProjetoIndex | None = None) -> ProjetoResolution:
    """
    Resolve o nome de projeto do export-contract para um `Projeto` do catálogo.

    Args:
        raw_name: nome bruto vindo do export.
        index: índice pré-construído (opcional; se ausente, constrói do DB).

    Returns:
        ProjetoResolution com status matched/ambiguous/unmatched.
    """
    if not (raw_name or "").strip():
        return ProjetoResolution(status="unmatched", reason="nome vazio")

    idx = index or build_projeto_index()

    n = _norm(raw_name)
    ck = _canon_key(raw_name)
    # alias é keyed pela CHAVE CANÔNICA (tolerante a hífen/vírgula/&/prefixo)
    alias_target = _SCOPED_ALIASES.get(ck)

    if alias_target is not None:
        # alias escopado: resolve pelo alvo canônico (já é forma canônica do catálogo)
        hits = idx.by_canon.get(alias_target, [])
        if len(hits) == 1:
            return ProjetoResolution(
                status="matched",
                projeto=hits[0],
                matched_via="alias",
                canonical_key=alias_target,
                reason="match por alias escopado",
            )
        if len(hits) > 1:
            return ProjetoResolution(
                status="ambiguous",
                canonical_key=alias_target,
                candidates=sorted(str(p.nome) for p in hits),
                reason="alias casa múltiplos projetos (não escolher no chute)",
            )
        return ProjetoResolution(
            status="unmatched", canonical_key=alias_target, reason="alvo do alias não existe no catálogo"
        )

    # 1) match exato por norm (preferido — evita falsa ambiguidade da chave canônica)
    norm_hits = idx.by_norm.get(n, [])
    if len(norm_hits) == 1:
        return ProjetoResolution(
            status="matched", projeto=norm_hits[0], matched_via="norm", canonical_key=n, reason="match exato por norm"
        )
    if len(norm_hits) > 1:
        return ProjetoResolution(
            status="ambiguous",
            canonical_key=n,
            candidates=sorted(str(p.nome) for p in norm_hits),
            reason="múltiplos projetos com o mesmo nome normalizado",
        )

    # 2) match por chave canônica determinística (& <-> E, hífen, vírgula, prefixo PROJETO)
    canon_hits = idx.by_canon.get(ck, [])
    if len(canon_hits) == 1:
        return ProjetoResolution(
            status="matched",
            projeto=canon_hits[0],
            matched_via="canon_rule",
            canonical_key=ck,
            reason="match por regra determinística",
        )
    if len(canon_hits) > 1:
        return ProjetoResolution(
            status="ambiguous",
            canonical_key=ck,
            candidates=sorted(str(p.nome) for p in canon_hits),
            reason="chave canônica casa múltiplos projetos (não escolher no chute)",
        )

    return ProjetoResolution(status="unmatched", canonical_key=ck, reason="nenhum projeto correspondente")
