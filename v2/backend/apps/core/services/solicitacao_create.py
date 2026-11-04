"""
Solicitacao creation service.

Centralizes initial status decision for new solicitacoes.
"""

from __future__ import annotations

from dataclasses import dataclass

from apps.core.models import Projeto


@dataclass(frozen=True)
class InitialStatusDecision:
    """Decision metadata for initial status assignment."""

    status: str
    fluxo: str | None
    reason: str


def resolve_initial_status(*, projeto: Projeto | None, sem_compra: bool = False) -> InitialStatusDecision:
    """
    Resolve initial status for a new solicitacao.

    Rules:
    - sem_compra (par sem compra, quem cria não é isento; pedido do dono, 03/11/2026) -> "pendente",
      em qualquer fluxo
    - projeto.fluxo == "NAO_SUPER" -> "aprovado"
    - otherwise -> "pendente"

    `sem_compra` é decidido por quem chama (a Regra 4 do serializer); os importadores não o passam.
    """
    fluxo = projeto.fluxo if projeto else None

    if sem_compra:
        return InitialStatusDecision(status="pendente", fluxo=fluxo, reason="sem_compra")

    if fluxo == "NAO_SUPER":
        return InitialStatusDecision(
            status="aprovado",
            fluxo=fluxo,
            reason="projeto_fluxo_nao_super",
        )

    return InitialStatusDecision(
        status="pendente",
        fluxo=fluxo,
        reason="default_or_super_flow",
    )
