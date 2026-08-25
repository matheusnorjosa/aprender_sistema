#!/usr/bin/env python
"""
Mede o drift das specs vivas ancorando em COMMIT, nao em data. Relata; nao barra.

POR QUE COMMIT E NAO DATA (Fase B.1 do PLAN_doc_drift_2026-08-25).
`git log --since=<data>` usa approxidate, que resolve contra a hora atual: a
mesma pergunta responde diferente as 08h e as 20h, e `--since` inclui o proprio
dia — entao a spec corrigida hoje aparece "em drift" no PR que a corrigiu. Ancora
em SHA nao tem hora, nao tem fuso e nao tem ambiguidade de mesmo dia. O repo ja
tinha inventado isso: `ACHADOS_REAIS.md` carrega `audit_baseline: 90f6a048`.

POR QUE RELATORIO E NAO PORTAO (Fase B.3).
Medido em 2026-08-24: 21 de 21 specs que declaram `sources_of_truth` estao em
drift, e 95% das ancoradas recebem commit novo em 7 dias. Um gate que barra sobre
"existe drift" barra sempre, e some na primeira semana. Drift em repouso e
metrica; o portao e por PR e limitado ao que aquele PR tocou —
`check_doc_impact.py`, Fase C.

A UNICA SAIDA != 0 E NAO PODER MEDIR (Fase B.2).
Em repositorio raso `git log` ve um commit e responde "sem drift": verde por
falta de dado, que e o proprio diagnostico deste plano se reproduzindo dentro da
correcao. Cinto e suspensorio — `fetch-depth: 0` no workflow E este guard, porque
config some em refactor e codigo com teste, nao.

TRES ESTADOS:
  OK          nenhum commit posterior a ancora tocou as fontes declaradas
  EM DRIFT    N commits posteriores tocaram as fontes
  NAO MEDIVEL sem `sources_of_truth` — "nao sei", nunca "esta ok"

As 5 specs "verdes" da auditoria eram exatamente as 5 que nao declaravam nada.
Confundir ausencia de medida com aprovacao e como o aviso de 180 dias virou
decoracao.

DUAS PROVENIENCIAS DE ANCORA, e a saida sempre diz qual:
  declarada  `verified_at_commit` no frontmatter — alguem conferiu naquele commit
  inferida   ultimo commit que tocou a propria spec

A inferida existe porque a alternativa era pior. Preencher `verified_at_commit`
nos 22 arquivos de uma vez seria escrever "verificado no commit X" para
verificacao que nunca houve — a alegacao sem lastro que esta auditoria existe
para cacar. O ultimo commit da spec e fato do git e responde a pergunta util (o
codigo mudou desde que este doc foi mexido?), desde que nao se disfarce da outra.
Declarada vence inferida sempre.

Uso:
    python scripts/doc_drift_report.py [--repo-root DIR]
    python scripts/doc_drift_report.py --format=gh-summary [--summary-file F]

Exit 0 = mediu (com ou sem drift). Exit 1 = nao deu para medir. Exit 2 = uso.

Testes: apps/core/tests/test_doc_drift.py
"""

from __future__ import annotations

import argparse
import os
import pathlib
import subprocess
import sys

# O console do Windows abre em cp1252 e este repo tem commit com `→`, acento e
# emoji no assunto — imprimir um deles derruba o script com UnicodeEncodeError.
# Um relatorio que so roda no CI nao serve para quem precisa dele antes do PR.
for _fluxo in (sys.stdout, sys.stderr):
    try:
        _fluxo.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except (AttributeError, OSError):
        pass

# Documentacao viva. `_archive/` e historico e nao se corrige (ADR-017 item 5).
RAIZES_DOC = ["v2/docs", "docs", "specs"]
IGNORA_DOC = ("_archive", "worktrees", "node_modules")

# Mesma regra do check_doc_impact: status que declara o doc como registro, nao
# como contrato vigente. Medir drift neles produz ruido por construcao.
STATUS_FORA = {"historical", "stale", "superseded", "deprecated"}


def _git(args: list[str], cwd: pathlib.Path) -> tuple[int, str]:
    try:
        r = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
            encoding="utf-8",
            errors="replace",
        )
        return r.returncode, r.stdout
    except (OSError, subprocess.SubprocessError):
        return 1, ""


