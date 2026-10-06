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
   - `ACerta Brasil Matemática` -> `ACerta Matemática`; `ACerta Brasil Português` e
     `ACerta Brasil Língua Portuguesa` -> `ACerta Português` (fusão decidida pelo dono em 02/10/2026)
   - `Fluir das Emoções` -> `Fluir das Emoções (Antigo)` (rename decidido pelo dono em 02/10/2026;
     `Fluir das Emoções - 1/2/3` têm chave própria e não passam pelo apelido)
   - `Brincando e Aprendendo Professor` -> `Brincando e Aprendendo`
   - nomes antigos apagados/renomeados em prod (decisão do dono em 05/10/2026):
     `Escrever, Comunicar e Ser` -> `ECS`; `Educação Financeira Livro N` -> `ED FINANCEIRA N` (N=1..4);
     `Aprendendo Mais Matemática N` -> `PROJETO AMMA N` (N=1,2)

Precedência: nome exato (norm) > chave canônica > alias. O nome que existe no catálogo, em
qualquer grafia, vence o alias; o alias só vale para nome que o catálogo não tem. Consequência,
nos dois estados de um rename/fusão feito por script de dados (que roda depois do deploy):
- antes do script (o projeto antigo existe): o nome da planilha casa o projeto antigo — nada é
  desviado para o alvo do alias;
- depois do script (o projeto antigo foi APAGADO ou RENOMEADO): o nome cai no alias e resolve
  para o alvo — o master `projeto` não recria o projeto antigo.
O índice inclui projeto inativo: a fusão que só desativar o projeto antigo NÃO ativa o alias.
Alias cujo alvo não existe devolve `unmatched` (RELAY-53: o alias antigo de `ACERTA BRASIL
PORTUGUES` apontava para um nome ausente de prod e sombreava o projeto de nome idêntico).

Ambiguidade (a chave canônica casa >1 projeto distinto) **falha explicitamente**
(`status="ambiguous"`), nunca escolhe um alvo no chute.

NÃO importa dados; só resolve nomes. Não tem efeito colateral.
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field, replace

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
    # ACerta Brasil juntado em ACerta (decisão do dono, 02/10/2026; a fusão é script de dados). Só
    # vale depois da fusão: enquanto "ACERTA BRASIL ..." existir no catálogo, o nome vence o apelido.
    "ACERTA BRASIL MATEMATICA": "ACERTA MATEMATICA",
    "ACERTA BRASIL PORTUGUES": "ACERTA PORTUGUES",
    "ACERTA BRASIL LINGUA PORTUGUESA": "ACERTA PORTUGUES",
    # "Fluir das Emoções" (sem número) renomeado para "... (Antigo)" (decisão do dono, 02/10/2026);
    # a planilha continua mandando o nome sem o sufixo. "FLUIR DAS EMOCOES 1/2/3" têm outra chave.
    "FLUIR DAS EMOCOES": "FLUIR DAS EMOCOES (ANTIGO)",
    # E1 (merge já aplicado no catálogo)
    "BRINCANDO E APRENDENDO PROFESSOR": "BRINCANDO E APRENDENDO",
    # Nomes antigos que não existem mais em prod (decisão do dono, 05/10/2026), 1 para 1. Sem eles um
    # pacote antigo recriaria o projeto. A chave canônica já tira a vírgula de "ESCREVER, COMUNICAR E SER"
    # e o prefixo de "PROJETO AMMA n".
    "ESCREVER COMUNICAR E SER": "ECS",
    "EDUCACAO FINANCEIRA LIVRO 1": "ED FINANCEIRA 1",
    "EDUCACAO FINANCEIRA LIVRO 2": "ED FINANCEIRA 2",
    "EDUCACAO FINANCEIRA LIVRO 3": "ED FINANCEIRA 3",
    "EDUCACAO FINANCEIRA LIVRO 4": "ED FINANCEIRA 4",
    "APRENDENDO MAIS MATEMATICA 1": "AMMA 1",
    "APRENDENDO MAIS MATEMATICA 2": "AMMA 2",
}


@dataclass(frozen=True)
class ProjetoResolution:
    """Resultado da resolução. `status` in {matched, ambiguous, unmatched}."""

    status: str
    projeto: Projeto | None = None
    matched_via: str = ""  # "norm" | "alias" | "canon_rule" | "disciplina"
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

    # 1) match exato por norm. Vem antes do alias: o nome que existe no catálogo é a resposta,
    # e evita a falsa ambiguidade da chave canônica.
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

    # 2) match por chave canônica determinística (& <-> E, hífen, vírgula, prefixo PROJETO). Vem
    # antes do alias: "ACERTA BRASIL - PORTUGUES" fica em "ACERTA BRASIL PORTUGUES" enquanto ele existir.
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

    # 3) alias escopado, keyed pela CHAVE CANÔNICA (tolerante a hífen/vírgula/&/prefixo). Só chega
    # aqui o nome que NÃO existe no catálogo em nenhuma grafia: o apelido nunca desvia de um projeto
    # que existe. Alvo ausente do catálogo = `unmatched`.
    alias_target = _SCOPED_ALIASES.get(ck, "")
    alias_hits = idx.by_canon.get(alias_target, []) if alias_target else []
    if len(alias_hits) == 1:
        return ProjetoResolution(
            status="matched",
            projeto=alias_hits[0],
            matched_via="alias",
            canonical_key=alias_target,
            reason="match por alias escopado",
        )
    if len(alias_hits) > 1:
        return ProjetoResolution(
            status="ambiguous",
            canonical_key=alias_target,
            candidates=sorted(str(p.nome) for p in alias_hits),
            reason="alias casa múltiplos projetos (não escolher no chute)",
        )

    return ProjetoResolution(status="unmatched", canonical_key=ck, reason="nenhum projeto correspondente")


# ── Agenda: agrupador + disciplina (decisão do dono P8, 05/10/2026) ──
# (chave canônica do agrupador, disciplina do export) -> nome do projeto da disciplina. Disciplina dupla
# (LING-MAT), vazia ou de público não está aqui: o evento fica no agrupador. Só Superativar e ACerta.
_AGRUPADOR_POR_DISCIPLINA: dict[tuple[str, str], str] = {
    ("SUPERATIVAR", "LING"): "Superativar Linguagens",
    ("SUPERATIVAR", "MAT"): "Superativar Matemática",
    ("ACERTA", "LING"): "ACerta Português",
    ("ACERTA", "MAT"): "ACerta Matemática",
}


def resolve_projeto_agenda(raw_name: str, disciplina: str, *, index: ProjetoIndex | None = None) -> ProjetoResolution:
    """Resolve o projeto de um evento da agenda. Agrupador (Superativar/ACerta) com disciplina única
    (`LING`/`MAT`) vai para o projeto da disciplina; o resto segue `resolve_projeto_export`. Se o projeto
    da disciplina não existir no catálogo, o evento fica no agrupador (nunca `unmatched` por causa disto)."""
    idx = index or build_projeto_index()
    alvo = _AGRUPADOR_POR_DISCIPLINA.get((_canon_key(raw_name), (disciplina or "").strip().upper()))
    if alvo:
        res = resolve_projeto_export(alvo, index=idx)
        if res.status == "matched":
            return replace(res, matched_via="disciplina", reason="agrupador classificado pela disciplina")
    return resolve_projeto_export(raw_name, index=idx)
