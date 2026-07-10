"""
Testes para /api/features - apply_blocked.

Valida que o campo apply_blocked é calculado corretamente com base no valor de
GCAL_CLIENT (apply_blocked = GCAL_CLIENT != "google" — trava operações acidentais
no Google Calendar).

#1541: os 4 testes estavam 100% em @pytest.mark.skip 'TEMP' desde o PR16 (jan/2026)
e nunca foram restaurados — o campo de segurança apply_blocked ficou sem cobertura
ativa. Pior: se reativados falhariam por dois motivos (a) usavam APIClient SEM auth
esperando 200, mas o endpoint exige autenticação (403); (b) usavam
patch.dict(os.environ, ...) mas a view lê settings.GCAL_CLIENT, não os.environ. Ambos
corrigidos aqui (force_authenticate + @override_settings).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from django.test import override_settings
from rest_framework.test import APIClient

import pytest

from apps.core.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db


def _auth_client() -> APIClient:
    client = APIClient()
    client.force_authenticate(user=UsuarioFactory())
    return client


@override_settings(GCAL_CLIENT="fake")
def test_features_apply_blocked_true():
    """apply_blocked=True quando GCAL_CLIENT='fake' (bloqueia apply acidental)."""
    response = _auth_client().get("/api/features/")

    assert response.status_code == 200
    data = response.json()
    assert data["apply_blocked"] is True
    assert data["GCAL_CLIENT"] == "fake"


@override_settings(GCAL_CLIENT="google")
def test_features_apply_blocked_false():
    """apply_blocked=False quando GCAL_CLIENT='google' (client real permite apply)."""
    response = _auth_client().get("/api/features/")

    assert response.status_code == 200
    data = response.json()
    assert data["apply_blocked"] is False
    assert data["GCAL_CLIENT"] == "google"


@override_settings(GCAL_CLIENT="test")
def test_features_apply_blocked_with_unknown_client():
    """Qualquer valor != 'google' bloqueia apply (fail-safe)."""
    response = _auth_client().get("/api/features/")

    assert response.status_code == 200
    data = response.json()
    assert data["apply_blocked"] is True
    assert data["GCAL_CLIENT"] == "test"


def test_features_returns_environment():
    """/api/features retorna ENVIRONMENT + GCAL_CLIENT."""
    response = _auth_client().get("/api/features/")

    assert response.status_code == 200
    data = response.json()
    assert "ENVIRONMENT" in data
    assert "GCAL_CLIENT" in data


def test_features_requires_authentication():
    """Sem auth → 403: o endpoint expõe config de ambiente, não pode ser anônimo."""
    response = APIClient().get("/api/features/")

    assert response.status_code in (401, 403)
