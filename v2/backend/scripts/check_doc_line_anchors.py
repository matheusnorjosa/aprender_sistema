#!/usr/bin/env python
"""
Ancora de codigo em spec e por SIMBOLO, nao por `arquivo.py:NNN`.

O PROBLEMA E DE CLASSE, NAO DE ARQUIVO. O doc-drift-auditor (PR #1998) achou, na
primeira rodada real, ancoras `arquivo.py:NNN` obsoletas no imports.spec.md: o
importer cresceu ~500->1900 linhas e nenhuma ancora foi re-derivada, entao a spec
manda o leitor para uma linha que hoje tem outro codigo. Nao e cosmetico — quem
clica cai no lugar errado e conclui a coisa errada sobre o sistema.

Medido em 2026-09-11: 52 linhas de ancora-com-linha em 17 specs, contra ~575
referencias a nivel de arquivo/simbolo (link markdown + backtick sem linha, ~92%).
A ancora-com-linha e a minoria de ~8% que drifta a cada movimento de codigo. O
nome do simbolo (`PROTECTED_FIELDS`, `_assign_groups`) e estavel a esse movimento
— e a spec ja usa esse estilo na esmagadora maioria das referencias.

CALIBRAGEM: BLOQUEIA. Preciso (regex de `arquivo.ext:NNN`), com a divida existente
VARRIDA antes de trancar (limpar primeiro, trancar depois) e conserta-se DENTRO do
PR — troca-se a ancora pelo nome do simbolo. A excecao deliberada (ex.: prosa de
auditoria de seguranca que cita um range exato) entra no allowlist COM MOTIVO,
mesmo contrato do `adr-numeros-allowlist.txt`: entrada nua e o comeco da erosao.

Escopo: `v2/docs/specs/**/*.md` (specs SDD). Ignora bloco de codigo cercado (```),
o frontmatter (onde `sources_of_truth` e caminho puro) e specs fora de escopo
(status historical/stale/superseded/deprecated — historico nao se corrige,
ADR-017 item 5).

Uso:
    python v2/backend/scripts/check_doc_line_anchors.py [--repo-root DIR] [--allowlist PATH]

Exit 0 = nenhuma ancora de linha. Exit 1 = ancora encontrada / allowlist sem motivo.
Exit 2 = uso.

Testes: apps/core/tests/test_check_doc_line_anchors.py
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

# `doc_frontmatter` e o SSOT de como se le uma spec — dois parsers respondendo
# diferente sobre o mesmo arquivo e o gerador de drift que estes gates combatem.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import doc_frontmatter  # noqa: E402

# Escopo apertado (hard-ban): so as specs SDD, onde referenciar por simbolo ja e a
# convencao dominante. Planos/auditorias citam linha exata de proposito — fora daqui.
SPECS_ROOT = "v2/docs/specs"
IGNORA = ("_archive", "worktrees", "node_modules")

ALLOWLIST = "v2/docs/.doc-line-anchors-allowlist.txt"
MOTIVO_MINIMO = 10

# So a forma INEQUIVOCA: `caminho/arquivo.ext:NNN` (range `:N-M`, cadeia `:N,M-P`),
# com extensao de CODIGO. Um endereco de rede (`127.0.0.1:9443`, bare `:5173`) nao
# tem extensao de codigo antes do `:`, entao NUNCA casa aqui — porta e conteudo
# legitimo, e hard-ban que reprova porta nasce vermelho e e desligado (gate-calibration).
# A forma bare `` `:NNN` `` (arquivo nomeado antes, linha solta) e ambigua com porta e
# fica FORA do gate: e varrida uma vez, e regressao dela e caso do doc-drift-auditor.
# Link markdown (`](../x.py)`) e ancora `#L47` tambem nao tem `.ext:NNN` -> nao casam.
_LINHAS = r"\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*"
_EXTS = r"(?:py|pyi|tsx|ts|jsx|js|yml|yaml|sh|toml|ini|cfg|md|json)"
ANCORA_ARQUIVO = re.compile(r"[\w./\\-]+\." + _EXTS + r":" + _LINHAS)

_ALLOW_LINHA = re.compile(
    r"^(?P<rel>\S+)\s+(?P<ancora>[\w./\\-]+\." + _EXTS + r":" + _LINHAS + r")" + r"\s*(?:[—–-]{1,2}\s*(?P<motivo>.*))?$"
)


def _le_allowlist(raiz: pathlib.Path) -> tuple[set[tuple[str, str]], list[str]]:
    """(pares (rel, ancora) perdoados, entradas sem motivo escrito).

    Entrada sem motivo e o comeco da erosao: um allowlist que so aceita a ancora
    vira lugar de esconder drift, e o gate volta a nao valer nada.
    """
    perdoados: set[tuple[str, str]] = set()
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
        m = _ALLOW_LINHA.match(linha)
        if not m:
            continue
        rel = m.group("rel").replace("\\", "/")
        ancora = m.group("ancora")
        motivo = (m.group("motivo") or "").strip()
        if len(motivo) < MOTIVO_MINIMO:
            sem_motivo.append(f"{rel} {ancora}")
        else:
            perdoados.add((rel, ancora))
    return perdoados, sem_motivo


def _ancoras_de(texto: str) -> list[tuple[int, str]]:
    """(linha 1-indexada, ancora) de cada ancora fora do frontmatter e de fences."""
    achados: list[tuple[int, str]] = []
    linhas = texto.split("\n")
    in_fm = False
    in_fence = False
    for i, linha in enumerate(linhas):
        strip = linha.strip()
        if i == 0 and strip == "---":
            in_fm = True
            continue
        if in_fm:
            if strip == "---":
                in_fm = False
            continue
        if strip.startswith("```") or strip.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for m in ANCORA_ARQUIVO.finditer(linha):
            achados.append((i + 1, m.group(0)))
    return achados


def _specs_vivas(raiz: pathlib.Path):
    d = raiz / SPECS_ROOT
    if not d.is_dir():
        return
    for p in sorted(d.rglob("*.md")):
        rel = p.relative_to(raiz).as_posix()
        if any(x in rel for x in IGNORA):
            continue
        try:
            texto = p.read_text(encoding="utf-8")
        except OSError:
            continue
        if doc_frontmatter.fora_de_escopo(texto):
            continue  # historico nao se corrige (ADR-017 item 5)
        yield rel, texto


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--allowlist", default=None, help="override do caminho do allowlist (testes)")
    a = ap.parse_args(argv[1:])

    raiz = pathlib.Path(a.repo_root).resolve()
    if not raiz.is_dir():
        print(f"ERRO: repo-root nao encontrado: {raiz}", file=sys.stderr)
        return 2

    perdoados, sem_motivo = _le_allowlist(raiz)

    if sem_motivo:
        print("BLOQUEIO — entrada de allowlist sem motivo escrito:")
        for e in sorted(set(sem_motivo)):
            print(f"  {e}")
        print()
        print(f"Escreva `<spec> <ancora> — por que` em {ALLOWLIST}. Allowlist que aceita")
        print("ancora nua vira lugar de esconder drift, e o gate deixa de valer.")
        return 1

    achados: list[str] = []
    for rel, texto in _specs_vivas(raiz):
        for linha, ancora in _ancoras_de(texto):
            if (rel, ancora) in perdoados:
                continue
            achados.append(f"  {rel}:{linha}: `{ancora}`")

    if achados:
        print(f"BLOQUEIO — {len(achados)} ancora(s) de linha em spec (drifta quando o codigo anda):")
        for a_ in achados:
            print(a_)
        print()
        print("Referencie o SIMBOLO (funcao/classe/constante), nao a linha: o nome e estavel")
        print("a movimento de codigo, a linha nao. Ex.: `PROTECTED_FIELDS` em vez de `x.py:50`.")
        print(f"Excecao deliberada (range exato de auditoria) entra em {ALLOWLIST}")
        print("no formato `<spec> <ancora> — motivo`.")
        return 1

    print(f"OK nenhuma ancora de linha em {SPECS_ROOT}/**.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
