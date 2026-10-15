"""
Login do admin com o mesmo bloqueio da API, sem senha testável em conta bloqueada e
com o mesmo custo de hash para CPF existente e inexistente.

Auditoria de segurança 2026-10-14, PR 1:
- C1: ``/admin/login/`` aceitava senhas sem limite, sem contar falha e sem
  ``LOGIN_FAILED`` no AuditLog.
- C2: com a conta bloqueada, ``authenticate()`` rodava antes do ``if is_locked``;
  o tempo de resposta denunciava a senha certa.
- C7: CPF inexistente custava menos hashes que CPF existente (enumeração por tempo).

Os CPFs daqui são sintéticos (sequência da factory), nunca de pessoa real.
"""

# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportArgumentType=false

from __future__ import annotations

import re
from collections.abc import Callable, Iterator
from typing import Any
from unittest.mock import patch

from django.contrib.auth.hashers import get_hasher
from django.core.cache import cache
from django.test import Client, override_settings
from rest_framework.test import APIClient

import pytest

from apps.core.models import AuditLog
from apps.core.tests.ambiente_repo import exige_raiz_do_repo
from apps.core.tests.factories import UsuarioFactory
from apps.core.views_auth import _get_failed_attempts, _increment_failed_attempts, _lockout_bucket

pytestmark = pytest.mark.django_db

_SENHA = "senha-certa-123"
_ERRADA = "senha-errada"
_IP = "127.0.0.1"  # REMOTE_ADDR do test client; sem X-Forwarded-For o resolvedor cai nele
_CPF_INEXISTENTE = "99999999999"


@pytest.fixture(autouse=True)
def _cache_limpo() -> Iterator[None]:
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def _sem_throttle_da_api() -> Iterator[None]:
    # O assunto é o bloqueio por conta; o throttle por IP da API é outro mecanismo.
    with patch("apps.core.views_auth.LoginThrottle.allow_request", return_value=True):
        yield


@pytest.fixture
def superusuario() -> Any:
    usuario = UsuarioFactory(superuser=True, password=_SENHA)
    usuario.username = usuario.cpf  # produção: username = CPF para todos
    usuario.save(update_fields=["username"])
    return usuario


def _admin(client: Client, username: str, senha: str) -> Any:
    return client.post("/admin/login/?next=/admin/", {"username": username, "password": senha})


def _api(client: APIClient, username: str, senha: str) -> Any:
    return client.post("/api/auth/login/", {"username": username, "password": senha}, format="json")


def _entrou(resposta: Any, client: Client) -> bool:
    return resposta.status_code == 302 and "_auth_user_id" in client.session


# ===================================================================
# C1 — /admin/login/ passa pelo mesmo bloqueio e registro da API
# ===================================================================


def test_admin_login_controle_positivo_senha_certa_entra(superusuario):
    """Controle: sem bloqueio, a senha certa entra no admin (302 + sessão)."""
    client = Client()
    assert _entrou(_admin(client, superusuario.username, _SENHA), client)


@override_settings(ACCOUNT_LOCKOUT_THRESHOLD=10)
def test_admin_login_11_falhas_bloqueia_audita_sem_cpf_e_senha_certa_nao_entra(superusuario):
    client = Client()
    for _ in range(11):
        resposta = _admin(client, superusuario.username, _ERRADA)
        assert resposta.status_code == 200  # formulário de volta, com erro

    falhas = AuditLog.objects.filter(action=AuditLog.Action.LOGIN_FAILED)
    assert falhas.count() == 10  # a 11ª já encontra a conta bloqueada
    for log in falhas:
        assert superusuario.cpf not in str(log.details)
        assert log.details["username"] == "<cpf>"
    assert AuditLog.objects.filter(action=AuditLog.Action.LOGIN_BLOCKED).count() == 1

    # 12º POST com a senha CERTA: a conta está bloqueada, não entra.
    resposta = _admin(client, superusuario.username, _SENHA)
    assert not _entrou(resposta, client)
    assert resposta.status_code == 200


@override_settings(ACCOUNT_LOCKOUT_THRESHOLD=10)
def test_api_e_admin_compartilham_o_contador_sem_contar_em_dobro(superusuario):
    api, admin = APIClient(), Client()
    bucket = _lockout_bucket(superusuario.username)

    for _ in range(5):
        assert _api(api, superusuario.username, _ERRADA).status_code == 400
    assert _get_failed_attempts(bucket, _IP) == 5  # uma falha da API conta UMA vez

    for _ in range(5):
        assert _admin(admin, superusuario.username, _ERRADA).status_code == 200
    assert _get_failed_attempts(bucket, _IP) == 10
    assert AuditLog.objects.filter(action=AuditLog.Action.LOGIN_FAILED).count() == 10

    # 6º erro no admin = 11ª tentativa: já bloqueada, não incrementa nem grava LOGIN_FAILED.
    assert _admin(admin, superusuario.username, _ERRADA).status_code == 200
    assert _get_failed_attempts(bucket, _IP) == 10

    # Bloqueio vale nos dois lados, com a senha certa.
    resposta_api = _api(api, superusuario.username, _SENHA)
    assert resposta_api.status_code == 400
    assert resposta_api.data == {"error": "Credenciais inválidas."}
    assert not _entrou(_admin(admin, superusuario.username, _SENHA), admin)


