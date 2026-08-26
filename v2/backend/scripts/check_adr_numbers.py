#!/usr/bin/env python
"""
Numero de ADR e unico — nas DUAS arvores (F.1 do PLAN_doc_drift_2026-08-25).

O PROBLEMA NAO E A COLISAO QUE EXISTE, E A PROXIMA. Ha dois `ADR-012` em arvores
diferentes, e isso ja esta documentado em
`docs/architecture/project-decisions/README.md:30` como "pendente de
renumeracao". Renumerar agora e churn em duas arvores por ganho cosmetico —
nao e o que este script faz.

O que uma nota em README nao faz e impedir reincidencia, e o proprio plano
registra que o **ADR-019 recriou a colisao 21 dias depois de a primeira ser
documentada**. Medido em 2026-08-26: `docs/architecture/project-decisions/` vai
ate ADR-018 e `v2/docs/adr/` ja tem ADR-019. O proximo ADR escrito na primeira
arvore colide. Isso nao e divida do passado — e uma armadilha armada para o
proximo commit.

O DANO E CONCRETO, nao teorico: `docs/guides/etl.md:5` cita "ADR-012" querendo
dizer o de SHA1 (arvore v2), e dentro do mkdocs o leitor resolve para o de
guardrails — outro assunto, outra decisao. Numero ambiguo faz a citacao apontar
para o documento errado sem que ninguem perceba.

CALIBRAGEM: BLOQUEIA. Preciso (parse de nome de arquivo, zero heuristica), raro
(uma colisao hoje) e conserta-se DENTRO do PR — escolhe-se outro numero, e a
saida diz qual esta livre. A colisao existente entra no allowlist com motivo,
mesmo contrato do `citacoes-apagadas-allowlist.txt`: limpar primeiro, trancar
depois.

Uso:
    python v2/backend/scripts/check_adr_numbers.py [--repo-root DIR]

Exit 0 = numeracao unica. Exit 1 = colisao. Exit 2 = uso.

Testes: apps/core/tests/test_check_adr_numbers.py
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

for _fluxo in (sys.stdout, sys.stderr):
    try:
        _fluxo.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except (AttributeError, OSError):
        pass

# As duas arvores compartilham UM espaco de numeracao, embora vivam separadas.
ARVORES = ("docs/architecture/project-decisions", "v2/docs/adr")

# `README.md` e `template.md` moram na mesma pasta e nao sao ADR.
ADR = re.compile(r"^ADR-(\d{3})\b", re.IGNORECASE)

ALLOWLIST = "docs/architecture/project-decisions/adr-numeros-allowlist.txt"
MOTIVO_MINIMO = 10


def _le_allowlist(raiz: pathlib.Path) -> tuple[set[str], list[str]]:
    """(numeros perdoados, numeros listados sem motivo).

    Entrada sem motivo e o comeco da erosao: um allowlist que so aceita numero
    vira lugar de esconder colisao, e o gate volta a nao valer nada.
    """
    perdoados: set[str] = set()
    sem_motivo: list[str] = []
    f = raiz / ALLOWLIST
    if not f.is_file():
        return perdoados, sem_motivo
    try:
        linhas = f.read_text(encoding="utf-8").splitlines()
    except OSError:
        return perdoados, sem_motivo
    for linha in linhas:
        linha = linha.strip()
        if not linha or linha.startswith("#"):
            continue
        m = re.match(r"^(\d{3})\s*(?:[—–-]{1,2}\s*(.*))?$", linha)
        if not m:
            continue
        motivo = (m.group(2) or "").strip()
        if len(motivo) < MOTIVO_MINIMO:
            sem_motivo.append(m.group(1))
        else:
            perdoados.add(m.group(1))
    return perdoados, sem_motivo


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--repo-root", default=".")
    a = ap.parse_args(argv[1:])

    raiz = pathlib.Path(a.repo_root).resolve()
    if not raiz.is_dir():
        print(f"ERRO: repo-root nao encontrado: {raiz}", file=sys.stderr)
        return 2

    # numero -> [caminhos]
    por_numero: dict[str, list[str]] = {}
    for arv in ARVORES:
        d = raiz / arv
        if not d.is_dir():
            continue  # arvore ausente nao e erro; e repo parcial ou teste
        for p in sorted(d.glob("*.md")):
            m = ADR.match(p.name)
            if m:
                por_numero.setdefault(m.group(1), []).append(f"{arv}/{p.name}")

    perdoados, sem_motivo = _le_allowlist(raiz)

    colisoes = {n: fs for n, fs in sorted(por_numero.items()) if len(fs) > 1 and n not in perdoados}

    if sem_motivo:
        print("BLOQUEIO — entrada de allowlist sem motivo escrito:")
        for n in sorted(set(sem_motivo)):
            print(f"  {n}")
        print()
        print(f"Escreva `NNN — por que` em {ALLOWLIST}. Allowlist que aceita numero")
        print("nu vira lugar de esconder colisao, e o gate deixa de valer.")
        return 1

    if colisoes:
        usados = {int(n) for n in por_numero}
        proximo = max(usados) + 1 if usados else 1
        print(f"BLOQUEIO — {len(colisoes)} numero(s) de ADR usado(s) mais de uma vez:")
        for n, fs in colisoes.items():
            print(f"  ADR-{n}")
            for f in fs:
                print(f"      {f}")
        print()
        print("As duas arvores compartilham UM espaco de numeracao. Numero repetido faz")
        print("a citacao em prosa apontar para o documento errado — ja acontece com o")
        print("012, citado em docs/guides/etl.md querendo dizer o da arvore v2.")
        print()
        print(f"Proximo numero livre: ADR-{proximo:03d}.")
        print(f"Se a colisao for historica e deliberada, registre em {ALLOWLIST}")
        print("no formato `NNN — motivo`.")
        return 1

    print(f"OK {len(por_numero)} ADR(s), numeracao unica nas {len(ARVORES)} arvores.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
