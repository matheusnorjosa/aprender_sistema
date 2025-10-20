import csv
import os
from collections import defaultdict

IN_CSV = "out_formulas/formulas_references.csv"
OUT_MMD = "out_formulas/formulas_graph.mmd"

# nó = "file|sheet"; aresta: sheet -> ref_sheet (agregada)
edges = defaultdict(int)

with open(IN_CSV, encoding="utf-8-sig") as f:
    r = csv.DictReader(f)
    for row in r:
        src = f"{row['file']}|{row['sheet']}"
        dst = row["ref_sheet"] or "(mesma_aba)"
        edges[(src, dst)] += 1

with open(OUT_MMD, "w", encoding="utf-8") as f:
    f.write("graph LR\n")
    for (src, dst), w in edges.items():
        f.write(f'  "{src}" -->|{w}| "{dst}"\n')

print("[OK] Mermaid salvo em", OUT_MMD)
