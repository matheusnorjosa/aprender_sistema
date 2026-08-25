#!/usr/bin/env python
"""
Mantem a documentacao viva: liga o que o PR muda a doc que descreve aquilo.

PROBLEMA MEDIDO (auditoria de 2026-08-24, 450 arquivos; contagens conferidas em
2026-08-25 contra o HEAD d8e64714 — reproduza antes de citar, elas crescem):
  - 92,9% dos commits `fix(...)` nao tocam um unico .md (8 de 113 desde 2026-06-01).
  - O arbitro de defeitos ficou 74 commits sem atualizacao, 27 deles fixes
    (intervalo 9631ef60..HEAD), e nenhum deles tocou um .md.
  - 39 issues FECHADAS sao citadas como abertas em 66 lugares da doc viva.
  - A regra ja estava escrita, em negrito, dentro do proprio arbitro. O modo de
    falha nao e ignorancia — e ausencia de enforcement.

DOIS DETECTORES, calibrados pela precisao de cada um:

  1. ISSUE RESOLVIDA -> DOC QUE A CITA          [BLOQUEIA]
     Um commit com `Closes #N` resolve algo. Se um doc vivo descreve #N como
     defeito aberto, ele passou a mentir naquele instante. Preciso e raro.

  2. CODIGO ALTERADO -> SPEC QUE O DECLARA      [AVISA]
     Toda spec declara `sources_of_truth`. Se o PR toca um desses arquivos, a
     spec ficou suspeita por construcao. Medido: dispara em 60% dos commits,
     media de 2,6 specs. Bloquear nisso trava o repositorio e o gate e revertido.

POR QUE NAO ANCORAR SO NA ISSUE: `Closes #N` aparece em apenas 27,7% dos commits
de fix, e as citacoes `Mxx-yy` cairam a zero quando a frente virou frontend. Um
gate ancorado so ai fica verde por vacuidade.

SAIDA DE ESCAPE, deliberada: `doc-nao-afetada: <caminho> — <justificativa>` no
corpo do PR. Sem ela o gate vira imposto e e contornado; com ela, a decisao de
"nao afeta" fica registrada e revisavel em vez de tacita. A justificativa e
obrigatoria — waiver vazio e o comeco da erosao.

Uso (CI):
    python scripts/check_doc_impact.py --range origin/main...HEAD --pr-body-file corpo.txt

Uso (teste/local, sem git):
    python scripts/check_doc_impact.py --repo-root DIR \
        --changed-files-from f.txt --commit-messages-from c.txt --pr-body-file b.txt

Exit 0 = sem bloqueio (avisos podem existir). Exit 1 = bloqueio. Exit 2 = uso.

Testes: apps/core/tests/test_check_doc_impact.py
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import subprocess
import sys

# Roda como script solto no runner, entao o proprio diretorio entra no sys.path.
# `doc_frontmatter` e o SSOT de como se le uma spec — dois parsers respondendo
# diferente sobre o mesmo arquivo e o gerador de drift que este gate combate.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import doc_frontmatter  # noqa: E402

# Verbo que declara resolucao. Sem verbo, a mencao e contexto — avisa, nao bloqueia.
RESOLVE = re.compile(r"(?i)\b(clos(?:e|es|ed)|fix(?:e[sd])?|resolv(?:e|es|ed))\s+#(\d{2,6})\b")
MENCAO = re.compile(r"#(\d{2,6})\b")
ACHADO = re.compile(r"\bM\d{2}-\d{2}\b")

# Documentacao viva. _archive e historico e nao se corrige (ADR-017 item 5).
RAIZES_DOC = ["v2/docs", "docs", "specs"]
IGNORA_DOC = ("_archive", "worktrees", "node_modules")

WAIVER = re.compile(r"(?im)^\s*doc[- ]nao[- ]afetada\s*:\s*(?P<caminho>\S+)\s*(?:[—–-]{1,2}\s*(?P<motivo>.+))?$")


def _rotula(ids: list[str]) -> str:
    """Issue leva `#`; achado nao.

    Esta saida e lida por gente e colada em PR. `#M26-03` fabrica uma referencia
    que nao resolve em lugar nenhum — o GitHub nem linka.
    """
    return ", ".join("#" + i if i.isdigit() else i for i in ids)


def _le(p: str | None) -> str:
    if not p:
        return ""
    try:
        return pathlib.Path(p).read_text(encoding="utf-8")
    except OSError:
        return ""


def _git(args: list[str], cwd: pathlib.Path) -> str:
    try:
        r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False, timeout=120)
        return r.stdout if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


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


def _status(texto: str) -> str:
    return doc_frontmatter.status(texto)


def _sources_of_truth(texto: str) -> list[str]:
    return doc_frontmatter.frontmatter(texto)[1]


def _sot_encolheu(raiz: pathlib.Path, base: str, rel: str, texto_atual: str) -> list[str]:
    """Itens que sumiram do `sources_of_truth` desta spec em relacao a `base`.

    B.4 — O INCENTIVO PERVERSO. As 21 specs que declaram `sources_of_truth` estao
    21/21 em drift; as unicas verdes eram as que nao declaravam nada. A saida
    barata, entao, e apagar linhas da lista: o drift some sem que uma linha de
    doc fique correta. Encolher pode ser legitimo (arquivo removido, escopo
    dividido) — por isso exige justificativa, nao proibicao.
    """
    antes = _git(["show", f"{base}:{rel}"], raiz)
    if not antes:
        return []  # spec nova neste PR: nao ha do que encolher
    _, fontes_antes = doc_frontmatter.frontmatter(antes)
    _, fontes_agora = doc_frontmatter.frontmatter(texto_atual)
    return sorted(set(fontes_antes) - set(fontes_agora))


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--range", dest="intervalo")
    ap.add_argument("--changed-files-from")
    ap.add_argument("--commit-messages-from")
    ap.add_argument("--pr-body-file")
    ap.add_argument(
        "--summary-file",
        help="destino do resumo em Markdown. Default: $GITHUB_STEP_SUMMARY.",
    )
    a = ap.parse_args(argv[1:])

    raiz = pathlib.Path(a.repo_root).resolve()
    if not raiz.is_dir():
        print(f"ERRO: repo-root nao encontrado: {raiz}", file=sys.stderr)
        return 2

    base = ""
    if a.changed_files_from:
        alterados = [x.strip() for x in _le(a.changed_files_from).split("\n") if x.strip()]
        mensagens = _le(a.commit_messages_from)
    elif a.intervalo:
        alterados = [x.strip() for x in _git(["diff", "--name-only", a.intervalo], raiz).split("\n") if x.strip()]
        mensagens = _git(["log", "--format=%B", a.intervalo], raiz)
        # B.4 compara a lista declarada contra a versao da base. Com `...` a base
        # e o merge-base, que e o mesmo ponto que o diff acima usa.
        base = a.intervalo.split("...")[0].split("..")[0].strip()
    else:
        print("ERRO: informe --range ou --changed-files-from.", file=sys.stderr)
        return 2

    corpo = _le(a.pr_body_file)
    texto_pr = mensagens + "\n" + corpo
    tocados = {x.replace("\\", "/") for x in alterados}

    # Waiver so vale FORA de comentario HTML: escondido num <!-- --> ele nao e
    # revisavel, e a razao inteira de existir e ser revisavel. Remover os
    # comentarios antes de procurar tambem impede que o texto-exemplo do
    # pull_request_template.md vire waiver automatico.
    corpo_visivel = re.sub(r"(?s)<!--.*?-->", "", corpo)

    PLACEHOLDER = re.compile(r"(?i)^(por que nao afeta|caminho/do/doc|<[^>]+>|\.{3,}|xxx+)$")

    waivers: dict[str, str] = {}
    sem_motivo: list[str] = []
    for m in WAIVER.finditer(corpo_visivel):
        cam = m.group("caminho").replace("\\", "/")
        motivo = (m.group("motivo") or "").strip()
        if len(motivo) < 10 or PLACEHOLDER.match(motivo) or PLACEHOLDER.match(cam):
            sem_motivo.append(cam)
        else:
            waivers[cam] = motivo

    resolvidas = {m.group(2) for m in RESOLVE.finditer(texto_pr)}
    mencionadas = {m.group(1) for m in MENCAO.finditer(texto_pr)} - resolvidas

    # Um ID Mxx-yy citado no PR NAO significa que o achado foi resolvido — a
    # propria auditoria registra commits que citam ID como contexto. Medido:
    # tratar toda mencao como resolucao produziu falso positivo em commit real
    # (ac418a50 citava 4 IDs sem resolver nenhum). So conta como resolucao
    # quando o assunto e de fix E o ID aparece nele.
    achados: set[str] = set()
    for linha in mensagens.split("\n"):
        if re.match(r"^\s*(fix|hotfix)\s*[(:]", linha, re.I):
            achados |= set(ACHADO.findall(linha))
    achados_mencionados = set(ACHADO.findall(texto_pr)) - achados

    bloqueios: list[tuple[str, str]] = []
    avisos: list[tuple[str, str]] = []

    for p, rel in _docs_vivos(raiz):
        try:
            texto = p.read_text(encoding="utf-8")
        except OSError:
            continue

        # Doc que se declara historico nao se corrige (ADR-017 item 5). Vale
        # tambem fora de _archive: a auditoria de 2026-07-17 mora em audits/ e
        # abre com "Registro historico — nao e a fila de trabalho".
        if _status(texto) in {"historical", "stale"}:
            continue

        refs_doc = set(MENCAO.findall(texto)) | set(ACHADO.findall(texto))

        # detector 1 — issue resolvida citada pelo doc
        duras = sorted((resolvidas | achados) & refs_doc)
        if duras and rel not in tocados:
            if rel in waivers:
                pass
            elif rel in sem_motivo:
                bloqueios.append((rel, f"waiver sem justificativa (>=10 caracteres) para {_rotula(duras)}"))
            else:
                bloqueios.append((rel, f"o PR resolve {_rotula(duras)} e este doc cita, mas nao foi atualizado"))

        # detector 1b — mencao sem verbo de resolucao: so avisa
        brandas = sorted((mencionadas | achados_mencionados) & refs_doc)
        if brandas and rel not in tocados and not duras:
            avisos.append((rel, f"cita {_rotula(brandas)}, mencionado no PR sem verbo de resolucao"))

        # detector 2 — indice reverso: so avisa
        sot = _sources_of_truth(texto)
        atingidos = [s for s in sot if s.replace("\\", "/") in tocados]
        if atingidos and rel not in tocados:
            amostra = ", ".join(atingidos[:3]) + ("…" if len(atingidos) > 3 else "")
            avisos.append((rel, f"declara em sources_of_truth arquivo que o PR alterou: {amostra}"))

        # detector 3 (B.4) — a lista encolheu: BLOQUEIA sem justificativa.
        # Apagar linhas do sources_of_truth faz o drift sumir sem corrigir uma
        # linha de doc. E a saida barata que a Fase B criaria se ninguem olhasse.
        if base and rel in tocados:
            sumiram = _sot_encolheu(raiz, base, rel, texto)
            if sumiram:
                amostra = ", ".join(sumiram[:3]) + ("…" if len(sumiram) > 3 else "")
                if rel in waivers:
                    pass
                elif rel in sem_motivo:
                    bloqueios.append((rel, f"waiver sem justificativa para sources_of_truth que encolheu: {amostra}"))
                else:
                    bloqueios.append(
                        (
                            rel,
                            f"sources_of_truth perdeu {len(sumiram)} item(ns) — {amostra}. "
                            "Encolher a lista faz o drift sumir sem corrigir a doc",
                        )
                    )

    # E.2 — AUDITAR O USO DO CONTORNO. O waiver e necessario (sem saida de
    # escape o gate vira imposto e e contornado por fora) E e o ponto de erosao.
    # A contagem vai para o job summary porque, se subir de forma sustentada,
    # quem esta errado e o GATE, nao a pessoa. Metrica sem lugar onde alguem
    # olhe e decoracao — foi assim que o aviso de 180 dias morreu.
    #
    # So escreve a secao quando ha uso: aviso sem acao e ruido, e ruido treina
    # a ignorar o gate.
    destino = a.summary_file or os.environ.get("GITHUB_STEP_SUMMARY")
    if destino and (waivers or sem_motivo):
        linhas = [
            "## Documentacao viva — uso do waiver",
            "",
            f"Este PR usou **{len(waivers)}** waiver(s) justificado(s)"
            + (f" e **{len(sem_motivo)}** sem justificativa." if sem_motivo else "."),
            "",
            "Se este numero subir de forma sustentada entre PRs, o gate esta errado —",
            'nao a pessoa. O contorno existe para a decisao de "nao afeta" ficar',
            "registrada e revisavel, em vez de tacita.",
            "",
            "| doc dispensado | justificativa |",
            "| --- | --- |",
        ]
        for cam, motivo in sorted(waivers.items()):
            linhas.append(f"| `{cam}` | {motivo} |")
        for cam in sorted(sem_motivo):
            linhas.append(f"| `{cam}` | **sem justificativa — nao vale** |")
        linhas.append("")
        try:
            with open(destino, "a", encoding="utf-8") as fh:
                fh.write(os.linesep.join(linhas) + os.linesep)
        except OSError:
            pass

    if avisos:
        print("AVISO — specs e docs que o PR provavelmente afeta:")
        for rel, por in sorted(set(avisos)):
            print(f"  {rel}\n      {por}")
        print()

    if bloqueios:
        print("BLOQUEIO — documentacao viva que passou a mentir com este PR:")
        for rel, por in sorted(set(bloqueios)):
            print(f"  {rel}\n      {por}")
        print()
        print("Resolva de UMA destas formas:")
        print("  1. atualize o documento neste mesmo PR; ou")
        print("  2. declare no corpo do PR, com justificativa de verdade:")
        print("     doc-nao-afetada: <caminho> — <por que nao afeta>")
        print()
        print("A linha precisa ficar VISIVEL no corpo: waiver dentro de <!-- --> nao")
        print("conta, porque a razao de existir e ser revisavel. Justificativa vazia,")
        print("curta ou igual ao texto-exemplo do template tambem e recusada — e por")
        print("ali que este tipo de gate morre.")
        return 1

    print(f"OK nenhuma documentacao viva ficou desatualizada por este PR ({len(tocados)} arquivo(s) no diff).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
