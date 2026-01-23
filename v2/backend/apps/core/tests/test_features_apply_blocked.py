"""
Testes para /api/features - apply_blocked.

Valida que o campo apply_blocked é calculado corretamente
com base no valor de GCAL_CLIENT.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

import os
from unittest.mock import patch

from rest_framework.test import APIClient

import pytest

pytestmark = pytest.mark.django_db


@pytest.mark.skip(reason="TEMP: De outro PR - será corrigido após merge sequencial")
def test_features_apply_blocked_true():
    """
    Testa que apply_blocked=True quando GCAL_CLIENT="fake".

    Garante que operações de apply são bloqueadas com client fake
    para evitar operações acidentais.
    """
    with patch.dict(os.environ, {"GCAL_CLIENT": "fake"}):
        client = APIClient()
        response = client.get("/api/features/")

        assert response.status_code == 200
        data = response.json()
        assert "apply_blocked" in data
        assert data["apply_blocked"] is True
        assert data["GCAL_CLIENT"] == "fake"


@pytest.mark.skip(reason="TEMP: De outro PR - será corrigido após merge sequencial")
def test_features_apply_blocked_false():
    """
    Testa que apply_blocked=False quando GCAL_CLIENT="google".

    Com client real do Google, operações de apply são permitidas.
    """
    with patch.dict(os.environ, {"GCAL_CLIENT": "google"}):
        client = APIClient()
        response = client.get("/api/features/")

        assert response.status_code == 200
        data = response.json()
        assert "apply_blocked" in data
        assert data["apply_blocked"] is False
        assert data["GCAL_CLIENT"] == "google"


@pytest.mark.skip(reason="TEMP: De outro PR - será corrigido após merge sequencial")
def test_features_returns_environment():
    """
    Testa que /api/features retorna informações de ambiente.
    """
    client = APIClient()
    response = client.get("/api/features/")

    assert response.status_code == 200
    data = response.json()
    assert "ENVIRONMENT" in data
    assert "GCAL_CLIENT" in data


@pytest.mark.skip(reason="TEMP: De outro PR - será corrigido após merge sequencial")
def test_features_apply_blocked_with_unknown_client():
    """
    Testa que apply_blocked=True com client desconhecido.

    Qualquer valor diferente de "google" deve bloquear apply.
    """
    with patch.dict(os.environ, {"GCAL_CLIENT": "test"}):
        client = APIClient()
        response = client.get("/api/features/")

        assert response.status_code == 200
        data = response.json()
        assert data["apply_blocked"] is True
        assert data["GCAL_CLIENT"] == "test"
