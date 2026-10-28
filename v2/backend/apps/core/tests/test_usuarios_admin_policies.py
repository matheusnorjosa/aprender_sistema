"""
Resumo do perfil de acesso (ensaio r3, 28/10/2026): o que a pessoa vê no menu.

O form de Usuários mostrava "sem permissões específicas definidas" para um Formador, o que não diz
o que ele pode fazer. `GET /api/usuarios-admin/{id}/policies/` devolve as policies públicas da
pessoa pela MESMA regra de `GET /api/me/policies/` (`resolve_public_policies`), que é a fonte do
menu dela. Só leitura, com a permissão de sempre da tela (`manage_admin_registries`); a conta de
superusuário continua invisível para quem não é superusuário (404, P0-0). Nada muda o poder de ninguém.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportArgumentType=false

from __future__ import annotations

from rest_framework.test import APIClient

import pytest

from apps.core.rbac.policies import PUBLIC_POLICY_KEYS, resolve_public_policies
from apps.core.tests.factories import GroupFactory, UsuarioFactory, com_pacote_do_dat, com_papel

pytestmark = pytest.mark.django_db


@pytest.fixture
def dat():
    user = UsuarioFactory(username="dat_policies")
    user.groups.add(GroupFactory(name="DAT"))
    com_pacote_do_dat(user)
    return user


@pytest.fixture
def formador():
    user = UsuarioFactory(username="formador_policies")
    com_papel(user, "FORMADOR")
    return user


def _get(user, alvo):
    client = APIClient()
    client.force_authenticate(user)
    return client.get(f"/api/usuarios-admin/{alvo.pk}/policies/", secure=True)


def test_devolve_as_policies_da_pessoa_pela_regra_do_menu(dat, formador):
    resp = _get(dat, formador)

    assert resp.status_code == 200
    assert resp.data == resolve_public_policies(formador)
    # Só chaves do registro público, nunca codename de capacidade.
    assert set(resp.data) <= set(PUBLIC_POLICY_KEYS)


def test_admin_ve_as_proprias_policies_de_admin(dat):
    resp = _get(dat, dat)

    assert resp.status_code == 200
    assert "manage_admin_registries" in resp.data


def test_sem_a_permissao_da_tela_403(formador, dat):
    assert _get(formador, dat).status_code == 403


def test_conta_de_superusuario_continua_invisivel_para_o_dat(dat):
    alvo = UsuarioFactory(username="su_policies", superuser=True)

    assert _get(dat, alvo).status_code == 404
