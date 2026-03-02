"""
ETL de Compras: import idempotente de COMPRAS_pronto.csv.

Delega toda a lógica para apps.core.services.controle_imports.import_compras_from_file.

Uso:
    # Dry-run (preview sem writes)
    python manage.py etl_import_compras --file=<path> --dry-run

    # Apply (persiste no banco)
    python manage.py etl_import_compras --file=<path>
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportMissingParameterType=false

from __future__ import annotations

import json
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.core.services.controle_imports import import_compras_from_file


class Command(BaseCommand):
    help = "Importa COMPRAS_pronto.csv para o banco (idempotente, dry-run por padrão)"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--file",
            type=str,
            required=True,
            help="Caminho do arquivo CSV (COMPRAS_pronto.csv)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Simula execução sem writes no banco (padrão: False)",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        file_path: str = options["file"]
        dry_run: bool = options["dry_run"]

        self.stdout.write(f"[COMPRAS ETL] file={file_path} dry_run={dry_run}")

        try:
            report = import_compras_from_file(path=file_path, dry_run=dry_run)
        except FileNotFoundError as exc:
            raise CommandError(str(exc)) from exc

        stats = report["stats"]
        pendencias = report["pendencias"]

        mode = "DRY-RUN" if dry_run else "APPLY"
        self.stdout.write(f"\n[{mode}] Processadas {stats.get('total', '?')} linhas")
        self.stdout.write(f"  Created:   {stats['created']}")
        self.stdout.write(f"  Updated:   {stats.get('updated', 0)}")
        self.stdout.write(f"  Skipped:   {stats['skipped']}")

        mun_missing = pendencias.get("municipios", [])
        proj_missing = pendencias.get("projetos", [])
        linhas_inv = pendencias.get("linhas_invalidas", [])

        if mun_missing:
            self.stdout.write(self.style.WARNING(f"\nPENDÊNCIAS — municípios ({len(mun_missing)}):"))
            for p in mun_missing[:10]:
                self.stdout.write(f"  linha {p['row']}: '{p['municipio']}' ({p.get('uf', '')})")
            if len(mun_missing) > 10:
                self.stdout.write(f"  ... e mais {len(mun_missing) - 10}")

        if proj_missing:
            self.stdout.write(self.style.WARNING(f"\nPENDÊNCIAS — projetos ({len(proj_missing)}):"))
            for p in proj_missing[:10]:
                self.stdout.write(f"  linha {p['row']}: produto '{p['produto']}'")
            if len(proj_missing) > 10:
                self.stdout.write(f"  ... e mais {len(proj_missing) - 10}")

        if linhas_inv:
            self.stdout.write(self.style.WARNING(f"\nPENDÊNCIAS — linhas inválidas ({len(linhas_inv)}):"))
            for p in linhas_inv[:5]:
                self.stdout.write(f"  linha {p['row']}: {p['motivo']}")

        self.stdout.write("\nRelatório JSON: out_etl/import_compras_report.json")

        if dry_run:
            self.stdout.write(self.style.WARNING("\n[DRY-RUN] Nenhuma alteração foi gravada."))
        else:
            self.stdout.write(self.style.SUCCESS(f"\n✅ ETL concluído — {stats['created']} compras criadas."))
