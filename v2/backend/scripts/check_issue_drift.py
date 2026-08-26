#!/usr/bin/env python
"""
Reconcilia estado de issue com o que a doc viva afirma (Fase A.1 do plano).

O QUE OS OUTROS GATES NAO ALCANCAM. As Fases B–F impedem drift NOVO: sao todas
por PR. Nenhuma limpa o que ja estava la quando foram construidas — e a Fase A,
que era exatamente isso, nunca foi executada.

CASO VERIFICADO PONTA A PONTA (2026-08-26): a issue #1611 esta CLOSED, e
`v2/docs/specs/backend/backup-dr.spec.md:40` diz "Restore (leitura) — quebrado",
`:109` diz "(M26-01, P0, issue #1611)", e `INDEX_SDD.md:81` repete "restore
quebrado, #1611 P0". Quem abre a spec CANONICA de DR conclui que o restore de
producao nao funciona. O gate da Fase C bloquearia — mas o fix mergeou antes dele
existir, e gate por PR nao alcanca o passado.

O NUMERO, MEDIDO COM CUIDADO. 146 issues fechadas sao citadas em doc viva, em 305
lugares. NAO sao 146 mentiras: "corrigido em #1611" e referencia historica
correta. Contar palavra-chave aqui e a armadilha de sempre — o texto que descreve
a CORRECAO cita a mesma issue que o texto que descreve o defeito. Filtrando para
citacao com marcador de ABERTO e SEM marcador de corrigido: 71, sendo 30 nas
specs canonicas.

POR QUE RATCHET, E NAO BLOQUEIO NEM AVISO:
  bloquear  com 71 pendentes reprova todo PR no dia 1, e o gate e revertido.
  avisar    e o que fez o limiar de 180 dias virar decoracao — aviso sem acao
            associada e ruido, e ruido treina a ignorar.
  ratchet   sobre piso medido: a contagem por raiz nao pode CRESCER. Padrao
            provado neste repositorio (cobertura vitest, subida 3x em 4 dias).
            A reducao e trabalho de conteudo; o mecanismo garante que ela nunca
            ande para tras.

A HEURISTICA E ASSUMIDA, NAO DISFARCADA. "Marcador de aberto na mesma linha" nao
prova que o doc mente — prova que merece triagem. A saida chama de SUSPEITA, e o
que o ratchet trava e o numero de suspeitas.

Uso (CI):
    python v2/backend/scripts/check_issue_drift.py --baseline v2/docs/.issue-drift-baseline.json

Uso (teste/offline):
    python .../check_issue_drift.py --repo-root DIR --closed-from f.json --baseline p.json

Exit 0 = dentro do piso. Exit 1 = cresceu. Exit 2 = uso/configuracao.

Testes: apps/core/tests/test_check_issue_drift.py
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import subprocess
import sys

for _fluxo in (sys.stdout, sys.stderr):
    try:
        _fluxo.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except (AttributeError, OSError):
        pass

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import doc_frontmatter  # noqa: E402

RAIZES_DOC = ["v2/docs", "docs"]
IGNORA_DOC = ("_archive", "worktrees", "node_modules")

MENCAO = re.compile(r"#(\d{3,5})\b")
ABERTO = re.compile(
    r"(?i)(\baberto\b|\bquebrad|\bpendente\b|\bP0\b|\bP1\b|⛔|nao corrigido|não corrigido|\bbloqueia\b)"
)
# Se a MESMA linha diz que foi resolvido, a citacao e historica e esta correta.
CORRIGIDO = re.compile(r"(?i)(corrigid|resolvid|fechad|implementad|mergead|conclu|feito em|sanad)")


def _fechadas_da_api() -> set[str] | None:
    try:
        r = subprocess.run(
            ["gh", "issue", "list", "--state", "closed", "--limit", "800", "--json", "number"],
            capture_output=True,
            text=True,
            check=False,
            timeout=180,
            encoding="utf-8",
            errors="replace",
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0 or not r.stdout.strip():
        return None
    try:
        return {str(x["number"]) for x in json.loads(r.stdout)}
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


def _raiz_de(rel: str) -> str:
    partes = rel.split("/")
    return "/".join(partes[:3]) if len(partes) > 3 else "/".join(partes[:2])


def _varre(raiz: pathlib.Path, fechadas: set[str]) -> list[tuple[str, int, str, str]]:
    achados: list[tuple[str, int, str, str]] = []
    for base in RAIZES_DOC:
        d = raiz / base
        if not d.is_dir():
            continue
        for p in sorted(d.rglob("*.md")):
            rel = p.relative_to(raiz).as_posix()
            if any(x in rel for x in IGNORA_DOC):
                continue
            try:
                texto = p.read_text(encoding="utf-8")
            except OSError:
                continue
            if doc_frontmatter.fora_de_escopo(texto):
                continue
            for n, linha in enumerate(texto.split("\n"), 1):
                if not ABERTO.search(linha) or CORRIGIDO.search(linha):
                    continue
                for m in MENCAO.finditer(linha):
                    if m.group(1) in fechadas:
                        achados.append((rel, n, m.group(1), linha.strip()[:100]))
    return achados


def _resumo(linhas: list[str]) -> None:
    destino = os.environ.get("GITHUB_STEP_SUMMARY")
    if not destino:
        return
    try:
        with open(destino, "a", encoding="utf-8") as fh:
            fh.write("\n".join(linhas) + "\n")
    except OSError:
        pass


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--baseline", help="JSON {raiz: teto}. Obrigatorio.")
    ap.add_argument("--closed-from", help="JSON com numeros de issue fechada (teste/offline)")
    a = ap.parse_args(argv[1:])

    raiz = pathlib.Path(a.repo_root).resolve()
    if not raiz.is_dir():
        print(f"ERRO: repo-root nao encontrado: {raiz}", file=sys.stderr)
        return 2

    # Piso ausente lido como zero reprovaria tudo no dia 1; lido como vazio
    # aprovaria por vacuidade. Nenhum dos dois: e erro de configuracao.
    if not a.baseline:
        print("ERRO: --baseline e obrigatorio. Sem piso medido nao ha ratchet —", file=sys.stderr)
        print("zero reprovaria tudo hoje, e vazio aprovaria por vacuidade.", file=sys.stderr)
        return 2
    try:
        piso = json.loads(pathlib.Path(a.baseline).read_text(encoding="utf-8"))
        if not isinstance(piso, dict):
            raise ValueError("o piso precisa ser um objeto {raiz: teto}")
    except (OSError, json.JSONDecodeError, ValueError) as e:
        print(f"ERRO: piso ilegivel em {a.baseline}: {e}", file=sys.stderr)
        return 2

    if a.closed_from:
        try:
            fechadas = {str(x) for x in json.loads(pathlib.Path(a.closed_from).read_text(encoding="utf-8"))}
        except (OSError, json.JSONDecodeError) as e:
            print(f"ERRO: --closed-from ilegivel: {e}", file=sys.stderr)
            return 2
    else:
        lidas = _fechadas_da_api()
        if lidas is None:
            print()
            print("AVISO: nao consegui listar as issues fechadas (gh indisponivel ou sem")
            print("permissao). NADA foi verificado aqui — isto nao e aprovacao, e ausencia")
            print("de medida. Fazer o CI depender da API do GitHub seria pior.")
            return 0
        fechadas = lidas

    achados = _varre(raiz, fechadas)

    por_raiz: dict[str, int] = {}
    for rel, _, _, _ in achados:
        por_raiz[_raiz_de(rel)] = por_raiz.get(_raiz_de(rel), 0) + 1

    cresceram = {r: (n, piso.get(r, 0)) for r, n in por_raiz.items() if n > piso.get(r, 0)}
    caiu = {r: (por_raiz.get(r, 0), t) for r, t in piso.items() if por_raiz.get(r, 0) < t}

    if achados:
        print(f"SUSPEITA — {len(achados)} citacao(oes) a issue FECHADA com marcador de aberto:")
        for rel, n, num, trecho in achados[:40]:
            print(f"  {rel}:{n}  #{num}")
            print(f"      {trecho}")
        if len(achados) > 40:
            print(f"  ... e mais {len(achados) - 40}")
        print()
        print("Heuristica, nao veredito: marcador de aberto na mesma linha diz que a")
        print("linha merece triagem, nao que ela mente. Confira antes de editar.")
        print()

    resumo = [
        "## Reconciliacao de issue",
        "",
        f"**{len(achados)}** suspeita(s) em {len(por_raiz)} raiz(es). "
        "Citacao a issue fechada com marcador de aberto e sem marcador de corrigido.",
        "",
    ]
    if por_raiz:
        resumo += ["| raiz | agora | teto |", "| --- | ---: | ---: |"]
        resumo += [f"| `{r}` | {n} | {piso.get(r, 0)} |" for r, n in sorted(por_raiz.items())]
        resumo.append("")
    _resumo(resumo)

    if caiu:
        print("Caiu abaixo do teto — aperte o piso para travar o ganho:")
        for r, (agora, teto) in sorted(caiu.items()):
            print(f"  {r}: {agora} (teto {teto})")
        print()

    if cresceram:
        print("BLOQUEIO — a contagem CRESCEU acima do piso medido:")
        for r, (agora, teto) in sorted(cresceram.items()):
            print(f"  {r}: {agora} > {teto}")
        print()
        print("O piso existe para a divida so andar para baixo. Corrija a citacao, ou")
        print(f"justifique a subida ajustando {a.baseline} no mesmo PR.")
        return 1

    print(f"OK {len(achados)} suspeita(s), nenhuma raiz acima do piso medido.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
