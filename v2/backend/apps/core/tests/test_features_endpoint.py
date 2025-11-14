"""
Testes para endpoint /api/features/ (PR 12/N).

Cobertura:
- Requer autenticação
- Retorna flags efetivas (merge cfg + fallback)
- Estrutura de resposta correta

Endpoint testado:
- GET /api/features/
"""

import pytest
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.core.models import Usuario

pytestmark = pytest.mark.django_db


# ============================================================================
# TESTES DE AUTENTICAÇÃO
# ============================================================================


def test_features_requires_authentication():
    """Endpoint /api/features/ exige autenticação."""
    client = APIClient()
    url = reverse("core:features")
    res = client.get(url)

    assert res.status_code == 403, "Deve retornar 403 para usuário não autenticado"


def test_features_authenticated_user_allowed():
    """Usuário autenticado tem acesso a /api/features/."""
    user = Usuario.objects.create_user(
        username="user1", email="user@x.com", password="x", cpf="11111111111"
    )

    client = APIClient()
    client.force_authenticate(user=user)

    url = reverse("core:features")
    res = client.get(url)

    assert res.status_code == 200, f"Usuário autenticado deve ter acesso: {res.data}"


# ============================================================================
# TESTES DE ESTRUTURA DA RESPOSTA
# ============================================================================


def test_features_response_structure():
    """Resposta de /api/features/ tem estrutura esperada."""
    user = Usuario.objects.create_user(
        username="user1", email="user@x.com", password="x", cpf="11111111111"
    )

    client = APIClient()
    client.force_authenticate(user=user)

    url = reverse("core:features")
    res = client.get(url)

    assert res.status_code == 200
    data = res.json()

    # Verificar campos obrigatórios
    assert "USE_V2_ONLY" in data
    assert "GCAL_MODE" in data
    assert "PREVIEW_ONLY" in data
    assert "METRICS_ENABLED" in data
    assert "SHOW_PRE_AGENDA" in data


@override_settings(GCAL_CLIENT='fake')
def test_features_default_values():
    """
    Flags padrão estão corretas (seguras para go-live).

    Issue #130: Forçar GCAL_CLIENT='fake' para garantir que GCAL_MODE derivado
    seja 'fake' independente da configuração do ambiente Docker.
    """
    user = Usuario.objects.create_user(
        username="user1", email="user@x.com", password="x", cpf="11111111111"
    )

    client = APIClient()
    client.force_authenticate(user=user)

    url = reverse("core:features")
    res = client.get(url)

    assert res.status_code == 200
    data = res.json()

    # Defaults seguros (PR 12/N - Go-live pack)
    assert data["USE_V2_ONLY"] is True, "USE_V2_ONLY deve ser true por padrão"
    assert data["GCAL_MODE"] == "fake", "GCAL_MODE deve ser 'fake' por padrão"
    assert data["PREVIEW_ONLY"] is True, "PREVIEW_ONLY deve ser true por padrão"
    assert data["METRICS_ENABLED"] is True, "METRICS_ENABLED deve ser true por padrão"
    assert data["SHOW_PRE_AGENDA"] is True, "SHOW_PRE_AGENDA deve ser true por padrão"


# ============================================================================
# TESTES DE MERGE CONFIG + FALLBACK
# ============================================================================


def test_features_returns_fallback_when_no_config():
    """Se não houver Config, retorna fallback de settings."""
    user = Usuario.objects.create_user(
        username="user1", email="user@x.com", password="x", cpf="11111111111"
    )

    client = APIClient()
    client.force_authenticate(user=user)

    url = reverse("core:features")
    res = client.get(url)

    assert res.status_code == 200
    data = res.json()

    # Deve retornar fallback (settings.FEATURE_FLAGS)
    assert "USE_V2_ONLY" in data
    assert "GCAL_MODE" in data


def test_features_config_overrides_fallback():
    """Config do banco sobrescreve fallback de settings."""
    from apps.core.models import Config

    # Criar Config com features customizadas
    Config.objects.create(
        key="features",
        value={
            "GCAL_MODE": "google",  # Sobrescreve "fake"
            "PREVIEW_ONLY": False,  # Sobrescreve true
        },
    )

    user = Usuario.objects.create_user(
        username="user1", email="user@x.com", password="x", cpf="11111111111"
    )

    client = APIClient()
    client.force_authenticate(user=user)

    url = reverse("core:features")
    res = client.get(url)

    assert res.status_code == 200
    data = res.json()

    # Valores customizados do Config devem prevalecer
    assert data["GCAL_MODE"] == "google", "Config deve sobrescrever fallback"
    assert data["PREVIEW_ONLY"] is False, "Config deve sobrescrever fallback"

    # Valores não no Config devem vir do fallback
    assert data["USE_V2_ONLY"] is True, "Fallback deve ser usado quando não em Config"


# ============================================================================
# TESTES DE TIPOS DE DADOS
# ============================================================================


def test_features_boolean_flags_are_booleans():
    """Flags booleanas retornam bool (não string)."""
    user = Usuario.objects.create_user(
        username="user1", email="user@x.com", password="x", cpf="11111111111"
    )

    client = APIClient()
    client.force_authenticate(user=user)

    url = reverse("core:features")
    res = client.get(url)

    assert res.status_code == 200
    data = res.json()

    assert isinstance(data["USE_V2_ONLY"], bool)
    assert isinstance(data["PREVIEW_ONLY"], bool)
    assert isinstance(data["METRICS_ENABLED"], bool)
    assert isinstance(data["SHOW_PRE_AGENDA"], bool)


def test_features_gcal_mode_is_string():
    """GCAL_MODE retorna string."""
    user = Usuario.objects.create_user(
        username="user1", email="user@x.com", password="x", cpf="11111111111"
    )

    client = APIClient()
    client.force_authenticate(user=user)

    url = reverse("core:features")
    res = client.get(url)

    assert res.status_code == 200
    data = res.json()

    assert isinstance(data["GCAL_MODE"], str)
    assert data["GCAL_MODE"] in ["fake", "google"], "GCAL_MODE deve ser 'fake' ou 'google'"


# ============================================================================
# TESTES DE SUPERUSER
# ============================================================================


def test_features_superuser_has_access():
    """Superuser tem acesso a /api/features/."""
    user = Usuario.objects.create_superuser(
        username="admin", email="admin@x.com", password="x", cpf="99999999999"
    )

    client = APIClient()
    client.force_authenticate(user=user)

    url = reverse("core:features")
    res = client.get(url)

    assert res.status_code == 200, "Superuser deve ter acesso a features"
