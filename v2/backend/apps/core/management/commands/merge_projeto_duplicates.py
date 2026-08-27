"""Command: mescla os 3 pares VIDA duplicados no golden DB. Dry-run por padrão;
`--apply` executa. Lógica em `apps/core/services/projeto_merge.py`."""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false, reportUnknownArgumentType=false

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand

from apps.core.services.projeto_merge import merge_projeto_duplicates


class Command(BaseCommand):
    help = "Mescla pares de Projeto duplicados (planos/DAT ↔ operacional '&'). Dry-run por padrão."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--apply", action="store_true", help="Executa a mesclagem (sem isto, só reporta).")

    def handle(self, *args: Any, **options: Any) -> None:
        apply = bool(options["apply"])
        report = merge_projeto_duplicates(apply=apply)
        for e in report["pairs"]:
            self.stdout.write(
                f"[{e['status']:>11}] {e['dup']!r} → {e['survivor']!r}  reparent={e.get('reparented', {})}"
            )
        modo = "APLICADO" if apply else "DRY-RUN (nada gravado)"
        self.stdout.write(self.style.SUCCESS(f"merge_projeto_duplicates: {modo}"))
