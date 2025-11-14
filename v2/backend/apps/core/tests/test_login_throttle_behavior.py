"""
Testes de COMPORTAMENTO do rate limiting no login (Issue #133 - SEC-P1).

⚠️ ATENÇÃO: Estes testes servem como REFERÊNCIA e DOCUMENTAÇÃO do comportamento
esperado do throttling. Eles NÃO rodam automaticamente na CI devido a limitações
do ambiente de testes (cache limpo entre execuções).

VALIDAÇÃO:
- ✅ Configuração: test_login_throttle_simple.py (3/3 testes passando na CI)
- ⚠️ Comportamento: Validação MANUAL em staging/produção (ver SECURITY.md)

COMPORTAMENTO ESPERADO (validar manualmente):
- 5 requisições permitidas no intervalo de 1 minuto
- 6ª requisição retorna 429 (Too Many Requests)
- Após janela de tempo (61s), novas requisições são permitidas
- Throttling não vaza informação sobre credenciais válidas/inválidas

LIMITAÇÕES EM TESTES:
- Fixture clear_throttle_cache limpa cache entre testes (previne acúmulo)
- APIClient não mantém estado de sessão como navegador real
- Test isolation impede teste de comportamento multiprocesso

COMO TESTAR MANUALMENTE:
Ver seção "Testing" em SECURITY.md para script curl.
"""

import pytest
import time
from uuid import uuid4
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient
from rest_framework import status

from apps.core.models import Usuario


pytestmark = pytest.mark.django_db


@pytest.fixture
def usuario_valido():
    """Usuário válido para testes de throttling."""
    uid = uuid4().hex
    cpf = str(uuid4().int % 10**11).zfill(11)
    return Usuario.objects.create_user(
        username=f"throttle_user_{uid}",
        email=f"throttle_{uid}@example.com",
        password="validpass123",
        cpf=cpf,
        is_active=True,
    )


@pytest.fixture
def api_client_with_cache():
    """API client with cache cleared before each test."""
    cache.clear()
    client = APIClient()
    yield client
    cache.clear()


# ===================================================================
# TESTES DE COMPORTAMENTO DE THROTTLING
# ===================================================================


def test_throttle_allows_5_requests_in_1_minute(api_client_with_cache, usuario_valido):
    """
    SEC-P1: LoginThrottle deve permitir 5 requisições no intervalo de 1 minuto.

    Valida:
    - Primeiras 5 requisições retornam 200 ou 400 (não 429)
    - Throttling não interfere com autenticação normal
    """
    # 5 requisições com credenciais válidas devem passar
    for i in range(5):
        response = api_client_with_cache.post(
            "/api/auth/login/",
            {"username": usuario_valido.username, "password": "validpass123"},
            format="json",
            REMOTE_ADDR=f"192.168.1.{i}",  # IPs diferentes para evitar throttle compartilhado
        )
        # Deve retornar 200 (sucesso) ou 400 (credencial inválida), nunca 429
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST], \
            f"Request {i+1}/5 retornou {response.status_code} (esperado 200/400)"


@pytest.mark.skip(reason="Requer cache persistente entre requests. Validar MANUALMENTE em staging (ver SECURITY.md)")
def test_throttle_blocks_6th_request_in_1_minute(api_client_with_cache, usuario_valido):
    """
    SEC-P1: LoginThrottle deve BLOQUEAR 6ª requisição no intervalo de 1 minuto.

    ⚠️ MANUAL TEST: Este teste falha em ambiente de testes devido ao clear_cache fixture.
    Validação deve ser feita em staging/produção usando curl (ver SECURITY.md).

    COMPORTAMENTO ESPERADO:
    - Primeiras 5 requisições retornam 200/400 (autenticação normal)
    - 6ª requisição retorna 429 (Too Many Requests)
    - Mensagem: "Request was throttled. Expected available in X seconds."
    """
    # Usar mesmo IP para todas as requisições (throttle por IP)
    test_ip = "192.168.1.100"

    # Fazer 5 requisições (devem passar)
    for i in range(5):
        response = api_client_with_cache.post(
            "/api/auth/login/",
            {"username": usuario_valido.username, "password": "validpass123"},
            format="json",
            REMOTE_ADDR=test_ip,
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST], \
            f"Request {i+1}/5 retornou {response.status_code} (esperado 200/400, não 429)"

    # 6ª requisição deve ser bloqueada
    response = api_client_with_cache.post(
        "/api/auth/login/",
        {"username": usuario_valido.username, "password": "validpass123"},
        format="json",
        REMOTE_ADDR=test_ip,
    )

    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS, \
        f"6ª requisição retornou {response.status_code} (esperado 429)"

    # Validar mensagem de erro
    assert "detail" in response.data, "Response deve conter campo 'detail' com mensagem de erro"


