#!/usr/bin/env python
"""
Script para construir catálogo de Google Sheets a partir do repositório.
Busca URLs de export CSV em todos os arquivos e cria catálogo estruturado.
"""
import json
import pathlib
import re


def main():
    print("🔍 Construindo catálogo de Google Sheets...")

    root = pathlib.Path(".")
    targets = []

    # Padrão para URLs de export CSV do Google Sheets
    pattern = r"https://docs\.google\.com/spreadsheets/d/([\w-]+)/export\?format=csv&gid=(\d+)"

    # Buscar em todos os arquivos (exceto node_modules e arquivos muito grandes)
    for p in root.rglob("*"):
        if (
            p.is_file()
            and p.stat().st_size < 2_000_000
            and "node_modules" not in str(p)
            and ".git" not in str(p)
        ):

            try:
                content = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            # Buscar matches
            for match in re.finditer(pattern, content):
                targets.append(
                    {"file": str(p), "sheet_id": match.group(1), "gid": match.group(2)}
                )

    # Normalizar e deduplicar
    seen = set()
    out = []

    for entry in targets:
        key = (entry["sheet_id"], entry["gid"])
        if key in seen:
            continue
        seen.add(key)
        out.append(entry)

    # Salvar catálogo
    catalog_path = pathlib.Path("ingestao/gsheets_catalog.json")
    catalog_data = {
        "entries": out,
        "total_entries": len(out),
        "generated_at": "2025-10-08T00:00:00Z",
        "description": "Catálogo automático de Google Sheets encontrados no repositório",
    }

    catalog_path.write_text(
        json.dumps(catalog_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"✓ Catálogo gerado: {catalog_path}")
    print(f"  Total de entradas: {len(out)}")

    if out:
        print("\n📋 Entradas encontradas:")
        for i, entry in enumerate(out[:10], 1):  # Mostrar primeiras 10
            print(f"  {i}. {entry['sheet_id']} (gid: {entry['gid']}) - {entry['file']}")

        if len(out) > 10:
            print(f"  ... e mais {len(out) - 10} entradas")
    else:
        print("  ⚠ Nenhuma URL de Google Sheets encontrada")
        print("  💡 Dica: Adicione URLs no formato:")
        print(
            "     https://docs.google.com/spreadsheets/d/SHEET_ID/export?format=csv&gid=GID"
        )

    return 0


if __name__ == "__main__":
    exit(main())
