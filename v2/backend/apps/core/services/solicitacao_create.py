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


def resolve_initial_status(*, projeto: Projeto | None) -> InitialStatusDecision:
    """
    Resolve initial status for a new solicitacao.

    Rules:
    - projeto.fluxo == "NAO_SUPER" -> "aprovado"
    - otherwise -> "pendente"
    """
    fluxo = projeto.fluxo if projeto else None

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
