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
from django.test import TestCase, override_settings
from rest_framework import serializers
from rest_framework.test import APIClient

import pytest

from apps.core.models import AuditLog, Usuario
from apps.core.serializers.usuario import UsuarioAdminSerializer
from apps.core.tests.factories import GroupFactory, UsuarioFactory, com_pacote_do_dat
from apps.core.views_auth import _get_lockout_key, _lockout_bucket

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


def _patch_senha(ator: Usuario, alvo: Usuario):
    client = APIClient()
    client.force_authenticate(ator)
    # A limpeza do bloqueio roda no commit da transação; o teste vive dentro de uma que nunca comita.
    with TestCase.captureOnCommitCallbacks(execute=True):
        return client.patch(f"/api/usuarios-admin/{alvo.pk}/", {"password": SENHA_NOVA}, format="json")


def _redefinir(ator: Usuario, alvo: Usuario) -> None:
    resp = _patch_senha(ator, alvo)
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
    assert not resp.has_header("Retry-After")


def test_username_com_cpf_de_outra_conta_nao_desbloqueia_a_outra(dat):
    """S1: o DAT dá à conta B o CPF do superusuário (com máscara) como login; redefinir a senha de B
    não pode zerar o bloqueio do superusuário, que cai no mesmo balde."""
    superusuario = UsuarioFactory(username=CPF, cpf=CPF, is_superuser=True, password=SENHA_ANTIGA)
    alvo = UsuarioFactory(username="529.982.247-25", cpf="11144477735", password=SENHA_ANTIGA)
    _errar_ate_bloquear(superusuario.cpf)

    _redefinir(dat, alvo)

    assert _entrar(superusuario.cpf, SENHA_ANTIGA).data["code"] == "ACCOUNT_LOCKED"


def test_username_com_o_proprio_cpf_mascarado_continua_desbloqueando(dat):
    alvo = UsuarioFactory(username="111.444.777-35", cpf="11144477735", password=SENHA_ANTIGA)
    _errar_ate_bloquear(alvo.username)

    _redefinir(dat, alvo)

    assert _entrar(alvo.username, SENHA_NOVA).status_code == 200


def test_redefinir_que_falha_na_lotacao_nao_desbloqueia():
    """S2: se o salvar é recusado depois da senha (a lotação recusa), a senha e a auditoria voltam;
    o bloqueio também precisa continuar."""
    superusuario = UsuarioFactory(is_superuser=True, is_staff=True)
    alvo = UsuarioFactory(cpf=CPF, password=SENHA_ANTIGA)
    _errar_ate_bloquear(CPF)

    recusa = serializers.ValidationError({"gerencia_id": "recusado"})
    with patch.object(UsuarioAdminSerializer, "_apply_lotacao", side_effect=recusa):
        resp = _patch_senha(superusuario, alvo)

    assert resp.status_code == 400, resp.content
    assert _entrar(CPF, SENHA_ANTIGA).data["code"] == "ACCOUNT_LOCKED"


@patch("apps.core.views_auth._GLOBAL_LOCKOUT_THRESHOLD", 3)
def test_retry_after_usa_o_maior_prazo_entre_as_chaves_que_bloqueiam():
    """R1: bloqueado pela chave global (30 min); a chave deste IP existe, abaixo do limite e com
    prazo curto. O aviso não pode sair com o prazo do IP."""
    bucket = _lockout_bucket(CPF)
    cache.set(_get_lockout_key(bucket, IP_CASA), 1, timeout=60)
    cache.set(_get_lockout_key(bucket), 3, timeout=1800)

    resp = _entrar(CPF, SENHA_ANTIGA, IP_CASA)

    assert resp.data["code"] == "ACCOUNT_LOCKED"
    assert int(resp["Retry-After"]) > 60
