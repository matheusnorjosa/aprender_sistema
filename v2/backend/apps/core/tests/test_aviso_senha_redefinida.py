"""
F1 do scan de segurança (16/10/2026) — aviso à pessoa cuja senha foi redefinida por outra.

Decisão do dono (S4, 16/10): o DAT continua podendo redefinir a senha de qualquer conta que não
seja de superusuário. Em troca, a dona da conta fica sabendo: no próximo acesso (a tela de troca
obrigatória) o `/api/me/` traz `aviso_senha_redefinida = {"por": <rótulo>, "em": "dd/mm/aaaa"}`.
O aviso some quando ela define a própria senha. Sem dado pessoal além do rótulo de quem redefiniu
(o mesmo das telas: nome, ou "Usuario #id"; nunca CPF, login ou e-mail).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false

from __future__ import annotations

from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import Usuario
from apps.core.rbac.policies import can_admin_mutate_target
from apps.core.tests.factories import GroupFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

SENHA_RECEBIDA = "Provisoria#2026"
SENHA_NOVA = "Girassol#Azul77"


@pytest.fixture
def dat() -> Usuario:
    user = UsuarioFactory(first_name="Pessoa", last_name="Do Dat")
    user.groups.add(GroupFactory(name="DAT"))
    return user


def _redefinir(ator: Usuario, alvo: Usuario, senha: str = SENHA_RECEBIDA):
    client = APIClient()
    client.force_authenticate(ator)
    resp = client.patch(f"/api/usuarios-admin/{alvo.id}/", {"password": senha}, format="json")
    assert resp.status_code == 200, resp.content
    return resp


def _me(usuario: Usuario) -> dict:
    # force_login: a conta marcada passa pelo middleware da troca obrigatória, que libera o /me.
    # refresh: a sessão leva o hash da senha; o objeto em memória ainda tem o de antes da redefinição.
    usuario.refresh_from_db()
    client = APIClient()
    client.force_login(usuario)
    resp = client.get("/api/me/")
    assert resp.status_code == 200
    return resp.json()


def test_quem_teve_a_senha_redefinida_ve_quem_e_quando(dat):
    alvo = UsuarioFactory()
    _redefinir(dat, alvo)

    aviso = _me(alvo)["aviso_senha_redefinida"]

    assert aviso == {"por": "Pessoa Do Dat", "em": timezone.localdate().strftime("%d/%m/%Y")}


def test_rotulo_de_quem_redefiniu_sem_nome_nao_traz_cpf_login_nem_email():
    ator = UsuarioFactory(first_name="", last_name="", username="52998224725", cpf="52998224725")
    ator.groups.add(GroupFactory(name="DAT"))
    alvo = UsuarioFactory()
    _redefinir(ator, alvo)

    aviso = _me(alvo)["aviso_senha_redefinida"]

    assert aviso["por"] == f"Usuario #{ator.pk}"
    assert ator.cpf not in str(aviso)
    assert ator.email not in str(aviso)


def test_sem_redefinicao_nao_ha_aviso():
    assert _me(UsuarioFactory())["aviso_senha_redefinida"] is None


def test_conta_nova_criada_com_senha_nao_ganha_aviso(dat):
    client = APIClient()
    client.force_authenticate(dat)
    resp = client.post(
        "/api/usuarios-admin/",
        {
            "username": "conta_nova",
            "email": "conta.nova@example.invalid",
            "cpf": "10000000009",
            "password": SENHA_RECEBIDA,
        },
        format="json",
    )
    assert resp.status_code == 201, resp.content
    assert _me(Usuario.objects.get(username="conta_nova"))["aviso_senha_redefinida"] is None


def test_quem_troca_a_propria_senha_pela_rota_admin_nao_ganha_aviso():
    superusuario = UsuarioFactory(superuser=True)
    _redefinir(superusuario, superusuario, SENHA_NOVA)
    assert _me(superusuario)["aviso_senha_redefinida"] is None


def test_aviso_some_quando_a_pessoa_define_a_propria_senha(dat):
    alvo = UsuarioFactory()
    _redefinir(dat, alvo)
    alvo.refresh_from_db()
    client = APIClient()
    client.force_login(alvo)

    resp = client.post(
        "/api/me/change-password/", {"old_password": SENHA_RECEBIDA, "new_password": SENHA_NOVA}, format="json"
    )

    assert resp.status_code == 200, resp.content
    assert client.get("/api/me/").json()["aviso_senha_redefinida"] is None


def test_aviso_nao_e_gravavel_pela_api(dat):
    alvo = UsuarioFactory()
    client = APIClient()
    client.force_authenticate(dat)
    client.patch(
        f"/api/usuarios-admin/{alvo.id}/",
        {"senha_redefinida_por": dat.id, "senha_redefinida_em": "2026-10-01T10:00:00Z", "cargo": "Formadora"},
        format="json",
    )
    assert _me(alvo)["aviso_senha_redefinida"] is None


def test_dat_continua_redefinindo_conta_com_capacidade_que_ele_nao_tem():
    """Decisão S4 (PR 10): a política não restringe por capacidade; só barra superusuário."""
    ator = UsuarioFactory()
    ator.groups.add(GroupFactory(name="DAT"))
    alvo = UsuarioFactory()
    alvo.groups.add(GroupFactory(name="Controle"))
    assert can_admin_mutate_target(ator, alvo) is True
    assert can_admin_mutate_target(ator, UsuarioFactory(superuser=True)) is False
