"""
"Eventos Futuros" do Dashboard Geral conta pelo dia de Fortaleza (RD-06), não pelo dia UTC.

Entre 21h e 0h de Fortaleza o dia UTC já é o seguinte: o evento de hoje à noite sumia da contagem.
Achado do roteiro de conferência das telas depois da carga (#1900, 09/11/2026).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOptionalSubscript=false

from __future__ import annotations

from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from unittest import mock
from zoneinfo import ZoneInfo

from rest_framework.test import APIClient

import pytest

from apps.core.tests.factories import SolicitacaoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

FORTALEZA = ZoneInfo("America/Fortaleza")


def test_evento_de_hoje_a_noite_conta_como_futuro_depois_das_21h():
    # 09/11 às 22h em Fortaleza = 10/11 à 1h UTC.
    agora = datetime(2026, 11, 10, 1, 0, tzinfo=dt_timezone.utc)
    inicio = datetime(2026, 11, 9, 23, 0, tzinfo=FORTALEZA)
    SolicitacaoFactory(status="aprovado", inicio=inicio, fim=inicio + timedelta(minutes=50))

    client = APIClient()
    client.force_authenticate(user=UsuarioFactory(superuser=True))
    with mock.patch("django.utils.timezone.now", return_value=agora):
        resp = client.get("/api/dashboard/overview/")

    assert resp.status_code == 200, resp.data
    assert resp.data["kpis"]["eventos_futuros"] == 1
