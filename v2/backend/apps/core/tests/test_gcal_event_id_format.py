"""
Testes do formato do eventId do Google Calendar (regra real base32hex).

O Google Calendar rejeita (HTTP 400 "Invalid resource id value") eventIds fora
da regra base32hex: apenas letras ``a-v`` e dígitos ``0-9``, sem hífen nem
underscore, com 5 a 1024 caracteres. O formato antigo ``asv2-{id}`` (com hífen)
era aceito por engano na validação local e falhava em produção.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportUnknownArgumentType=false

from __future__ import annotations

import re

import pytest

from apps.core.services.gcal.validation import (
    GCAL_EVENT_ID_PREFIX,
    _event_id_for,
    _validate_event_id,
)
from apps.core.tests.factories import SolicitacaoFactory

# Regra real do Google Calendar API para eventId: base32hex (a-v, 0-9), 5-1024 chars.
GOOGLE_EVENT_ID_RE = re.compile(r"^[a-v0-9]{5,1024}$")


@pytest.mark.django_db
def test_event_id_for_matches_google_base32hex_rule():
    """_event_id_for deve gerar um id que o Google aceita (sem hífen/underscore)."""
    sol = SolicitacaoFactory()

    event_id = _event_id_for(sol)

    assert GOOGLE_EVENT_ID_RE.match(event_id), f"eventId {event_id!r} deve casar a regra base32hex do Google (a-v, 0-9)"
    assert "-" not in event_id, "eventId não pode conter hífen (Google rejeita)"
    assert "_" not in event_id, "eventId não pode conter underscore (Google rejeita)"
    assert event_id == f"{GCAL_EVENT_ID_PREFIX}{sol.id}"


@pytest.mark.django_db
def test_event_id_prefix_is_valid_base32hex():
    """O prefixo canônico 'asv2' deve ser válido (a,s,v ∈ a-v; 2 ∈ 0-9)."""
    assert GOOGLE_EVENT_ID_RE.match(f"{GCAL_EVENT_ID_PREFIX}00000")


def test_validate_event_id_rejects_hyphen_and_underscore():
    """Formato antigo com hífen/underscore deve ser rejeitado (Google dá HTTP 400)."""
    with pytest.raises(ValueError):
        _validate_event_id("asv2-123")
    with pytest.raises(ValueError):
        _validate_event_id("asv2_123")


def test_validate_event_id_accepts_base32hex_and_rejects_out_of_range_letters():
    """Aceita a-v/0-9; rejeita w-z (fora do alfabeto base32hex)."""
    assert _validate_event_id("asv23265") is True
    with pytest.raises(ValueError):
        _validate_event_id("asv2zzzz")
