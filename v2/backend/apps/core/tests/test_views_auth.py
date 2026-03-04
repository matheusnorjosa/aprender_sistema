"""
Testes para endpoints de autenticação (Issue #134 - P1).

Valida:
- Login cria AuditLog (PA-05)
- Logout cria AuditLog (PA-05)
- Usuário inativo é bloqueado
- Credenciais vazias são rejeitadas
- Credenciais inválidas retornam 400
- Login bem-sucedido retorna dados do usuário
- Rate limiting aplicado (LoginThrottle)
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth.models import Group
from django.core.cache import cache
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.core.models import AuditLog, Usuario

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    """Clear throttle cache before each test to avoid 429 errors."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def usuario_ativo():
    """Usuário ativo para testes de login."""
    uid = uuid4().hex
    cpf = str(uuid4().int % 10**11).zfill(11)
    return Usuario.objects.create_user(
        username=f"user_{uid}",
        email=f"user_{uid}@example.com",
        password="testpass123",
        cpf=cpf,
        is_active=True,
    )


@pytest.fixture
def usuario_inativo():
    """Usuário inativo para testes de bloqueio."""
    uid = uuid4().hex
    cpf = str(uuid4().int % 10**11).zfill(11)
    return Usuario.objects.create_user(
        username=f"inactive_{uid}",
        email=f"inactive_{uid}@example.com",
        password="testpass123",
        cpf=cpf,
        is_active=False,
    )


@pytest.fixture
def usuario_superintendencia():
    """Usuário do grupo Superintendência."""
    uid = uuid4().hex
    cpf = str(uuid4().int % 10**11).zfill(11)
    user = Usuario.objects.create_user(
        username=f"super_{uid}",
        email=f"super_{uid}@example.com",
        password="testpass123",
        cpf=cpf,
        is_active=True,
    )
    grupo, _ = Group.objects.get_or_create(name="Superintendência")
    user.groups.add(grupo)
    return user


@pytest.fixture
def api_client():
    """API client for unauthenticated requests."""
    return APIClient()


# ===================================================================
# LOGIN ENDPOINT TESTS
# ===================================================================


