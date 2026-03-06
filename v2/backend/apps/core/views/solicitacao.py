"""
AS v2 - Solicitacao ViewSet compatibility wrapper.

Canonical implementation lives in `apps.core.views_solicitacao`.
This module exists only to preserve import compatibility for:
`from apps.core.views.solicitacao import SolicitacaoViewSet`.
"""

from __future__ import annotations

from apps.core.views_solicitacao import SolicitacaoViewSet

__all__ = ["SolicitacaoViewSet"]
