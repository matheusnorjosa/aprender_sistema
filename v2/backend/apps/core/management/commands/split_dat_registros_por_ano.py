"""Command: split per-year de DATRegistro. Roda APÓS o import das compras. Ver
`apps/core/services/dat_registro_split.py`."""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand

from apps.core.services.dat_registro_split import split_dat_registros


class Command(BaseCommand):
    help = "Divide os DATRegistro flat em um registro por ano de uso das compras (split per-year)."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--dry-run", action="store_true", help="Não grava; só reporta o que faria.")

    def handle(self, *args: Any, **options: Any) -> None:
        dry_run = bool(options["dry_run"])
        r = split_dat_registros(dry_run=dry_run)
        sufixo = " (DRY-RUN, nada gravado)" if dry_run else ""
        self.stdout.write(
            f"Pares processados: {r['pares']} | registros criados: {r['criados']} | "
            f"reatribuídos: {r['reatribuidos']} | compras sem registro: {r['compras_sem_registro']}{sufixo}"
        )
