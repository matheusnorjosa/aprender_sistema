"""
Participation.role: CheckConstraint no banco (integridade — auditoria #4).

`role` tinha só `choices` (validação Python), que import/shell/`.update()` driblam
— o PG aceitava um papel fora do contrato, quebrando availability/RBAC/relatórios
em silêncio. Espelha os 5 enums já protegidos por CHECK na migration 0032
(Solicitacao.status/gcal_status, AvailabilityBlock.status/tipo, Projeto.fluxo).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false, reportArgumentType=false, reportCallIssue=false, reportGeneralTypeIssues=false

from __future__ import annotations

from django.db import IntegrityError, transaction

import pytest

from apps.core.models import Participation
from apps.core.tests.factories import SolicitacaoFactory


@pytest.mark.django_db
class TestParticipationRoleDBConstraint:
    """O banco deve rejeitar `role` fora de Role.choices (não só o Python)."""

    def test_meta_declara_constraint_de_role(self):
        nomes = {c.name for c in Participation._meta.constraints}
        assert "core_participation_role_valid" in nomes

    def test_role_invalido_rejeitado_pelo_banco(self):
        sol = SolicitacaoFactory()
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Participation.objects.create(
                    solicitacao=sol,
                    guest_nome="Fulano de Tal",
                    role="PAPEL_INVALIDO",
                )

    def test_role_valido_aceito(self):
        sol = SolicitacaoFactory()
        p = Participation.objects.create(
            solicitacao=sol,
            guest_nome="Fulano de Tal",
            role=Participation.Role.FORMADOR,
        )
        assert p.pk is not None
