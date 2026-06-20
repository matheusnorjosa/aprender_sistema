#!/usr/bin/env python3
"""Gate de CI (SDD / ADR-017): lint de frontmatter das specs vivas.

Todo doc vivo em `v2/docs/specs/` (specs + INDEX + READMEs de area) deve comecar
com frontmatter YAML contendo, no minimo, `status` e `last_verified` (YYYY-MM-DD).
Falha (exit 1) se faltar campo obrigatorio ou a data estiver mal formada.
`last_verified` com mais de 180 dias gera AVISO (nao falha).

Uso: `python scripts/check_doc_frontmatter.py [raiz]` (default v2/docs/specs).
"""
import datetime
import os
import re
import sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "v2/docs/specs"
REQUIRED = ["status", "last_verified"]
FM = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)
FIELD = re.compile(r"^([A-Za-z_]+):\s*(.*)$")
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
        m = FM.match(txt)
        if not m:
            errors.append(rel + ": sem frontmatter YAML (--- ... ---)")
            continue
        fields = {}
        for line in m.group(1).splitlines():
            fm = FIELD.match(line)
            if fm:
                fields[fm.group(1)] = fm.group(2).strip()
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
