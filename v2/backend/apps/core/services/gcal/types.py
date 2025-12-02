"""
AS v2 — GCal Sync Types

Type definitions for GCal sync operations.
"""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

from apps.core.types import EventId

# Type alias for sync actions (different from ActionType in types.py which is for audit logs)
Action: TypeAlias = Literal["CREATE", "UPDATE", "DELETE", "ADOPT", "SKIP"]


@dataclass
class SyncOutcome:
    """
    Resultado de uma operação de sincronização.

    action: Tipo de ação executada
    solicitation_id: ID da solicitação
    external_event_id: ID do evento no Calendar (ou None)
    summary: Resumo do evento
    """

    action: Action
    solicitation_id: int
    external_event_id: EventId | None
    summary: str
