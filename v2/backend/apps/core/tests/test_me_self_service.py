"""LGPD art. 18 II/III — self-service do titular em /api/me/.

- II (acesso/confirmação): o titular vê os próprios cpf/telefone/cargo.
- III (correção): o titular corrige o próprio telefone (dado de contato), auditado.

Campos de identidade/organização (cpf, cargo, is_superuser, groups) NÃO são
autocorrigíveis pelo titular — o PATCH os ignora.
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportMissingParameterType=false, reportUnknownParameterType=false

from __future__ import annotations

from rest_framework.test import APIClient

import pytest

from apps.core.models import AuditLog
from apps.core.tests.factories import UsuarioFactory

ME_URL = "/api/me/"


@pytest.fixture
def titular():
    return UsuarioFactory(
        cpf="11144477735",
        username="11144477735",
        first_name="Maria",
        last_name="Souza",
        email="maria@aprendereditora.com.br",
        telefone="",
        cargo="Coordenadora",
    )


# ------------------------- art. 18-II: acesso -------------------------


@pytest.mark.django_db
def test_get_me_expoe_cpf_telefone_cargo_do_proprio_titular(titular):
    client = APIClient()
    client.force_authenticate(user=titular)

    resp = client.get(ME_URL)

    assert resp.status_code == 200
    data = resp.json()
    assert data["cpf"] == "11144477735"
    assert data["telefone"] == ""
    assert data["cargo"] == "Coordenadora"


@pytest.mark.django_db
def test_get_me_exige_autenticacao():
    resp = APIClient().get(ME_URL)
    assert resp.status_code in (401, 403)


# ------------------------- art. 18-III: correção -------------------------


@pytest.mark.django_db
def test_patch_me_corrige_telefone_e_audita(titular, django_capture_on_commit_callbacks):
    client = APIClient()
    client.force_authenticate(user=titular)

    # A trilha é emitida via transaction.on_commit (audita só se a mutação commitar —
    # sem trilha-fantasma). Capturamos + executamos os callbacks para vê-la no teste.
    with django_capture_on_commit_callbacks(execute=True):
        resp = client.patch(ME_URL, {"telefone": "(85) 99999-1234"}, format="json")

    assert resp.status_code == 200
    titular.refresh_from_db()
    assert titular.telefone == "(85) 99999-1234"
    # Trilha: o FATO da autocorreção é auditado (art. 18-III / accountability).
    assert AuditLog.objects.filter(usuario=titular, action=AuditLog.Action.USER_SELF_UPDATE).exists()


@pytest.mark.django_db
def test_patch_me_nao_altera_cpf_cargo_nem_privilegio(titular):
    client = APIClient()
    client.force_authenticate(user=titular)

    resp = client.patch(
        ME_URL,
        {"cpf": "00000000000", "cargo": "Diretora", "is_superuser": True, "telefone": "1199"},
        format="json",
    )

    assert resp.status_code == 200
    titular.refresh_from_db()
    # Só telefone muda; identidade/organização/privilégio ficam intactos.
    assert titular.telefone == "1199"
    assert titular.cpf == "11144477735"
    assert titular.cargo == "Coordenadora"
    assert titular.is_superuser is False


@pytest.mark.django_db
def test_patch_me_exige_autenticacao():
    resp = APIClient().patch(ME_URL, {"telefone": "1199"}, format="json")
    assert resp.status_code in (401, 403)
