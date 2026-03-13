"""
Seed idempotente dos 32 templates de acoes/notificacoes e executores.
"""

# pyright: reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandParser

from apps.core.services.acoes_notificacao_seed import seed_acoes_notificacao


class Command(BaseCommand):
    """Command para seed idempotente do modulo de acoes/notificacoes."""

    help = "Cria/atualiza templates de acoes (32 passos) e mapeamento de executores."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Exibe detalhes da execucao.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        verbose = bool(options.get("verbose", False))
        stats = seed_acoes_notificacao(verbose=verbose)
        message = (
            "Seed de acoes/notificacoes aplicado: "
            f"groups_created={stats['groups_created']}, "
            f"templates_created={stats['templates_created']}, "
            f"templates_updated={stats['templates_updated']}, "
            f"executor_links_created={stats['executor_links_created']}, "
            f"executor_links_removed={stats['executor_links_removed']}"
        )

        self.stdout.write(self.style.SUCCESS(message))