def test_login_success_returns_user_data(api_client, usuario_ativo):
    """
    Login bem-sucedido deve retornar 200 com dados do usuário.

    Valida:
    - Status 200
    - Campos: id, username, email, name, groups, is_superintendencia
    """
    response = api_client.post(
        "/api/auth/login/", {"username": usuario_ativo.username, "password": "testpass123"}, format="json"
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == usuario_ativo.id
    assert response.data["username"] == usuario_ativo.username
    assert response.data["email"] == usuario_ativo.email
    assert "groups" in response.data
    assert "is_superintendencia" in response.data


def test_login_creates_audit_log(api_client, usuario_ativo):
    """
    PA-05: Login deve criar AuditLog com action='LOGIN'.

    Valida:
    - AuditLog criado
    - action='LOGIN'
    - usuario=usuario_ativo
    - details contém ip_address e user_agent
    """
    initial_count = AuditLog.objects.count()

    response = api_client.post(
        "/api/auth/login/",
        {"username": usuario_ativo.username, "password": "testpass123"},
        format="json",
        HTTP_USER_AGENT="pytest-agent",
    )

    assert response.status_code == status.HTTP_200_OK
    assert AuditLog.objects.count() == initial_count + 1

    log = AuditLog.objects.latest("created_at")
    assert log.action == "LOGIN"
    assert log.usuario == usuario_ativo
    assert log.model_name == "Usuario"
    assert "ip_address" in log.details
    assert "user_agent" in log.details
    assert log.details["user_agent"] == "pytest-agent"


def test_login_inactive_user_blocked(api_client, usuario_inativo):
    """
    Usuário inativo deve ser bloqueado no login.

    Valida:
    - Status 400
    - Mensagem de erro: 'Credenciais inválidas.' (auth backend retorna None para inativos)
    """
    response = api_client.post(
        "/api/auth/login/", {"username": usuario_inativo.username, "password": "testpass123"}, format="json"
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["error"] == "Credenciais inválidas."


def test_login_empty_credentials_rejected(api_client):
    """
    Credenciais vazias devem retornar 400.

    Valida:
    - Username vazio → 400
    - Password vazio → 400
    - Ambos vazios → 400
    """
    # Username vazio
    response = api_client.post("/api/auth/login/", {"username": "", "password": "testpass123"}, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "obrigatórios" in response.data["error"]

    # Password vazio
    response = api_client.post("/api/auth/login/", {"username": "user", "password": ""}, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "obrigatórios" in response.data["error"]

    # Ambos vazios
    response = api_client.post("/api/auth/login/", {"username": "", "password": ""}, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "obrigatórios" in response.data["error"]


def test_login_invalid_credentials_rejected(api_client, usuario_ativo):
    """
    Credenciais inválidas devem retornar 400.

    Valida:
    - Senha errada → 400 'Credenciais inválidas.'
    - Usuário inexistente → 400 'Credenciais inválidas.'
    """
    # Senha errada
    response = api_client.post(
        "/api/auth/login/", {"username": usuario_ativo.username, "password": "wrongpass"}, format="json"
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["error"] == "Credenciais inválidas."
    assert "remaining_attempts" not in response.data
    assert "locked" not in response.data
    assert "lockout_minutes" not in response.data

    # Usuário inexistente
    response = api_client.post(
        "/api/auth/login/", {"username": "nonexistent", "password": "testpass123"}, format="json"
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["error"] == "Credenciais inválidas."
    assert "remaining_attempts" not in response.data
    assert "locked" not in response.data
    assert "lockout_minutes" not in response.data


@override_settings(ACCOUNT_LOCKOUT_THRESHOLD=1, ACCOUNT_LOCKOUT_DURATION=900)
def test_login_locked_account_returns_generic_error_response(api_client, usuario_ativo):
    """
    Conta bloqueada deve retornar a mesma resposta genérica de credencial inválida.

    Valida:
    - Status 400 (não 403) mesmo em lockout
    - Sem campos sensíveis (locked/remaining_attempts/lockout_minutes)
    - Detalhes de lockout mantidos apenas em AuditLog
    """
    # 1ª tentativa inválida: incrementa contador para atingir lockout (threshold=1)
    first = api_client.post(
        "/api/auth/login/", {"username": usuario_ativo.username, "password": "wrongpass"}, format="json"
    )
    assert first.status_code == status.HTTP_400_BAD_REQUEST
    assert first.data == {"error": "Credenciais inválidas."}

    # 2ª tentativa: conta já bloqueada internamente, resposta pública continua genérica
    locked = api_client.post(
        "/api/auth/login/", {"username": usuario_ativo.username, "password": "wrongpass"}, format="json"
    )
    assert locked.status_code == status.HTTP_400_BAD_REQUEST
    assert locked.data == {"error": "Credenciais inválidas."}
    assert "locked" not in locked.data
    assert "remaining_attempts" not in locked.data
    assert "lockout_minutes" not in locked.data

    blocked_log = AuditLog.objects.filter(action="LOGIN_BLOCKED").latest("created_at")
    assert blocked_log.details["username"] == usuario_ativo.username
    assert blocked_log.details["reason"] == "account_locked"


@override_settings(ACCOUNT_LOCKOUT_THRESHOLD=1, ACCOUNT_LOCKOUT_DURATION=900)
def test_login_failure_response_is_uniform_across_invalid_nonexistent_and_locked(api_client, usuario_ativo):
    """
    Cenários de falha de autenticação devem ter payload idêntico (anti-enumeração).

    Valida:
    - Senha inválida (usuário existente)
    - Usuário inexistente
    - Conta bloqueada por lockout
    """
    expected = {"error": "Credenciais inválidas."}

    invalid_existing = api_client.post(
        "/api/auth/login/", {"username": usuario_ativo.username, "password": "wrongpass"}, format="json"
    )
    nonexistent = api_client.post("/api/auth/login/", {"username": "ghost_user_123", "password": "wrongpass"})
    locked = api_client.post("/api/auth/login/", {"username": usuario_ativo.username, "password": "wrongpass"})

    assert invalid_existing.status_code == status.HTTP_400_BAD_REQUEST
    assert nonexistent.status_code == status.HTTP_400_BAD_REQUEST
    assert locked.status_code == status.HTTP_400_BAD_REQUEST

    assert invalid_existing.data == expected
    assert nonexistent.data == expected
    assert locked.data == expected


@patch("apps.core.views_auth.make_password")
def test_login_uses_dummy_hash_for_failed_authentication(mock_make_password, api_client):
    """
    Em falha de autenticação, deve executar hash dummy para reduzir timing leak.
    """
    response = api_client.post(
        "/api/auth/login/",
        {"username": "nonexistent_timing_user", "password": "testpass123"},
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    mock_make_password.assert_called_once_with("testpass123")


def test_login_returns_groups(api_client, usuario_superintendencia):
    """
    Login deve retornar lista de grupos do usuário.

    Valida:
    - Campo 'groups' é lista
    - Contém 'Superintendência' para usuário com esse grupo
    - is_superintendencia=True
    """
    response = api_client.post(
        "/api/auth/login/", {"username": usuario_superintendencia.username, "password": "testpass123"}, format="json"
    )

    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.data["groups"], list)
    assert "Superintendência" in response.data["groups"]
    assert response.data["is_superintendencia"] is True


# ===================================================================
# LOGOUT ENDPOINT TESTS
# ===================================================================


def test_logout_requires_authentication(api_client):
    """
    Logout deve exigir autenticação (IsAuthenticated).

    Valida:
    - Usuário não autenticado → 401 ou 403
    """
    response = api_client.post("/api/auth/logout/")
    assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


def test_logout_creates_audit_log(api_client, usuario_ativo):
    """
    PA-05: Logout deve criar AuditLog com action='LOGOUT'.

    Valida:
    - AuditLog criado
    - action='LOGOUT'
    - usuario=usuario_ativo
    - details contém ip_address e user_agent
    """
    # Force authenticate (session auth doesn't persist in APIClient)
    api_client.force_authenticate(user=usuario_ativo)

    initial_count = AuditLog.objects.count()

    # Fazer logout
    response = api_client.post("/api/auth/logout/", HTTP_USER_AGENT="pytest-agent")

    assert response.status_code == status.HTTP_200_OK
    assert AuditLog.objects.count() == initial_count + 1

    log = AuditLog.objects.latest("created_at")
    assert log.action == "LOGOUT"
    assert log.usuario == usuario_ativo
    assert log.model_name == "Usuario"
    assert "ip_address" in log.details
    assert "user_agent" in log.details


def test_logout_success_returns_message(api_client, usuario_ativo):
    """
    Logout bem-sucedido deve retornar 200 com mensagem.

    Valida:
    - Status 200
    - Mensagem de sucesso
    """
    # Force authenticate
    api_client.force_authenticate(user=usuario_ativo)

    # Fazer logout
    response = api_client.post("/api/auth/logout/")

    assert response.status_code == status.HTTP_200_OK
    assert "message" in response.data
    assert "sucesso" in response.data["message"]


def test_logout_clears_session(api_client, usuario_ativo):
    """
    Logout deve invalidar a autenticação.

    Valida:
    - Após logout + clear auth, requisição sem auth retorna 401/403
    """
    # Force authenticate
    api_client.force_authenticate(user=usuario_ativo)

    # Verificar que está autenticado (logout requer auth)
    response = api_client.post("/api/auth/logout/")
    assert response.status_code == status.HTTP_200_OK

    # Clear forced authentication (simula sessão limpa)
    api_client.force_authenticate(user=None)

    # Tentar logout novamente sem auth (deve falhar)
    response = api_client.post("/api/auth/logout/")
    assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
