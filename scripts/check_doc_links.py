#!/usr/bin/env python3
"""Gate de CI (SDD / ADR-017): links relativos quebrados em docs VIVOS.

Verifica links markdown relativos em `docs/` e `v2/docs/`, ignorando `_archive/`
(histórico imutável, principio 5 do plano SDD). Falha (exit 1) se algum link
relativo apontar para um arquivo que **não existe** ou que **não é rastreado pelo
git** (gitignored — ausente num clone limpo, ex.: `.claude/`, `.env.*`).

Checar contra `git ls-files` faz o resultado local casar com o CI (case-sensitive
+ checkout limpo). Não valida URLs http(s)/mailto, âncoras (#...), nem alvos com
espaço (trechos de código). Uso: `python scripts/check_doc_links.py [raiz ...]`.
"""
import os
import re
import subprocess
import sys

ROOTS = sys.argv[1:] or ["docs", "v2/docs"]
LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
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

if broken:
    print("X %d link(s) relativo(s) quebrado(s)/nao-rastreado(s) em docs vivos:" % len(broken))
    for b in sorted(set(broken)):
        print("   " + b)
    sys.exit(1)

print("OK 0 links relativos quebrados em docs vivos (%s, exceto _archive)." % ", ".join(ROOTS))
