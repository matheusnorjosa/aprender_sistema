"""
Leitor de frontmatter das specs SDD — SSOT unico para os gates de documentacao.

POR QUE EXISTE. `check_doc_impact.py` e `doc_drift_report.py` precisam da MESMA
resposta para "o que esta spec declara como fonte da verdade". Dois parsers que
respondem diferente sobre o mesmo arquivo e literalmente o gerador de drift que
estes gates existem para combater — e a regra do repo e explicita: 1 SSOT por
topico, linkar em vez de duplicar.

POR QUE ESCRITO A MAO. O parser de `scripts/check_doc_frontmatter.py` usa
`^([A-Za-z_]+):\\s*(.*)$`, que casa `sources_of_truth:` com valor VAZIO e descarta
os itens `  - caminho` de baixo. Quem confiasse nele leria toda spec como se nao
declarasse fonte nenhuma, e toda spec ficaria "verde" — verde por falta de dado,
que e o modo de falha central deste plano. PyYAML resolveria, mas os gates rodam
como script solto no runner, antes de qualquer `pip install` do backend.

Testes: apps/core/tests/test_doc_frontmatter.py
"""

from __future__ import annotations

import re

# Status que declaram o doc como registro, nao como contrato vigente. Historico
# nao se corrige (ADR-017 item 5), entao apontar drift neles e ruido garantido.
STATUS_FORA = {"historical", "stale", "superseded", "deprecated"}

_CHAVE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:(.*)$")


def frontmatter(texto: str) -> tuple[dict[str, str], list[str]]:
    """Devolve (campos escalares, itens de `sources_of_truth`).

    Sem frontmatter, devolve ({}, []) — o chamador distingue "nao e doc SDD" de
    "e doc SDD que nao declara fonte", que sao coisas diferentes.
    """
    linhas = texto.split("\n")
    if not linhas or linhas[0].strip() != "---":
        return {}, []

    campos: dict[str, str] = {}
    fontes: list[str] = []
    dentro_lista = False

    for ln in linhas[1:]:
        if ln.strip() == "---":
            break
        # Item de lista: indentado e comecando com "- ".
        if ln[:1].isspace() and ln.strip().startswith("- "):
            if dentro_lista:
                fontes.append(ln.strip()[2:].strip().strip("`\"'"))
            continue
        m = _CHAVE.match(ln)
        if not m:
            continue
        dentro_lista = False
        chave = m.group(1)
        valor = m.group(2).strip()
        if chave == "sources_of_truth":
            dentro_lista = True
            # Forma inline: `sources_of_truth: [a.py, b.py]`
            if valor.startswith("[") and valor.endswith("]"):
                fontes += [x.strip().strip("`\"'") for x in valor[1:-1].split(",") if x.strip()]
                dentro_lista = False
            continue
        campos[chave] = valor

    return campos, fontes


def status(texto: str) -> str:
    """`status` do frontmatter, em minusculas. Vazio se nao houver."""
    campos, _ = frontmatter(texto)
    return campos.get("status", "").strip().lower()


def fora_de_escopo(texto: str) -> bool:
    """True quando o doc e registro historico e nao contrato vigente."""
    return status(texto) in STATUS_FORA
