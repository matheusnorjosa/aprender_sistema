#!/usr/bin/env python3
"""Gate de CI (SDD / ADR-017): links relativos quebrados em docs VIVOS.

Verifica links markdown relativos em `docs/` e `v2/docs/`, ignorando `_archive/`
(histórico imutável, principio 5 do plano SDD). Falha (exit 1) se algum link
relativo apontar para um arquivo que **não existe** ou que **não é rastreado pelo
git** (gitignored — ausente num clone limpo, ex.: `.claude/`, `.env.*`).

Checar contra `git ls-files` faz o resultado local casar com o CI (case-sensitive
+ checkout limpo). Não valida URLs http(s)/mailto, âncoras (#...), nem alvos com
espaço (trechos de código). Uso: `python scripts/check_doc_links.py [raiz ...]`.

F.5 — AVISA (nunca bloqueia) sobre caminho escrito em CRASE que não resolve.
`` `v2/docs/X.md` `` parece referência mas não é link, então a regex acima nunca
o vê: foi assim que 11 arquivos SEC ficaram inalcançáveis com este gate verde.
Só conta o que tem forma de caminho (exige `/`) — nome solto em crase é prosa
nomeando um documento. Medido em 2026-08-25: 22 de 211 não resolvem, e só ~11
exigem ação; o resto são relatórios datados e declarações históricas corretas.
50% de precisão fica abaixo da barra usada para bloquear nos outros detectores.
"""
import os
import re
import subprocess
import sys

ROOTS = sys.argv[1:] or ["docs", "v2/docs"]
LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
# F.5: so conta o que tem FORMA de caminho (exige uma barra). Nome solto em
# crase — «ver `ACHADOS_REAIS.md`» — e prosa nomeando um doc, nao referencia:
# incluir isso dava 164 achados de 610, quase tudo ruido.
CRASE = re.compile(r"`([A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+\.md)`")
PREFIXOS = ("", "docs/", "v2/", "v2/docs/", "v2/docs/specs/", "v2/backend/", "v2/frontend/", "v2/infra/")
SKIP_DIRS = {
    ".git", "node_modules", ".venv", "venv", "site", "__pycache__",
    "graphify-out", "dist", "build", "_archive",
}

# Conjunto de arquivos rastreados pelo git (caminhos relativos à raiz, forward slash).
try:
    _out = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True, check=True
    ).stdout
    TRACKED = set(_out.replace("\\", "/").splitlines())
except Exception:
    TRACKED = set()  # sem git -> cai para checagem só de existência


def is_broken(abspath):
    if not os.path.exists(abspath):
        return True
    if os.path.isdir(abspath):
        return False  # diretórios não aparecem em git ls-files
    if TRACKED:
        rel = os.path.relpath(abspath).replace(os.sep, "/")
        return rel not in TRACKED
    return False


broken = []
crase = []
for root in ROOTS:
    if not os.path.isdir(root):
        continue
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if not fn.endswith(".md"):
                continue
            fp = os.path.join(dirpath, fn)
            try:
                txt = open(fp, encoding="utf-8").read()
            except OSError:
                continue
            for m in LINK.finditer(txt):
                tgt = m.group(1).strip()
                if tgt.startswith(("http://", "https://", "mailto:", "#", "<")):
                    continue
                if "://" in tgt:
                    continue
                path_only = tgt.split("#")[0].strip()
                if not path_only or " " in path_only:
                    continue
                abspath = os.path.normpath(os.path.join(dirpath, path_only))
                if is_broken(abspath):
                    broken.append(fp.replace(os.sep, "/") + " -> " + tgt)

            for m in CRASE.finditer(txt):
                ref = m.group(1)
                cands = [os.path.join(pre, ref) for pre in PREFIXOS]
                cands.append(os.path.join(dirpath, ref))
                if not any(os.path.exists(os.path.normpath(c)) for c in cands):
                    crase.append(fp.replace(os.sep, "/") + " -> `" + ref + "`")

if crase:
    # F.5 — REFERENCIA POR CAMINHO EM CRASE NAO E LINK. `v2/docs/X.md` escrito em
    # crase parece referencia e nenhum checador olha: a regex acima so casa
    # `[texto](alvo)`. Foi assim que 11 arquivos SEC ficaram inalcancaveis com o
    # gate verde.
    #
    # AVISA, nao bloqueia. Medido em 2026-08-25: 211 referencias com forma de
    # caminho em doc vivo, 22 nao resolvem, ~11 exigem acao. O resto sao
    # relatorios datados (candidatos a _archive) e declaracoes historicas
    # CORRETAS — inclusive uma no plano deste trabalho, afirmando com razao que
    # `graphify-out/wiki/index.md` nao existe. 50% de precisao esta abaixo da
    # barra que os outros detectores usam para bloquear.
    print("AVISO %d caminho(s) em crase que nao resolve(m) — parecem referencia," % len(set(crase)))
    print("      mas nenhum checador os segue, porque nao sao link:")
    for c in sorted(set(crase)):
        print("   " + c)
    print()

if broken:
    print("X %d link(s) relativo(s) quebrado(s)/nao-rastreado(s) em docs vivos:" % len(broken))
    for b in sorted(set(broken)):
        print("   " + b)
    sys.exit(1)

print("OK 0 links relativos quebrados em docs vivos (%s, exceto _archive)." % ", ".join(ROOTS))
if crase:
    print("   (%d caminho(s) em crase avisados acima; aviso, nao bloqueio)" % len(set(crase)))
