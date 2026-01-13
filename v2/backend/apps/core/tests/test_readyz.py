"""
Testes para endpoint /readyz (PR 12/N).

Cobertura:
- Health check do banco de dados (PostgreSQL)
- Health check do cache (Redis/LocMem)
- Resposta 200 quando healthy
- Resposta 503 quando unhealthy

Endpoint testado:
- GET /readyz
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false

from __future__ import annotations
import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from unittest.mock import patch

pytestmark = pytest.mark.django_db


# ============================================================================
# TESTES DE ESTRUTURA DA RESPOSTA
# ============================================================================


def test_readyz_returns_200_when_healthy():
    """GET /readyz retorna 200 quando sistema está healthy."""
    client = APIClient()
    url = reverse("core:readyz")
    res = client.get(url)

    assert res.status_code == 200, f"Readyz deve retornar 200 quando healthy: {res.json()}"

    data = res.json()
    assert "status" in data
    assert "checks" in data
    assert data["status"] == "healthy"


def test_readyz_checks_database():
    """Readyz verifica conexão com banco de dados."""
    client = APIClient()
    url = reverse("core:readyz")
    res = client.get(url)

    assert res.status_code == 200
    data = res.json()

    assert "database" in data["checks"]
    assert data["checks"]["database"] == "ok", "Database deve estar ok"


def test_readyz_checks_cache():
    """Readyz verifica conexão com cache (Redis ou LocMem)."""
    client = APIClient()
    url = reverse("core:readyz")
    res = client.get(url)

    assert res.status_code == 200
    data = res.json()

    assert "cache" in data["checks"]
    # Cache pode retornar "ok" ou "warning" (se disabled/LocMem)
    assert data["checks"]["cache"] in ["ok", "warning: set/get failed"], "Cache deve ter status válido"


# ============================================================================
# TESTES DE FALHAS
# ============================================================================


@patch("django.db.connection.cursor")
def test_readyz_returns_503_when_database_fails(mock_cursor):
    """Readyz retorna 503 se banco de dados falhar."""
    # Simular erro de conexão
    mock_cursor.side_effect = Exception("Connection refused")

    client = APIClient()
    url = reverse("core:readyz")
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

    client = APIClient()
    url = reverse("core:readyz")
    res = client.get(url)

    # Cache failure não deve causar 503 (é opcional)
    assert res.status_code == 200, "Cache failure não deve causar 503"

    data = res.json()
    assert data["status"] == "healthy"
    assert "warning:" in data["checks"]["cache"]


# ============================================================================
# TESTES DE AUTENTICAÇÃO
# ============================================================================


def test_readyz_does_not_require_authentication():
    """Readyz é público (não requer autenticação) para health checks externos."""
    client = APIClient()
    url = reverse("core:readyz")
    res = client.get(url)

    # Não deve retornar 401 ou 403
    assert res.status_code in [200, 503], "Readyz não deve requerer autenticação"


# ============================================================================
# TESTES DE EDGE CASES
# ============================================================================


def test_readyz_database_returns_unexpected_result():
    """Readyz trata resultado inesperado do banco como erro."""
    with patch("django.db.connection.cursor") as mock_cursor:
        mock_cursor_instance = mock_cursor.return_value.__enter__.return_value
        mock_cursor_instance.fetchone.return_value = (999,)  # Não é 1

        client = APIClient()
        url = reverse("core:readyz")
        res = client.get(url)

        assert res.status_code == 503, "Resultado inesperado do DB deve causar 503"

        data = res.json()
        assert data["status"] == "unhealthy"
        assert "unexpected result" in data["checks"]["database"]


def test_readyz_json_format():
    """Readyz retorna JSON válido."""
    client = APIClient()
    url = reverse("core:readyz")
    res = client.get(url)

    assert res.status_code == 200

    # Verificar que é JSON válido
    data = res.json()
    assert isinstance(data, dict)
    assert isinstance(data["checks"], dict)


# ============================================================================
# TESTES DE INTEGRAÇÃO
# ============================================================================


def test_readyz_works_with_real_database():
    """Readyz funciona com banco de dados real (não mock)."""
    client = APIClient()
    url = reverse("core:readyz")
    res = client.get(url)

    assert res.status_code == 200
    data = res.json()

    # Com DB real, deve retornar ok
    assert data["checks"]["database"] == "ok"
    assert data["status"] == "healthy"


def test_readyz_works_with_real_cache():
    """Readyz funciona com cache real (LocMem ou Redis)."""
    client = APIClient()
    url = reverse("core:readyz")
    res = client.get(url)

    assert res.status_code == 200
    data = res.json()

    # Cache deve estar ok ou com warning (não error)
    assert "ok" in data["checks"]["cache"] or "warning" in data["checks"]["cache"]