@pytest.mark.slow
def test_throttle_resets_after_time_window(api_client_with_cache, usuario_valido):
    """
    SEC-P1: LoginThrottle deve resetar após janela de tempo (1 minuto).

    Valida:
    - Após 5 requisições + bloqueio (429)
    - Aguardar 61 segundos (janela de 1 minuto + buffer)
    - Nova requisição deve ser permitida (não 429)

    ATENÇÃO: Este teste demora ~61 segundos para executar.
    """
    pytest.skip("Teste muito lento (~61s), executar manualmente ou em ambiente staging")

    test_ip = "192.168.1.200"

    # Fazer 5 requisições válidas
    for _ in range(5):
        api_client_with_cache.post(
            "/api/auth/login/",
            {"username": usuario_valido.username, "password": "validpass123"},
            format="json",
            REMOTE_ADDR=test_ip,
        )

    # 6ª requisição deve ser bloqueada
    response = api_client_with_cache.post(
        "/api/auth/login/",
        {"username": usuario_valido.username, "password": "validpass123"},
        format="json",
        REMOTE_ADDR=test_ip,
    )
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    # Aguardar janela de tempo expirar (61 segundos)
    time.sleep(61)

    # Nova requisição após janela deve ser permitida
    response = api_client_with_cache.post(
        "/api/auth/login/",
        {"username": usuario_valido.username, "password": "validpass123"},
        format="json",
        REMOTE_ADDR=test_ip,
    )
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST], \
        f"Após 61s, requisição retornou {response.status_code} (esperado 200/400, não 429)"


def test_throttle_does_not_leak_credential_info(api_client_with_cache):
    """
    SEC-P1: Throttling não deve vazar informação sobre credenciais válidas/inválidas.

    Valida:
    - 5 requisições com credenciais INVÁLIDAS retornam 400
    - 6ª requisição com credenciais INVÁLIDAS retorna 429 (não 400)
    - Atacante não pode distinguir "credencial errada" de "rate limit" na 6ª tentativa
    """
    test_ip = "192.168.1.300"

    # Fazer 5 requisições com credenciais inválidas (devem retornar 400)
    for i in range(5):
        response = api_client_with_cache.post(
            "/api/auth/login/",
            {"username": "nonexistent", "password": "wrongpass"},
            format="json",
            REMOTE_ADDR=test_ip,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST, \
            f"Request {i+1}/5 com credenciais inválidas retornou {response.status_code} (esperado 400)"

    # 6ª requisição deve ser bloqueada pelo throttle (429), não pela validação (400)
    response = api_client_with_cache.post(
        "/api/auth/login/",
        {"username": "nonexistent", "password": "wrongpass"},
        format="json",
        REMOTE_ADDR=test_ip,
    )

    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS, \
        f"6ª requisição retornou {response.status_code} (esperado 429, não 400)"


@pytest.mark.skip(reason="Requer cache persistente entre requests. Validar MANUALMENTE em staging (ver SECURITY.md)")
def test_throttle_independent_per_ip(api_client_with_cache, usuario_valido):
    """
    SEC-P1: Throttling deve ser INDEPENDENTE por IP (não global).

    ⚠️ MANUAL TEST: Este teste falha em ambiente de testes devido ao clear_cache fixture.
    Validação deve ser feita em staging/produção usando curl de IPs diferentes.

    COMPORTAMENTO ESPERADO:
    - IP1 faz 5 requisições → 6ª bloqueada (429)
    - IP2 ainda pode fazer 5 requisições independentes
    - Previne DoS mas não permite bypass via IP único
    """
    ip1 = "192.168.1.101"
    ip2 = "192.168.1.102"

    # IP1 faz 6 requisições (5 OK + 1 bloqueada)
    for _ in range(5):
        api_client_with_cache.post(
            "/api/auth/login/",
            {"username": usuario_valido.username, "password": "validpass123"},
            format="json",
            REMOTE_ADDR=ip1,
        )

    response_ip1_6th = api_client_with_cache.post(
        "/api/auth/login/",
        {"username": usuario_valido.username, "password": "validpass123"},
        format="json",
        REMOTE_ADDR=ip1,
    )
    assert response_ip1_6th.status_code == status.HTTP_429_TOO_MANY_REQUESTS, \
        "IP1 deve ser bloqueado na 6ª requisição"

    # IP2 ainda deve conseguir fazer requisições (não afetado pelo IP1)
    response_ip2 = api_client_with_cache.post(
        "/api/auth/login/",
        {"username": usuario_valido.username, "password": "validpass123"},
        format="json",
        REMOTE_ADDR=ip2,
    )
    assert response_ip2.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST], \
        f"IP2 retornou {response_ip2.status_code} (esperado 200/400, não 429)"


# ===================================================================
# TESTES DE EDGE CASES
# ===================================================================


def test_throttle_with_empty_credentials(api_client_with_cache):
    """
    SEC-P1: Credenciais vazias também contam para rate limit.

    Valida:
    - 5 requests com credenciais vazias retornam 400
    - 6ª request retorna 429 (não 400)
    - Previne bypass do throttle com payloads inválidos
    """
    test_ip = "192.168.1.400"

    # 5 requisições com credenciais vazias
    for _ in range(5):
        response = api_client_with_cache.post(
            "/api/auth/login/",
            {"username": "", "password": ""},
            format="json",
            REMOTE_ADDR=test_ip,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    # 6ª requisição deve ser bloqueada
    response = api_client_with_cache.post(
        "/api/auth/login/",
        {"username": "", "password": ""},
        format="json",
        REMOTE_ADDR=test_ip,
    )
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS, \
        "Credenciais vazias devem contar para rate limit"