# ===================================================================
# C2 — conta bloqueada não chama authenticate()
# ===================================================================


def _bloquear(username: str) -> None:
    bucket = _lockout_bucket(username)
    for _ in range(10):
        _increment_failed_attempts(bucket, _IP)


@override_settings(ACCOUNT_LOCKOUT_THRESHOLD=10)
def test_api_conta_bloqueada_nao_chama_authenticate(superusuario):
    _bloquear(superusuario.username)
    with patch("apps.core.views_auth.authenticate", return_value=None) as autenticar:
        resposta = _api(APIClient(), superusuario.username, _SENHA)
    autenticar.assert_not_called()
    assert resposta.status_code == 400
    assert resposta.data == {"error": "Credenciais inválidas."}


@override_settings(ACCOUNT_LOCKOUT_THRESHOLD=10)
def test_admin_conta_bloqueada_nao_chama_authenticate(superusuario):
    _bloquear(superusuario.username)
    client = Client()
    with patch("django.contrib.auth.forms.authenticate", return_value=None) as autenticar:
        resposta = _admin(client, superusuario.username, _SENHA)
    autenticar.assert_not_called()
    assert not _entrou(resposta, client)


# ===================================================================
# C7 — mesmo número de hashes nos três casos
# ===================================================================


def _contar_hashes(acao: Callable[[], Any]) -> int:
    """Conta as chamadas a ``encode`` do hasher padrão (make_password, set_password e
    check_password passam todos por ele)."""
    classe = type(get_hasher("default"))
    original = classe.encode
    with patch.object(classe, "encode", autospec=True, side_effect=original) as encode:
        acao()
    return encode.call_count


@pytest.mark.parametrize("canal", ["api", "admin"])
@override_settings(ACCOUNT_LOCKOUT_THRESHOLD=10)
def test_mesmo_numero_de_hashes_para_inexistente_existente_e_bloqueada(canal, superusuario):
    def tentar(username: str) -> Callable[[], Any]:
        if canal == "api":
            return lambda: _api(APIClient(), username, _ERRADA)
        return lambda: _admin(Client(), username, _ERRADA)

    inexistente = _contar_hashes(tentar(_CPF_INEXISTENTE))
    username_inexistente = _contar_hashes(tentar("ninguem_com_este_login"))
    existente = _contar_hashes(tentar(superusuario.username))
    _bloquear(superusuario.username)
    bloqueada = _contar_hashes(tentar(superusuario.username))

    assert inexistente == username_inexistente == existente == bloqueada == 1


# ===================================================================
# C1 — nginx: limit_req com zona própria na location /admin/
# ===================================================================


def _location(conf: str, cabecalho: str) -> str:
    m = re.search(re.escape(cabecalho) + r"\s*\{(?P<corpo>[^{}]*)\}", conf)
    assert m, f"location não encontrada: {cabecalho}"
    return m.group("corpo")


def _taxa_por_segundo(conf: str, zona: str) -> float:
    m = re.search(rf"limit_req_zone\s+\$binary_remote_addr\s+zone={zona}:\w+\s+rate=(\d+)r/([sm]);", conf)
    assert m, f"limit_req_zone '{zona}' não declarada"
    return int(m.group(1)) / (60 if m.group(2) == "m" else 1)


def test_nginx_admin_tem_limit_req_com_zona_propria_e_mais_baixa_que_a_api():
    conf = (exige_raiz_do_repo() / "v2" / "frontend" / "nginx.conf").read_text(encoding="utf-8")

    admin = _location(conf, "location ^~ /admin/")
    m = re.search(r"limit_req\s+zone=(\w+)", admin)
    assert m, "location /admin/ sem limit_req"
    zona = m.group(1)
    assert zona != "api"
    assert _taxa_por_segundo(conf, zona) < _taxa_por_segundo(conf, "api")

    # A zona do admin não vaza para a API nem para os estáticos do admin.
    assert f"zone={zona}" not in _location(conf, "location ^~ /api/")
    assert "limit_req" not in _location(conf, "location ^~ /static/")
