"""
G20 — "Total Formadores" do Dashboard Geral conta só quem é FORMADOR nos eventos aprovados.

Antes contava pessoas de qualquer papel (coordenador, coordenador que acompanha, convidado).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOptionalSubscript=false

from __future__ import annotations

from rest_framework.test import APIClient

import pytest

from apps.core.models import Participation
from apps.core.tests.factories import SolicitacaoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db


def test_total_formadores_conta_so_papel_formador():
    evento = SolicitacaoFactory(status="aprovado")
    for papel in Participation.Role:
        Participation.objects.create(solicitacao=evento, usuario=UsuarioFactory(), role=papel)
    # Formador de evento pendente não entra.
    pendente = SolicitacaoFactory()
    Participation.objects.create(solicitacao=pendente, usuario=UsuarioFactory(), role=Participation.Role.FORMADOR)

    client = APIClient()
    client.force_authenticate(user=UsuarioFactory(superuser=True))
    resp = client.get("/api/dashboard/overview/")

    assert resp.status_code == 200, resp.data
    assert resp.data["kpis"]["total_formadores"] == 1
