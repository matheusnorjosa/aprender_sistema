#!/usr/bin/env python
"""
Confere quais gates sao gates de verdade (Fase E.3 do PLAN_doc_drift_2026-08-25).

O PROBLEMA MEDIDO em 2026-08-25: dezenove jobs carregam `[required]` no proprio
nome; o ruleset da `main` exige dez. Nove estao rotulados como obrigatorios sem
serem — entre eles `backend rbac-lint`, `backend typecheck (pyright)`,
`backend tests (runner)` e `docker parity (backend)`. Quem le o nome no PR
conclui que aquilo trava o merge. Nao trava.

Isso importa mais que drift de doc: e o repositorio informando errado sobre a
propria protecao. Um nome nao e enforcement, e ninguem tinha como saber a
diferenca sem abrir a configuracao do ruleset.

DUAS DIVERGENCIAS, CALIBRAGEM OPOSTA — a diferenca e quem consegue consertar:

  1. EXIGIDO PELO RULESET, SEM JOB QUE PRODUZA        [BLOQUEIA]
     Context exigido que ninguem emite deixa o PR "Expected" para sempre. E
     preciso, e raro (hoje: zero) e conserta-se DENTRO do PR — alguem renomeou
     um job. Bloquear sobre baseline limpo custa nada.

  2. DECLARA `[required]`, RULESET NAO EXIGE          [AVISA]
     Corrigir e acao de admin no ruleset, nao mudanca de codigo. Bloquear um PR
     por algo que o autor nao pode consertar e a receita conhecida para o gate
     ser desligado. Vai para o job summary, onde a pessoa ja olha (E.1).

NAO PODER MEDIR NAO E APROVAR. Sem acesso a API o script avisa alto e sai 0 —
fazer o CI depender da disponibilidade da API do GitHub seria pior que a doenca.
Mas um conjunto exigido VAZIO nao e lido como "nada exigido": e lido como falha
de leitura. A diferenca entre "medi e nao ha" e "nao consegui medir" e
exatamente o que este plano existe para nao confundir.

Uso (CI):
    python v2/backend/scripts/check_required_checks.py --branch main

Uso (teste, sem rede):
    python .../check_required_checks.py --repo-root DIR --enforced-from ctx.json

Exit 0 = sem fantasma (avisos podem existir). Exit 1 = fantasma. Exit 2 = uso.

Testes: apps/core/tests/test_check_required_checks.py
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys

for _fluxo in (sys.stdout, sys.stderr):
    try:
        _fluxo.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except (AttributeError, OSError):
        pass


def _jobs(raiz: pathlib.Path) -> tuple[dict[str, str], list[str]]:
    """{context: arquivo}, e a lista de workflows ilegiveis.

    O context que o GitHub publica e o `name:` do job; na ausencia dele, o id.
    Ler com YAML de verdade, nao com grep: a medicao que motivou este script
    errou duas vezes por glob (`*.yml*` nao casa `ci.yaml`, o arquivo com mais
    jobs do repositorio) e por regex de aspas.
    """
    try:
        import yaml
    except ImportError:
        # Falha ALTO, nao pula. Ao contrario da API fora do ar, dependencia
        # ausente e condicao local e consertavel — pular aqui deixaria o gate
        # verde por nao ter rodado, que e o defeito que este plano combate.
        print(
            "ERRO: PyYAML ausente. Este gate le workflow com YAML de verdade porque\n"
            "regex/glob ja errou a medida duas vezes. Instale: pip install pyyaml",
            file=sys.stderr,
        )
        raise SystemExit(2)

    d = raiz / ".github" / "workflows"
    nomes: dict[str, str] = {}
    ilegiveis: list[str] = []
    if not d.is_dir():
        return nomes, ilegiveis

    for p in sorted(list(d.glob("*.yml")) + list(d.glob("*.yaml"))):
        try:
            doc = yaml.safe_load(p.read_text(encoding="utf-8"))
        except Exception:
            # Um workflow quebrado e problema de outro gate (actionlint). Aqui
            # ele so nao pode derrubar a medida nem virar fantasma silencioso.
            ilegiveis.append(p.name)
            continue
        if not isinstance(doc, dict):
            ilegiveis.append(p.name)
            continue
        for jid, job in (doc.get("jobs") or {}).items():
            nome = jid
            if isinstance(job, dict) and isinstance(job.get("name"), str):
                nome = job["name"]
            nomes[nome] = p.name
    return nomes, ilegiveis


def _exigidos_da_api(branch: str) -> set[str] | None:
    """Contexts exigidos, via `gh`. None se nao deu para ler."""
    try:
        r = subprocess.run(
            ["gh", "api", f"repos/:owner/:repo/rules/branches/{branch}"],
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
            encoding="utf-8",
            errors="replace",
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0 or not r.stdout.strip():
        return None
    try:
        regras = json.loads(r.stdout)
    except json.JSONDecodeError:
        return None
    if not isinstance(regras, list):
        return None

    ctx: set[str] = set()
    for regra in regras:
        if not isinstance(regra, dict) or regra.get("type") != "required_status_checks":
            continue
        for c in (regra.get("parameters") or {}).get("required_status_checks") or []:
            if isinstance(c, dict) and c.get("context"):
                ctx.add(c["context"])
    return ctx


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
    ap.add_argument("--branch", default="main")
    ap.add_argument("--enforced-from", help="JSON com a lista de contexts (teste/offline)")
    a = ap.parse_args(argv[1:])

    raiz = pathlib.Path(a.repo_root).resolve()
    if not raiz.is_dir():
        print(f"ERRO: repo-root nao encontrado: {raiz}", file=sys.stderr)
        return 2

    nomes, ilegiveis = _jobs(raiz)
    for nome in ilegiveis:
        print(f"AVISO: workflow ilegivel, fora da medida: {nome}")

    if a.enforced_from:
        try:
            exigidos = set(json.loads(pathlib.Path(a.enforced_from).read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError) as e:
            print(f"ERRO: --enforced-from ilegivel: {e}", file=sys.stderr)
            return 2
    else:
        lidos = _exigidos_da_api(a.branch)
        if lidos is None:
            print()
            print("AVISO: nao consegui ler o ruleset de " f"`{a.branch}` (gh indisponivel ou sem permissao).")
            print("Sem isso nao da para dizer quais checks travam merge — e fazer o CI")
            print("depender da API do GitHub seria pior. Nada foi verificado aqui.")
            return 0
        exigidos = lidos

    # Vazio quase sempre e leitura falhada, nao ausencia de protecao. Tratar como
    # "nada exigido" faria o gate aprovar em silencio justamente quando esta cego.
    if not exigidos:
        print()
        print("AVISO: o ruleset devolveu ZERO contexts exigidos.")
        print("Isso e falha de medida, nao aprovacao — um repositorio com ruleset")
        print("configurado nao devolve lista vazia. Nada foi verificado aqui.")
        return 0

    declarados = {n for n in nomes if n.startswith("[required]")}
    fantasmas = sorted(exigidos - set(nomes))
    rotulo_falso = sorted(declarados - exigidos)

    if rotulo_falso:
        print()
        print("AVISO — jobs que dizem [required] mas o ruleset NAO exige:")
        for n in rotulo_falso:
            print(f"  {n}")
            print(f"      {nomes[n]}")
        print()
        print("O nome informa errado sobre a protecao do repositorio. Corrigir e acao")
        print("de admin no ruleset (adicionar o context) ou tirar o rotulo do nome.")

    resumo = [
        "# Checks obrigatorios",
        "",
        f"**{len(exigidos)}** exigidos pelo ruleset de `{a.branch}` · "
        f"**{len(declarados)}** jobs declaram `[required]` · "
        f"**{len(rotulo_falso)}** rotulados sem serem exigidos.",
        "",
    ]
    if rotulo_falso:
        resumo += ["| job | workflow |", "| --- | --- |"]
        resumo += [f"| `{n}` | `{nomes[n]}` |" for n in rotulo_falso]
        resumo.append("")
    _resumo(resumo)

    if fantasmas:
        print()
        print("BLOQUEIO — contexts exigidos que NENHUM job produz:")
        for n in fantasmas:
            print(f"  {n}")
        print()
        print("Um context exigido que ninguem emite deixa o PR 'Expected' para sempre")
        print("e trava o merge. Renomeie o job de volta, ou tire o context do ruleset.")
        return 1

    print()
    print(
        f"OK {len(exigidos)} context(s) exigido(s), todos com job correspondente. "
        f"{len(rotulo_falso)} rotulo(s) falso(s) — aviso, nao bloqueio."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
