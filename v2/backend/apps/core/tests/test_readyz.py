"""
Testes para endpoint /readyz (PR 12/N).

Cobertura:
- Health check do banco de dados (PostgreSQL)
- Health check do cache (Redis/LocMem)
- Resposta 200 quando healthy
- Resposta 503 quando unhealthy

Endpoint testado:
- GET /readyz

SEC-RECON-03: readyz now returns conditional payload:
- Anonymous: {"status": "healthy"} (no checks)
- Staff/admin: {"status": "healthy", "checks": {...}} (full details)
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

import pytest

pytestmark = pytest.mark.django_db

User = get_user_model()


def _staff_client() -> APIClient:
    """Create an APIClient authenticated as staff (required for full readyz payload)."""
    user = User.objects.create_user("readyz_staff", "rz@test.com", "pass1234", is_staff=True)
    client = APIClient()
    client.force_authenticate(user=user)
    return client


# ============================================================================
# TESTES DE ESTRUTURA DA RESPOSTA (staff — full payload)
# ============================================================================


def test_readyz_returns_200_when_healthy():
    """GET /readyz retorna 200 quando sistema está healthy."""
    client = _staff_client()
    url = reverse("core:readyz")
    res = client.get(url)

    assert res.status_code == 200, f"Readyz deve retornar 200 quando healthy: {res.json()}"

    data = res.json()
    assert "status" in data
    assert "checks" in data
    assert data["status"] == "healthy"


def test_readyz_checks_database():
    """Readyz verifica conexão com banco de dados."""
    client = _staff_client()
    url = reverse("core:readyz")
    res = client.get(url)

    assert res.status_code == 200
    data = res.json()

    assert "database" in data["checks"]
    assert data["checks"]["database"] == "ok", "Database deve estar ok"


def test_readyz_checks_cache():
    """Readyz verifica conexão com cache (Redis ou LocMem)."""
    client = _staff_client()
    url = reverse("core:readyz")
    res = client.get(url)

    assert res.status_code == 200
    data = res.json()

    assert "cache" in data["checks"]
    # Cache pode retornar "ok" ou "warning" (se disabled/LocMem)
    assert data["checks"]["cache"] in ["ok", "warning: set/get failed"], "Cache deve ter status válido"


# ============================================================================
# TESTES DE FALHAS (staff — needs full payload to verify check details)
# ============================================================================


def test_readyz_returns_503_when_database_fails():
    """Readyz retorna 503 se banco de dados falhar."""
    # Create staff user BEFORE mocking cursor (needs real DB)
    client = _staff_client()
    url = reverse("core:readyz")

    with patch("django.db.connection.cursor") as mock_cursor:
        mock_cursor.side_effect = Exception("Connection refused")
        res = client.get(url)

    assert res.status_code == 503, "Readyz deve retornar 503 quando database falha"

    data = res.json()
    assert data["status"] == "unhealthy"
    assert "error:" in data["checks"]["database"]


@patch("django.core.cache.cache.set")
def test_readyz_cache_failure_is_warning_not_503(mock_cache_set):
    """Falha no cache não marca sistema como unhealthy (apenas warning)."""
    # Simular erro no cache
    mock_cache_set.side_effect = Exception("Redis connection refused")

    client = _staff_client()
    url = reverse("core:readyz")
    res = client.get(url)

    # Cache failure não deve causar 503 (é opcional)
    assert res.status_code == 200, "Cache failure não deve causar 503"

    data = res.json()
    assert data["status"] == "healthy"
    assert "warning:" in data["checks"]["cache"]


# ============================================================================
# TESTES DE AUTENTICAÇÃO (SEC-RECON-03)
# ============================================================================


def test_readyz_does_not_require_authentication():
    """Readyz é público (não requer autenticação) para health checks externos."""
    client = APIClient()
    url = reverse("core:readyz")
    res = client.get(url)

    # Não deve retornar 401 ou 403
    assert res.status_code in [200, 503], "Readyz não deve requerer autenticação"


def test_readyz_anonymous_gets_minimal_payload():
    """SEC-RECON-03: Anonymous users get only status, no checks."""
    client = APIClient()
    url = reverse("core:readyz")
    res = client.get(url)

    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "checks" not in data


def test_readyz_staff_gets_full_payload():
    """SEC-RECON-03: Staff users get full payload with checks."""
    client = _staff_client()
    url = reverse("core:readyz")
    res = client.get(url)

    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "checks" in data


# ============================================================================
# TESTES DE EDGE CASES (staff)
# ============================================================================


def test_readyz_database_returns_unexpected_result():
    """Readyz trata resultado inesperado do banco como erro."""
    with patch("django.db.connection.cursor") as mock_cursor:
        mock_cursor_instance = mock_cursor.return_value.__enter__.return_value
        mock_cursor_instance.fetchone.return_value = (999,)  # Não é 1

        client = _staff_client()
        url = reverse("core:readyz")
        res = client.get(url)

        assert res.status_code == 503, "Resultado inesperado do DB deve causar 503"

        data = res.json()
        assert data["status"] == "unhealthy"
        assert "unexpected result" in data["checks"]["database"]


def test_readyz_json_format():
    """Readyz retorna JSON válido."""
    client = _staff_client()
    url = reverse("core:readyz")
    res = client.get(url)

    assert res.status_code == 200

    # Verificar que é JSON válido
    data = res.json()
    assert isinstance(data, dict)
    assert isinstance(data["checks"], dict)


# ============================================================================
# TESTES DE INTEGRAÇÃO (staff)
# ============================================================================


def test_readyz_works_with_real_database():
    """Readyz funciona com banco de dados real (não mock)."""
    client = _staff_client()
    url = reverse("core:readyz")
    res = client.get(url)

    assert res.status_code == 200
    data = res.json()

    # Com DB real, deve retornar ok
    assert data["checks"]["database"] == "ok"
    assert data["status"] == "healthy"


def test_readyz_works_with_real_cache():
    """Readyz funciona com cache real (LocMem ou Redis)."""
    client = _staff_client()
    url = reverse("core:readyz")
    res = client.get(url)

    assert res.status_code == 200
    data = res.json()

    # Cache deve estar ok ou com warning (não error)
    assert "ok" in data["checks"]["cache"] or "warning" in data["checks"]["cache"]
