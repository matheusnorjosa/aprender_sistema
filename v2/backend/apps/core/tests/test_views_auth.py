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

import threading
from unittest.mock import patch
from uuid import uuid4

from django.core.cache import cache
from django.test import override_settings
from rest_framework import status
from rest_framework.request import Request
from rest_framework.test import APIClient, APIRequestFactory

import pytest

from apps.core.models import AuditLog
from apps.core.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db

# CPF válido (mod-11) fixo para os testes de bucket de lockout — as três grafias
# abaixo canonicalizam para o MESMO identificador.
_CPF_CRU = "11144477735"
_CPF_MASCARA = "111.444.777-35"
_CPF_ESPACOS = "111 444 777 35"


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
    return UsuarioFactory(
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
    return UsuarioFactory(
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
    return UsuarioFactory(
        username=f"super_{uid}",
        email=f"super_{uid}@example.com",
        password="testpass123",
        cpf=cpf,
        is_active=True,
        groups=["Superintendência"],
    )


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


@pytest.mark.parametrize("cpf_username", ["11144477735", "111.444.777-35"])
def test_login_failed_redige_cpf_no_details_username(api_client, cpf_username):
    """M03-10 (#1657): CPF usado como username em login falho NAO pode ser gravado em
    claro no AuditLog.details (PII-at-rest, LGPD art. 46). Redige na ESCRITA, nas duas
    formas (cru e formatado)."""
    resp = api_client.post("/api/auth/login/", {"username": cpf_username, "password": "wrongpass"}, format="json")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    log = AuditLog.objects.filter(action="LOGIN_FAILED").latest("created_at")
    assert log.details["username"] == "<cpf>"
    assert cpf_username not in str(log.details)


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


# ===================================================================
# M03-03 (#1614) — LOCKOUT/THROTTLE NÃO EVADÍVEIS
# ===================================================================


@pytest.fixture
def usuario_cpf_conhecido():
    """Usuário com CPF fixo (mod-11 válido) para exercitar bucket de lockout por grafia."""
    uid = uuid4().hex
    return UsuarioFactory(
        username=f"cpfuser_{uid}",
        email=f"cpfuser_{uid}@example.com",
        password="testpass123",
        cpf=_CPF_CRU,
        is_active=True,
    )


def _post_login(client: APIClient, username: str, password: str):
    return client.post("/api/auth/login/", {"username": username, "password": password}, format="json")


@override_settings(ACCOUNT_LOCKOUT_THRESHOLD=10)
def test_lockout_compartilha_bucket_entre_grafias_do_mesmo_cpf(api_client, usuario_cpf_conhecido):
    """10 falhas no CPF cru devem bloquear TAMBÉM a grafia com máscara (mesmo bucket).

    RED (bug M03-03): cada grafia é um bucket independente → a senha correta na grafia
    mascarada autentica (200). GREEN: o bucket é derivado do identificador canônico →
    a conta está bloqueada e a resposta é a genérica 400.
    """
    # Bypass do throttle: este teste é sobre LOCKOUT (precisa de >10 POSTs). O rate de
    # login em CI é 10/min e mascararia o lockout com 429 — concerns separados.
    with patch("apps.core.views_auth.LoginThrottle.allow_request", return_value=True):
        for _ in range(10):
            resp = _post_login(api_client, _CPF_CRU, "wrongpass")
            assert resp.status_code == status.HTTP_400_BAD_REQUEST

        # Senha CORRETA, mas na grafia mascarada → deve estar bloqueado (mesmo bucket do CPF cru).
        locked = _post_login(api_client, _CPF_MASCARA, "testpass123")
    assert locked.status_code == status.HTTP_400_BAD_REQUEST
    assert locked.data == {"error": "Credenciais inválidas."}


@override_settings(ACCOUNT_LOCKOUT_THRESHOLD=100)  # isola o caminho GLOBAL (IP-path nunca dispara)
@patch("apps.core.views_auth._GLOBAL_LOCKOUT_THRESHOLD", 6)
def test_lockout_nao_e_evadido_por_espacos(api_client, usuario_cpf_conhecido):
    """Falhas espalhadas por grafias com espaços diferentes acumulam no MESMO bucket global.

    RED: 3 grafias × 2 falhas = 6 falhas, mas em 3 buckets distintos (máx 2 < 6) → a senha
    correta autentica (200). GREEN: colapsam no bucket canônico → global=6 → bloqueado (400).
    """
    grafias = [_CPF_ESPACOS, "11144 477 735", "1 1 1 4 4 4 7 7 7 3 5"]  # todas = 11144477735 (11 díg.)
    # Bypass do throttle (rate 10/min em CI mascararia o lockout global com 429).
    with patch("apps.core.views_auth.LoginThrottle.allow_request", return_value=True):
        for grafia in grafias:
            for _ in range(2):
                resp = _post_login(api_client, grafia, "wrongpass")
                assert resp.status_code == status.HTTP_400_BAD_REQUEST

        # 7ª tentativa — senha CORRETA no CPF cru → global lockout deve bloquear.
        locked = _post_login(api_client, _CPF_CRU, "testpass123")
    assert locked.status_code == status.HTTP_400_BAD_REQUEST


def test_login_throttle_keia_caller_autenticado_wiring():
    """WIRING/regressão: LoginThrottle.get_cache_key NUNCA retorna None (nem p/ autenticado).

    RED (AnonRateThrottle): retorna None quando request.user.is_authenticated → sem throttle.
    """
    from apps.core.views_auth import LoginThrottle

    class _Authed:
        is_authenticated = True

    raw = APIRequestFactory().post("/api/auth/login/", REMOTE_ADDR=f"10.0.0.{uuid4().int % 250}")
    req = Request(raw)
    req.user = _Authed()  # type: ignore[assignment]

    key = LoginThrottle().get_cache_key(req, view=object())
    assert key is not None


def test_login_throttla_caller_autenticado():
    """COMPORTAMENTAL (nível-classe, determinístico): caller autenticado É throttleado.

    Cache locmem dedicado + ident único + rate baixo distintivo (2/min) → imune ao
    cache.clear() paralelo. RED: autenticado nunca chaveia → [True, True, True].
    GREEN: chaveia por IP → [True, True, False].
    """
    from apps.core.views_auth import LoginThrottle

    class _Authed:
        is_authenticated = True

    unique_ip = f"172.16.0.{uuid4().int % 250}"
    cache_loc = f"throttle-authed-{uuid4().hex}"

    with override_settings(
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": cache_loc,
            }
        }
    ):
        throttle = LoginThrottle()
        throttle.rate = "2/minute"
        throttle.num_requests, throttle.duration = throttle.parse_rate("2/minute")
        view = object()

        results = []
        for _ in range(3):
            raw = APIRequestFactory().post("/api/auth/login/", REMOTE_ADDR=unique_ip)
            req = Request(raw)
            req.user = _Authed()  # type: ignore[assignment]
            results.append(throttle.allow_request(req, view))

    assert results == [True, True, False]


def test_incremento_concorrente_nao_perde_tentativa():
    """30 incrementos concorrentes de _safe_increment não podem perder tentativa.

    RED (_safe_increment = cache.get + cache.set, não atômico): contador < 30.
    GREEN (cache.add + cache.incr atômico do Redis): contador == 30.
    """
    from apps.core.views_auth import _safe_increment

    key = f"test_incr_concurrency_{uuid4().hex}"
    cache.delete(key)
    n_threads = 30
    barrier = threading.Barrier(n_threads)

    def worker():
        barrier.wait()  # dispara todas ~ao mesmo tempo p/ maximizar contenção
        _safe_increment(key, timeout=60)

    threads = [threading.Thread(target=worker) for _ in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert int(cache.get(key)) == n_threads
    cache.delete(key)


def test_login_rejeita_username_nao_string(api_client, usuario_cpf_conhecido):
    """Payload com username não-string deve retornar 400, nunca 500 (M03-12, mesma raiz).

    RED: authenticate(username=["a"]) → re.sub sobre lista → TypeError → 500.
    GREEN: validação de tipo na entrada → 400.
    """
    resp = api_client.post("/api/auth/login/", {"username": ["a"], "password": "testpass123"}, format="json")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
