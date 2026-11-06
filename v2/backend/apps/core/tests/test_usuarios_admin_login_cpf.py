"""
Tela de Usuários (lote C do alinhamento, 06/11/2026): o login é o CPF e o e-mail de reserva não vai à tela.

- Criar conta grava `username = cpf`, mesmo se o pedido mandar outro login (D14).
- Trocar o CPF leva o login junto quando ele era o CPF antigo, na mesma transação e no mesmo registro de
  auditoria. Login que não era o CPF antigo fica como está.
- Login já usado por outra conta: 400 no CPF, não 500.
- O e-mail de reserva `<cpf>@placeholder.local` chega vazio à tela (D15). O login (o CPF) continua indo ao
  DAT por decisão do dono (05/11/2026).

Os CPFs aqui são sintéticos.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportIndexIssue=false, reportOptionalSubscript=false

from __future__ import annotations

from rest_framework.test import APIClient

import pytest

from apps.core.models import AuditLog, Usuario
from apps.core.tests.factories import UsuarioFactory, com_pacote_do_dat

pytestmark = pytest.mark.django_db

URL = "/api/usuarios-admin/"


def _client(user) -> APIClient:
    c = APIClient()
    c.force_authenticate(user)
    return c


@pytest.fixture
def root(db):
    return UsuarioFactory(superuser=True)


@pytest.fixture
def dat(db):
    user = UsuarioFactory()
    com_pacote_do_dat(user)
    return user


def test_criar_com_login_diferente_grava_o_cpf_como_login(root):
    resp = _client(root).post(
        URL,
        {"username": "joao.silva", "cpf": "10000000710", "email": "joao@example.invalid", "first_name": "Joao"},
        format="json",
    )

    assert resp.status_code == 201, resp.content
    assert Usuario.objects.get(pk=resp.data["id"]).username == "10000000710"


def test_criar_sem_login_grava_o_cpf_como_login(dat):
    resp = _client(dat).post(
        URL, {"cpf": "10000001163", "email": "ana@example.invalid", "first_name": "Ana"}, format="json"
    )

    assert resp.status_code == 201, resp.content
    assert Usuario.objects.get(pk=resp.data["id"]).username == "10000001163"


def test_criar_com_cpf_que_ja_e_login_de_outra_conta_da_400_no_cpf(root):
    UsuarioFactory(username="10000001830", cpf="10000002640")

    resp = _client(root).post(URL, {"cpf": "10000001830", "email": "x@example.invalid"}, format="json")

    assert resp.status_code == 400, resp.content
    assert "cpf" in resp.data["errors"]


def test_trocar_o_cpf_leva_o_login_junto_na_mesma_auditoria(root):
    alvo = UsuarioFactory(username="10000003450", cpf="10000003450")

    resp = _client(root).patch(f"{URL}{alvo.pk}/", {"cpf": "10000004260"}, format="json")

    assert resp.status_code == 200, resp.content
    alvo.refresh_from_db()
    assert (alvo.cpf, alvo.username) == ("10000004260", "10000004260")
    registro = AuditLog.objects.get(action=AuditLog.Action.UPDATE, details__target_user_id=alvo.pk)
    assert set(registro.details["campos"]) == {"cpf", "username"}


def test_trocar_o_cpf_com_o_form_reenviando_o_login_antigo_leva_o_login_junto(dat):
    alvo = UsuarioFactory(username="10000005070", cpf="10000005070")

    resp = _client(dat).patch(
        f"{URL}{alvo.pk}/", {"cpf": "10000005800", "username": "10000005070", "first_name": "Nova"}, format="json"
    )

    assert resp.status_code == 200, resp.content
    alvo.refresh_from_db()
    assert (alvo.cpf, alvo.username) == ("10000005800", "10000005800")


def test_login_que_nao_era_o_cpf_antigo_fica_como_esta(root):
    alvo = UsuarioFactory(username="login.antigo", cpf="10000006300")

    resp = _client(root).patch(f"{URL}{alvo.pk}/", {"cpf": "10000007110"}, format="json")

    assert resp.status_code == 200, resp.content
    alvo.refresh_from_db()
    assert (alvo.cpf, alvo.username) == ("10000007110", "login.antigo")


def test_trocar_o_cpf_para_um_login_de_outra_conta_da_400_e_nao_muda_nada(root):
    UsuarioFactory(username="10000008010", cpf="10000008700")
    alvo = UsuarioFactory(username="10000009180", cpf="10000009180")

    resp = _client(root).patch(f"{URL}{alvo.pk}/", {"cpf": "10000008010"}, format="json")

    assert resp.status_code == 400, resp.content
    assert "cpf" in resp.data["errors"]
    alvo.refresh_from_db()
    assert (alvo.cpf, alvo.username) == ("10000009180", "10000009180")


def test_email_de_reserva_chega_vazio_e_o_login_continua_indo_ao_dat(dat):
    alvo = UsuarioFactory(username="10000010170", cpf="10000010170", email="10000010170@placeholder.local")

    resp = _client(dat).get(f"{URL}{alvo.pk}/")

    assert resp.status_code == 200, resp.content
    assert resp.data["email"] == ""
    # Decisão do dono (05/11/2026): o login, que é o CPF, chega ao DAT.
    assert resp.data["username"] == "10000010170"


def test_email_de_verdade_chega_como_esta(dat):
    alvo = UsuarioFactory(email="maria@example.invalid")

    resp = _client(dat).get(f"{URL}{alvo.pk}/")

    assert resp.data["email"] == "maria@example.invalid"


def test_salvar_sem_mandar_email_mantem_o_de_reserva(dat):
    alvo = UsuarioFactory(username="10000011150", cpf="10000011150", email="10000011150@placeholder.local")

    resp = _client(dat).patch(f"{URL}{alvo.pk}/", {"first_name": "Nome"}, format="json")

    assert resp.status_code == 200, resp.content
    alvo.refresh_from_db()
    assert alvo.email == "10000011150@placeholder.local"
    assert resp.data["email"] == ""
