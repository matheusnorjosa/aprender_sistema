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
    assert resposta_api.data["code"] == "ACCOUNT_LOCKED"
    assert not _entrou(_admin(admin, superusuario.username, _SENHA), admin)


def _grafias_do_cpf(cpf: str) -> list[str]:
    """Grafias que o ``normalize_login_identifier`` aceita e que o ``redact_cpf`` não pega."""
    return [
        f"{cpf[:9]}-{cpf[9:]}",
        f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:]}",
        f"{cpf[:3]} {cpf[3:6]} {cpf[6:9]} {cpf[9:]}",
        f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]} - {cpf[9:]}",
    ]


@pytest.mark.parametrize("canal", ["api", "admin"])
@pytest.mark.parametrize("indice_grafia", range(4))
@override_settings(ACCOUNT_LOCKOUT_THRESHOLD=10)
def test_auditlog_redige_cpf_em_qualquer_grafia_aceita_no_login(canal, indice_grafia, superusuario):
    """LOGIN_FAILED e LOGIN_BLOCKED nunca guardam o CPF, em qualquer grafia que autentica."""
    grafia = _grafias_do_cpf(superusuario.cpf)[indice_grafia]

    def tentar() -> None:
        if canal == "api":
            assert _api(APIClient(), grafia, _ERRADA).status_code == 400
        else:
            assert _admin(Client(), grafia, _ERRADA).status_code == 200

    tentar()
    _bloquear(superusuario.cpf)
    tentar()

    logs = AuditLog.objects.filter(action__in=[AuditLog.Action.LOGIN_FAILED, AuditLog.Action.LOGIN_BLOCKED])
    assert {log.action for log in logs} == {AuditLog.Action.LOGIN_FAILED, AuditLog.Action.LOGIN_BLOCKED}
    for log in logs:
        assert log.details["username"] == "<cpf>"


@override_settings(ACCOUNT_LOCKOUT_THRESHOLD=10)
def test_admin_login_certo_zera_o_contador_como_na_api(superusuario):
    """Depois de 9 erros e 1 acerto no admin, 1 erro a mais não bloqueia a conta."""
    bucket = _lockout_bucket(superusuario.username)
    for _ in range(9):
        assert _admin(Client(), superusuario.username, _ERRADA).status_code == 200
    assert _get_failed_attempts(bucket, _IP) == 9

    client = Client()
    assert _entrou(_admin(client, superusuario.username, _SENHA), client)
    assert _get_failed_attempts(bucket, _IP) == 0

    assert _admin(Client(), superusuario.username, _ERRADA).status_code == 200
    client = Client()
    assert _entrou(_admin(client, superusuario.username, _SENHA), client)


# ===================================================================
# Login pelo username com formato de CPF diferente do campo cpf
# ===================================================================


@pytest.fixture
def username_diferente_do_cpf() -> Any:
    """Conta cujo username tem 11 dígitos mas difere do campo cpf (ex.: CPF corrigido
    depois pelo botão 'Alterar CPF', com o username travado)."""
    usuario = UsuarioFactory(superuser=True, password=_SENHA)
    usuario.username = "9" + usuario.cpf[1:]
    usuario.save(update_fields=["username"])
    assert usuario.username != usuario.cpf
    return usuario


@pytest.mark.parametrize("campo", ["username", "cpf"])
def test_api_entra_pelo_username_com_formato_de_cpf_e_pelo_cpf(campo, username_diferente_do_cpf):
    identificador = getattr(username_diferente_do_cpf, campo)
    assert _api(APIClient(), identificador, _SENHA).status_code == 200


@pytest.mark.parametrize("campo", ["username", "cpf"])
def test_admin_entra_pelo_username_com_formato_de_cpf_e_pelo_cpf(campo, username_diferente_do_cpf):
    client = Client()
    assert _entrou(_admin(client, getattr(username_diferente_do_cpf, campo), _SENHA), client)


def test_username_com_formato_de_cpf_custa_um_hash_so(username_diferente_do_cpf):
    """O fallback por username (CPF não achado) não soma hash: continua 1 (C7)."""
    assert _contar_hashes(lambda: _api(APIClient(), username_diferente_do_cpf.username, _ERRADA)) == 1


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
    assert resposta.data["code"] == "ACCOUNT_LOCKED"


@override_settings(ACCOUNT_LOCKOUT_THRESHOLD=10)
def test_admin_conta_bloqueada_nao_chama_authenticate(superusuario):
    _bloquear(superusuario.username)
    client = Client()
    with patch("django.contrib.auth.forms.authenticate", return_value=None) as autenticar:
        resposta = _admin(client, superusuario.username, _SENHA)
    autenticar.assert_not_called()
    assert not _entrou(resposta, client)


def _sem_csrf(html: str) -> str:
    """Tira o token CSRF, que muda a cada cliente, para comparar o resto da página."""
    return re.sub(r'name="csrfmiddlewaretoken" value="[^"]*"', 'name="csrfmiddlewaretoken"', html)


@override_settings(ACCOUNT_LOCKOUT_THRESHOLD=10)
def test_admin_conta_bloqueada_responde_igual_a_senha_errada(superusuario):
    """C2: conta bloqueada recebe a mesma resposta da senha errada (status, erro do
    formulário e página), para a resposta não denunciar o bloqueio."""
    senha_errada = _admin(Client(), superusuario.username, _ERRADA)
    _bloquear(superusuario.username)
    bloqueada = _admin(Client(), superusuario.username, _SENHA)

    assert bloqueada.status_code == senha_errada.status_code == 200
    erros = bloqueada.context["form"].errors.get_json_data()
    assert erros  # controle: a tentativa bloqueada mostra erro de fato
    assert erros == senha_errada.context["form"].errors.get_json_data()
    assert _sem_csrf(bloqueada.content.decode()) == _sem_csrf(senha_errada.content.decode())


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


def test_nginx_limita_so_o_login_do_admin_com_zona_propria_e_mais_baixa_que_a_api():
    """A zona baixa vale só para /admin/login/; navegar no admin (autocomplete do select2
    a cada tecla, jsi18n, salvar) segue na zona da API e não leva 429 no meio do trabalho."""
    conf = (exige_raiz_do_repo() / "v2" / "frontend" / "nginx.conf").read_text(encoding="utf-8")

    login = _location(conf, "location = /admin/login/")
    m = re.search(r"limit_req\s+zone=(\w+)", login)
    assert m, "location /admin/login/ sem limit_req"
    zona = m.group(1)
    assert zona != "api"
    assert _taxa_por_segundo(conf, zona) < _taxa_por_segundo(conf, "api")
    assert "proxy_pass" in login

    # A zona do login não vaza para o resto do admin, para a API nem para os estáticos.
    resto_do_admin = _location(conf, "location ^~ /admin/")
    assert f"zone={zona}" not in resto_do_admin
    assert "limit_req zone=api" in resto_do_admin
    assert f"zone={zona}" not in _location(conf, "location ^~ /api/")
    assert "limit_req" not in _location(conf, "location ^~ /static/")
