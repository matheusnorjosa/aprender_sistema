#!/usr/bin/env python3
"""Gate de CI (SDD / ADR-017): lint de frontmatter das specs vivas.

Todo doc vivo em `v2/docs/specs/` (specs + INDEX + READMEs de area) deve comecar
com frontmatter YAML contendo, no minimo, `status` e `last_verified` (YYYY-MM-DD).
Falha (exit 1) se faltar campo obrigatorio, a data estiver mal formada ou o
cabecalho nao for YAML valido. `last_verified` com mais de 180 dias gera AVISO
(nao falha).

O cabecalho e lido por `v2/backend/scripts/doc_frontmatter.py`, o leitor unico dos
gates de doc (FER-64); precisa do PyYAML instalado.

Uso: `python scripts/check_doc_frontmatter.py [raiz]` (default v2/docs/specs).
"""

import datetime
import os
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "v2" / "backend" / "scripts"))
import doc_frontmatter  # noqa: E402

ROOT = sys.argv[1] if len(sys.argv) > 1 else "v2/docs/specs"
REQUIRED = ["status", "last_verified"]
DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")

errors = []
warnings = []
today = datetime.date.today()

for dirpath, dirnames, filenames in os.walk(ROOT):
    if "_archive" in dirpath.replace(os.sep, "/").split("/"):
        continue
    for fn in filenames:
        if not fn.endswith(".md"):
            continue
        fp = os.path.join(dirpath, fn)
        rel = fp.replace(os.sep, "/")
        txt = open(fp, encoding="utf-8").read()
        try:
            fields, _ = doc_frontmatter.frontmatter(txt)
        except ValueError as e:
            errors.append(rel + ": " + " ".join(str(e).split()))
            continue
        if not fields:
            errors.append(rel + ": sem frontmatter YAML (--- ... ---)")
            continue
        for req in REQUIRED:
            if not fields.get(req):
                errors.append(rel + ": falta '" + req + "' no frontmatter")
        lv = fields.get("last_verified", "")
        dm = DATE.match(lv)
        if dm:
            d = datetime.date(int(dm.group(1)), int(dm.group(2)), int(dm.group(3)))
            age = (today - d).days
            if age > 180:
                warnings.append(rel + ": last_verified " + lv + " (" + str(age) + "d > 180)")
        elif lv:
            errors.append(rel + ": last_verified '" + lv + "' nao e YYYY-MM-DD")

for w in warnings:
    print("AVISO " + w)

if errors:
    print("X %d problema(s) de frontmatter:" % len(errors))
    for e in errors:
        print("   " + e)
    sys.exit(1)

print("OK frontmatter valido em %s (status + last_verified presentes)." % ROOT)
