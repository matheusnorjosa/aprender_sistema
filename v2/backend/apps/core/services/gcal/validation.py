"""
AS v2 — GCal Event ID Validation

Validation utilities for Google Calendar event IDs.
"""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false

from __future__ import annotations

import re

from apps.core.models import Solicitacao
from apps.core.types import EventId


def _validate_event_id(event_id: EventId) -> bool:
    """
    Valida eventId conforme especificação Google Calendar API.

    Regras:
    - Comprimento: 5-1024 caracteres
    - Caracteres permitidos: a-z, 0-9, - (hífen), _ (underscore)
    - Deve ser lowercase

    Args:
        event_id: ID do evento a validar

    Returns:
        bool: True se válido, False caso contrário

    Raises:
        ValueError: Se eventId inválido (com mensagem descritiva)
    """
    if not event_id:
        raise ValueError("eventId não pode ser vazio")

    if len(event_id) < 5:
        raise ValueError(f"eventId muito curto: {len(event_id)} chars (mínimo: 5)")

    if len(event_id) > 1024:
        raise ValueError(f"eventId muito longo: {len(event_id)} chars (máximo: 1024)")

    # Verificar caracteres permitidos (a-z, 0-9, -, _)
    if not re.match(r"^[a-z0-9_-]+$", event_id):
        raise ValueError(
            f"eventId contém caracteres inválidos: {event_id}. "
            "Permitido: a-z, 0-9, -, _"
        )

    return True


def _event_id_for(s: Solicitacao) -> EventId:
    """
    Gera eventId determinístico para uma Solicitacao.

    Format: asv2-{id}

    Args:
        s: Solicitacao

    Returns:
        str: Event ID determinístico (ex: asv2-123)

    Raises:
        ValueError: Se ID gerado for inválido
    """
    event_id = f"asv2-{s.id}"

    # Validar antes de retornar
    _validate_event_id(event_id)

    return event_id
