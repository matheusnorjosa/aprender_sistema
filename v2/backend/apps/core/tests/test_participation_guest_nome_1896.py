"""#1896 (D1) — `Participation.guest_nome`: preserva o nome do participante quando NEM
`usuario` NEM `guest_email` resolvem.

Import v15 (RELAY 50): 251 linhas de 3 pessoas que saíram ficam com o nome preenchido e
SEM pessoa vinculada — o nome é MARCADO, não descartado. O `CheckConstraint` de hoje
(`usuario OR guest_email`) tornava isso impossível. D1: relaxa a constraint para incluir
`guest_nome != ''` e adiciona uma UniqueConstraint parcial nome-only (idempotência do
handler de import: re-run não duplica).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportIndexIssue=false, reportCallIssue=false, reportArgumentType=false, reportOperatorIssue=false, reportGeneralTypeIssues=false

from __future__ import annotations

from django.db import IntegrityError, transaction

import pytest

from apps.core.models.solicitacao import Participation
from apps.core.serializers.solicitacao import ParticipationNestedSerializer
from apps.core.tests.factories import SolicitacaoFactory


@pytest.mark.django_db
def test_can_create_participation_with_only_guest_nome() -> None:
    sol = SolicitacaoFactory()
    p = Participation.objects.create(solicitacao=sol, role=Participation.Role.FORMADOR, guest_nome="Fulana Que Saiu")
    assert p.pk is not None
    assert p.usuario is None
    assert not p.guest_email
    assert p.guest_nome == "Fulana Que Saiu"


@pytest.mark.django_db
def test_name_only_participation_is_unique_per_solicitacao_role() -> None:
    sol = SolicitacaoFactory()
    Participation.objects.create(solicitacao=sol, role=Participation.Role.FORMADOR, guest_nome="Fulana")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Participation.objects.create(solicitacao=sol, role=Participation.Role.FORMADOR, guest_nome="Fulana")


@pytest.mark.django_db
def test_still_rejects_participation_with_no_identity() -> None:
    """Sem usuario, sem email E sem nome → o CheckConstraint continua barrando."""
    sol = SolicitacaoFactory()
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Participation.objects.create(solicitacao=sol, role=Participation.Role.FORMADOR)


@pytest.mark.django_db
def test_serializer_exposes_guest_nome() -> None:
    sol = SolicitacaoFactory()
    p = Participation.objects.create(solicitacao=sol, role=Participation.Role.FORMADOR, guest_nome="Fulana")
    data = ParticipationNestedSerializer(p).data
    assert data["guest_nome"] == "Fulana"
