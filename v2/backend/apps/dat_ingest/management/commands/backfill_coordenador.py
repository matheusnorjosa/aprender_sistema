"""
Management command to backfill coordenador field from usuario.

For events imported via ETL where coordenador is NULL,
set coordenador = usuario (the coordenador from spreadsheet column N).
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandParser
from django.db.models import F

from apps.core.models import Solicitacao


class Command(BaseCommand):
    help = "Backfill coordenador field from usuario for ETL-imported events"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without applying them",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        dry_run = options.get("dry_run", False)

        self.stdout.write(f"🔄 Backfilling coordenador field (dry_run={dry_run})")

        # Find all solicitacoes where coordenador is NULL but usuario is not
        events_to_update = Solicitacao.objects.filter(
            coordenador__isnull=True,
            usuario__isnull=False
        )

        total = events_to_update.count()
        self.stdout.write(f"   Found {total} events to update")

        if total == 0:
            self.stdout.write(self.style.SUCCESS("   ✅ Nothing to update"))
            return

        if dry_run:
            # Show sample of what would be updated
            sample_size = min(5, total)
            self.stdout.write(f"\n   Sample of {sample_size} events that would be updated:")
            for sol in events_to_update[:sample_size]:
                self.stdout.write(
                    f"     ID {sol.id}: usuario={sol.usuario.username} -> coordenador={sol.usuario.username}"
                )
            self.stdout.write(f"\n   [DRY-RUN] Would update {total} events")
        else:
            # Update all events
            updated = events_to_update.update(coordenador=F('usuario'))
            self.stdout.write(self.style.SUCCESS(f"   ✅ Updated {updated} events"))