def _frontmatter(texto: str) -> tuple[dict[str, str], list[str]]:
    """Le campos escalares e a lista `sources_of_truth`.

    Escrito a mao de proposito: o parser do `check_doc_frontmatter.py` usa
    `^([A-Za-z_]+):\\s*(.*)$`, que casa `sources_of_truth:` com valor VAZIO e
    descarta os itens `  - caminho` abaixo. Quem confiasse nele leria toda spec
    como se nao declarasse fonte nenhuma — e toda spec ficaria "verde".
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
        if ln.startswith((" ", "\t")) and ln.strip().startswith("- "):
            if dentro_lista:
                fontes.append(ln.strip()[2:].strip().strip("`\"'"))
            continue
        dentro_lista = False
        if ":" not in ln:
            continue
        chave, _, valor = ln.partition(":")
        chave = chave.strip()
        if not chave or not chave.replace("_", "").isalnum():
            continue
        valor = valor.strip()
        if chave == "sources_of_truth":
            dentro_lista = True
            continue
        campos[chave] = valor
    return campos, fontes


def _docs_vivos(raiz: pathlib.Path):
    for base in RAIZES_DOC:
        d = raiz / base
        if not d.is_dir():
            continue
        for p in sorted(d.rglob("*.md")):
            rel = p.relative_to(raiz).as_posix()
            if any(x in rel for x in IGNORA_DOC):
                continue
            yield p, rel


def _e_raso(raiz: pathlib.Path) -> bool:
    rc, out = _git(["rev-parse", "--is-shallow-repository"], raiz)
    return rc == 0 and out.strip() == "true"


def _drift(raiz: pathlib.Path, sha: str, fontes: list[str]) -> tuple[int, list[str]]:
    """Commits depois de `sha` que tocaram `fontes`. Sem relogio em lugar nenhum."""
    rc, out = _git(
        ["log", "--format=%h %s", f"{sha}..HEAD", "--", *fontes],
        raiz,
    )
    if rc != 0:
        return -1, []
    linhas = [x for x in out.split("\n") if x.strip()]
    return len(linhas), linhas


def _linha_tabela(*celulas: str) -> str:
    return "| " + " | ".join(celulas) + " |"


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--format", dest="formato", choices=["texto", "gh-summary"], default="texto")
    ap.add_argument(
        "--summary-file",
        help="destino do gh-summary. Default: $GITHUB_STEP_SUMMARY.",
    )
    a = ap.parse_args(argv[1:])

    raiz = pathlib.Path(a.repo_root).resolve()
    if not raiz.is_dir():
        print(f"ERRO: repo-root nao encontrado: {raiz}", file=sys.stderr)
        return 2

    rc, _ = _git(["rev-parse", "--git-dir"], raiz)
    if rc != 0:
        print(f"ERRO: {raiz} nao e um repositorio git — sem historico nao ha o que medir.", file=sys.stderr)
        return 1

    if _e_raso(raiz):
        print(
            "ERRO: repositorio RASO (shallow). `git log` aqui ve um punhado de commits e\n"
            "responderia 'sem drift' por falta de dado — que e exatamente o defeito que\n"
            "este relatorio existe para medir. Use `fetch-depth: 0` no checkout.",
            file=sys.stderr,
        )
        return 1

    em_drift: list[tuple[str, int, list[str], str]] = []
    ok: list[tuple[str, str]] = []
    nao_medivel: list[tuple[str, str]] = []
    nao_resolvem: list[tuple[str, str]] = []

    for caminho, rel in _docs_vivos(raiz):
        try:
            texto = caminho.read_text(encoding="utf-8")
        except OSError:
            continue
        campos, fontes = _frontmatter(texto)
        if not campos:
            continue  # nao e doc SDD; fora de escopo
        if campos.get("status", "").lower() in STATUS_FORA:
            continue

        if not fontes:
            nao_medivel.append((rel, "sem fontes (`sources_of_truth` ausente ou vazio)"))
            continue

        # Entrada que nao e caminho mede NADA e nao reclama: passada ao `git log`
        # como pathspec, simplesmente nao casa, e a spec aparece "sem drift" por
        # malformacao em vez de por estar em dia. Medido em 2026-08-25: 6 de 303
        # entradas nao resolvem — tres sao frases em prosa dentro da lista do
        # proprio arbitro de defeitos, tres sao caminho com anotacao entre
        # parenteses.
        #
        # MAS "nao existe no disco" NAO basta como criterio, e o teste de
        # renomeacao provou isso derrubando a primeira versao desta checagem:
        # fonte renomeada e exatamente o caso em que o caminho declarado sumiu — e
        # ai a ausencia E o sinal de drift, nao ruido. O discriminador e o mesmo
        # do gate da camada de instrucao: se o git ja conheceu o caminho, mede;
        # se nunca viu, nao e caminho.
        vivas: list[str] = []
        for f in fontes:
            if (raiz / f).exists():
                vivas.append(f)
                continue
            rc_f, out_f = _git(["log", "--all", "-1", "--format=%h", "--", f], raiz)
            if rc_f == 0 and out_f.strip():
                vivas.append(f)  # existiu e sumiu: e drift, e o git sabe contar
            else:
                nao_resolvem.append((rel, f))
        if not vivas:
            nao_medivel.append((rel, f"nenhuma das {len(fontes)} entradas de `sources_of_truth` resolve"))
            continue
        fontes = vivas

        sha = campos.get("verified_at_commit", "").strip().strip("`\"'")
        proveniencia = "declarada"
        if sha:
            rc, _ = _git(["cat-file", "-e", f"{sha}^{{commit}}"], raiz)
            if rc != 0:
                nao_medivel.append((rel, f"ancora declarada `{sha}` nao existe neste historico"))
                continue
        else:
            rc, out = _git(["log", "-1", "--format=%H", "--", rel], raiz)
            sha = out.strip()
            proveniencia = "inferida"
            if rc != 0 or not sha:
                nao_medivel.append((rel, "sem ancora declarada e sem historico proprio"))
                continue

        n, commits = _drift(raiz, sha, fontes)
        if n < 0:
            nao_medivel.append((rel, f"`git log {sha[:8]}..HEAD` falhou"))
        elif n == 0:
            ok.append((rel, proveniencia))
        else:
            em_drift.append((rel, n, commits, proveniencia))

    em_drift.sort(key=lambda t: (-t[1], t[0]))
    total = len(em_drift) + len(ok) + len(nao_medivel)

    nao_resolvem.sort()

    if a.formato == "gh-summary":
        destino = a.summary_file or os.environ.get("GITHUB_STEP_SUMMARY")
        md = _monta_summary(em_drift, ok, nao_medivel, nao_resolvem, total)
        if destino:
            with open(destino, "a", encoding="utf-8") as fh:
                fh.write(md)
        else:
            print(md)
        # A tabela vai para o summary; o stdout continua sendo o log do job.
        _imprime_texto(em_drift, ok, nao_medivel, nao_resolvem, total)
        return 0

    _imprime_texto(em_drift, ok, nao_medivel, nao_resolvem, total)
    return 0


def _imprime_texto(
    em_drift: list[tuple[str, int, list[str], str]],
    ok: list[tuple[str, str]],
    nao_medivel: list[tuple[str, str]],
    nao_resolvem: list[tuple[str, str]],
    total: int,
) -> None:
    if em_drift:
        print("EM DRIFT — specs cujas fontes mudaram depois da ancora:")
        for rel, n, commits, prov in em_drift:
            print(f"  {rel}")
            print(f"      {n} commit(s) depois da ancora ({prov})")
            for c in commits[:3]:
                print(f"        {c}")
            if n > 3:
                print(f"        ... e mais {n - 3}")
        print()

    if nao_resolvem:
        print("FONTE QUE NAO RESOLVE — entrada de sources_of_truth que nao e caminho:")
        for rel, f in nao_resolvem:
            print(f"  {rel}")
            print(f"      {f}")
        print("  Passada ao git log como pathspec, nao casa nada: a spec mede menos")
        print("  do que declara, e o silencio parece 'sem drift'.")
        print()

    if nao_medivel:
        print("NAO MEDIVEL — nao e 'sem drift', e 'nao da para saber':")
        for rel, motivo in nao_medivel:
            print(f"  {rel}")
            print(f"      {motivo}")
        print()

    for rel, prov in ok:
        print(f"OK {rel} — 0 commit desde a ancora ({prov})")

    inferidas = sum(1 for t in em_drift if t[3] == "inferida") + sum(1 for t in ok if t[1] == "inferida")
    print()
    print(f"{total} doc(s) SDD: {len(em_drift)} em drift, {len(ok)} sem drift, " f"{len(nao_medivel)} nao medivel.")
    if inferidas:
        print(
            f"{inferidas} com ancora INFERIDA do ultimo commit da propria spec — "
            "mede mudanca de codigo, nao atesta conferencia."
        )
    print("Relatorio, nao portao: drift sozinho nunca reprova (Fase B.3 do plano).")


def _monta_summary(
    em_drift: list[tuple[str, int, list[str], str]],
    ok: list[tuple[str, str]],
    nao_medivel: list[tuple[str, str]],
    nao_resolvem: list[tuple[str, str]],
    total: int,
) -> str:
    linhas = [
        "# Drift das specs vivas",
        "",
        f"**{len(em_drift)}** em drift · **{len(ok)}** sem drift · "
        f"**{len(nao_medivel)}** nao medivel · {total} doc(s) SDD.",
        "",
        "Medido por ancora de commit, nao por data — `--since` usa approxidate e "
        "responde diferente conforme a hora do dia.",
        "",
        "Ancora **declarada** e `verified_at_commit` no frontmatter: alguem conferiu "
        "naquele commit. Ancora **inferida** e o ultimo commit da propria spec: mede "
        "mudanca de codigo, nao atesta conferencia.",
        "",
    ]

    if em_drift:
        linhas += [
            "## Em drift",
            "",
            _linha_tabela("spec", "commits desde a ancora", "ancora", "mais recente"),
            _linha_tabela("---", "---:", "---", "---"),
        ]
        for rel, n, commits, prov in em_drift:
            recente = commits[0] if commits else ""
            linhas.append(_linha_tabela(f"`{rel}`", str(n), prov, f"`{recente}`"))
        linhas.append("")

    if nao_medivel:
        linhas += [
            "## Nao medivel",
            "",
            "Ausencia de medida nao e aprovacao — as specs 'verdes' da auditoria "
            "eram justamente as que nao declaravam nada.",
            "",
            _linha_tabela("doc", "por que"),
            _linha_tabela("---", "---"),
        ]
        for rel, motivo in nao_medivel:
            linhas.append(_linha_tabela(f"`{rel}`", motivo))
        linhas.append("")

    if ok:
        linhas += ["## Sem drift", "", *[f"- `{rel}` ({prov})" for rel, prov in ok], ""]

    return "\n".join(linhas) + "\n"


if __name__ == "__main__":
    sys.exit(main(sys.argv))
