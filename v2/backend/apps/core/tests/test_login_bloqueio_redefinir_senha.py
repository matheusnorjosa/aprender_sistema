"""Item 38 (ensaio r2, 20/10/2026): bloqueio do login e senha redefinida pelo DAT.

1. Redefinir a senha pelo DAT não desbloqueava a conta: os contadores de erro (por conta+IP e o
   global da conta) seguiam valendo até 15 min depois do 1º erro, e a pessoa com a senha nova
   continuava recusada. A tela do DAT diz "A nova senha entra em vigor imediatamente."
2. A conta bloqueada recebia a MESMA frase da senha errada, inclusive com a senha certa. Agora a
   resposta diz que é bloqueio (`code = ACCOUNT_LOCKED` + `Retry-After`). Não revela se a conta
   existe: o bloqueio conta erros pelo identificador digitado, exista ele ou não.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false

from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import patch

from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient

import pytest

from apps.core.models import AuditLog, Usuario
from apps.core.tests.factories import GroupFactory, UsuarioFactory, com_pacote_do_dat

pytestmark = pytest.mark.django_db

SENHA_ANTIGA = "Antiga#2026x"
SENHA_NOVA = "Provisoria#2026"
CPF = "52998224725"
IP_CASA = "10.0.0.1"
IP_ESCRITORIO = "10.0.0.2"


@pytest.fixture(autouse=True)
def _cache_limpo_e_sem_throttle() -> Iterator[None]:
    cache.clear()
    with (
        patch("apps.core.views_auth.LoginThrottle.allow_request", return_value=True),
        override_settings(NUM_PROXIES=0, ACCOUNT_LOCKOUT_THRESHOLD=2, ACCOUNT_LOCKOUT_DURATION=900),
    ):
        yield
    cache.clear()


@pytest.fixture
def dat() -> Usuario:
    user = UsuarioFactory(first_name="Pessoa", last_name="Do Dat")
    user.groups.add(GroupFactory(name="DAT"))
    com_pacote_do_dat(user)
    return user


def _entrar(identificador: str, senha: str, ip: str = IP_CASA):
    return APIClient().post(
        "/api/auth/login/", {"username": identificador, "password": senha}, format="json", REMOTE_ADDR=ip
    )


def _errar_ate_bloquear(identificador: str, ip: str = IP_CASA) -> None:
    for _ in range(2):
        assert _entrar(identificador, "errada", ip).status_code == 400


def _redefinir(ator: Usuario, alvo: Usuario) -> None:
    client = APIClient()
    client.force_authenticate(ator)
    resp = client.patch(f"/api/usuarios-admin/{alvo.pk}/", {"password": SENHA_NOVA}, format="json")
    assert resp.status_code == 200, resp.content


def test_redefinir_pelo_dat_desbloqueia_a_conta_em_todo_ip_e_pelos_dois_identificadores(dat):
    alvo = UsuarioFactory(username=f"login_{CPF}", cpf=CPF, password=SENHA_ANTIGA)
    _errar_ate_bloquear(CPF, IP_CASA)
    _errar_ate_bloquear(alvo.username, IP_ESCRITORIO)
    assert _entrar(CPF, SENHA_ANTIGA, IP_CASA).data["code"] == "ACCOUNT_LOCKED"

    _redefinir(dat, alvo)

    assert _entrar(CPF, SENHA_NOVA, IP_CASA).status_code == 200
    assert _entrar(alvo.username, SENHA_NOVA, IP_ESCRITORIO).status_code == 200


@patch("apps.core.views_auth._GLOBAL_LOCKOUT_THRESHOLD", 3)
def test_redefinir_zera_tambem_o_bloqueio_global_da_conta(dat):
    alvo = UsuarioFactory(cpf=CPF, password=SENHA_ANTIGA)
    for ip in ("10.0.1.1", "10.0.1.2", "10.0.1.3"):
        _entrar(CPF, "errada", ip)
    assert _entrar(CPF, SENHA_ANTIGA, "10.0.1.9").data["code"] == "ACCOUNT_LOCKED"

    _redefinir(dat, alvo)

    assert _entrar(CPF, SENHA_NOVA, "10.0.1.9").status_code == 200


def test_redefinir_uma_conta_nao_desbloqueia_outra(dat):
    alvo = UsuarioFactory(password=SENHA_ANTIGA)
    outra = UsuarioFactory(password=SENHA_ANTIGA)
    _errar_ate_bloquear(alvo.username)
    _errar_ate_bloquear(outra.username)

    _redefinir(dat, alvo)

    assert _entrar(outra.username, SENHA_ANTIGA).data["code"] == "ACCOUNT_LOCKED"


def test_bloqueio_tem_resposta_propria_igual_para_conta_que_existe_e_que_nao_existe():
    existente = UsuarioFactory(password=SENHA_ANTIGA)
    _errar_ate_bloquear(existente.username)
    _errar_ate_bloquear("ninguem_tem_este_login")

    com_conta = _entrar(existente.username, SENHA_ANTIGA)  # senha certa: ainda bloqueada
    sem_conta = _entrar("ninguem_tem_este_login", SENHA_ANTIGA)

    assert com_conta.status_code == sem_conta.status_code == 400
    assert com_conta.data == sem_conta.data
    assert com_conta.data["code"] == "ACCOUNT_LOCKED"
    assert 0 < int(com_conta["Retry-After"]) <= 900
    assert 0 < int(sem_conta["Retry-After"]) <= 900
    assert AuditLog.objects.filter(action=AuditLog.Action.LOGIN_BLOCKED).count() == 2


def test_senha_errada_sem_bloqueio_continua_com_a_resposta_generica():
    existente = UsuarioFactory(password=SENHA_ANTIGA)

    resp = _entrar(existente.username, "errada")

    assert resp.status_code == 400
    assert resp.data == {"error": "Credenciais inválidas."}
    assert "Retry-After" not in resp
