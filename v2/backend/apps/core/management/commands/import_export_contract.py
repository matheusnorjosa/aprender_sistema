"""
Management command — importer do export-contract (dry-run-first).

Uso:
    # dry-run (padrão, não escreve):
    python manage.py import_export_contract --path /caminho/export-contract-2026-06-02-fix1

    # apply create-only de entidades EXPLICITAMENTE permitidas (futuro):
    python manage.py import_export_contract --path ... --apply --allow-entity dat_area

Segurança:
- sem `--apply` → dry-run (só classifica).
- `--apply` sem `--allow-entity` → BLOQUEADO (nada escrito).
- modo `create-only`: só insere would_create; nunca atualiza; nunca sobrescreve campo protegido.
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from django.core.management.base import BaseCommand

from apps.core.services.export_contract_importer import ExportContractImporter

if TYPE_CHECKING:
    from argparse import ArgumentParser


class Command(BaseCommand):
    help = "Importer do export-contract (dry-run por padrão; --apply exige --allow-entity)."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--path", required=True, help="Diretório do export-contract (com manifest.json).")
        parser.add_argument(
            "--mode",
            default="create-only",
            choices=["create-only"],
            help="Modo de import (apenas create-only nesta fase).",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            default=False,
            help="Executa writes. Exige --allow-entity; sem allowlist é bloqueado.",
        )
        parser.add_argument(
            "--allow-entity",
            action="append",
            default=[],
            dest="allow",
            help="Entidade permitida para apply (repetível). Sem isto, --apply não escreve.",
        )
        parser.add_argument("--json", action="store_true", default=False, help="Saída em JSON.")

    def handle(self, *args: Any, **opts: Any) -> None:
        importer = ExportContractImporter(
            path=opts["path"],
            mode=opts["mode"],
            apply=opts["apply"],
            allow=tuple(opts["allow"]),
        )
        report = importer.run()

        if opts["json"]:
            self.stdout.write(json.dumps(report, ensure_ascii=False, indent=2))
            return

        self.stdout.write(self.style.MIGRATE_HEADING("Import export-contract"))
        self.stdout.write(f"  path={opts['path']}  mode={report['mode']}  apply={report['apply']}")
        if report["apply_blocked"]:
            self.stdout.write(self.style.WARNING("  ⚠️  --apply BLOQUEADO: forneça --allow-entity. Nada escrito."))
        for ent, v in report["por_entidade"].items():
            if v.get("status") == "not_implemented":
                self.stdout.write(f"  [{ent}] NOT_IMPLEMENTED (rows={v['export_rows']})")
            else:
                linha = (
                    f"  [{ent}] rows={v['export_rows']} create={v['would_create']}"
                    + f" update={v['would_update']} skip={v['would_skip_same']}"
                    + f" protected_diff={v['protected_diff']} reject={v['would_reject']}"
                )
                self.stdout.write(linha)
        if report["applied"]:
            self.stdout.write(self.style.SUCCESS(f"  applied(create-only)={report['applied']}"))
