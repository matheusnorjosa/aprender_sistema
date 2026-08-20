"""
Recalcula `DATRegistro.nr_codigos` a partir das compras (contrato v5).

Backfill idempotente / rede de segurança para o cálculo per-compra: rode após um
import de `dat_compra`, uma migração de dados, ou para convergir qualquer drift.
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand

from apps.core.models import DATRegistro
from apps.core.services.dat_codigos import recompute_all


class Command(BaseCommand):
    help = "Recalcula nr_codigos de todos os DATRegistro a partir das compras (idempotente)."

    def handle(self, *args: Any, **opts: Any) -> None:
        total = DATRegistro.objects.count()
        alterados = recompute_all()
        self.stdout.write(self.style.SUCCESS(f"Recalculados {total} registros; {alterados} alterados."))
