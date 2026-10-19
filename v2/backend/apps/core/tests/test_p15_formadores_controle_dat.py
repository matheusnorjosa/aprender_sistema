"""
P15 (regressão, item 22 da lista de liberação, 19/10/2026): Controle e DAT veem os formadores de todas
as gerências em `/api/options/formadores-do-setor/` e no seletor de Deslocamentos
(`/api/deslocamentos/alvos/`). Resolvido no PR 9 (`formadores_do_setor` com `tem_capacidade_global`).

Desde o PR 12 o poder vem só da lotação: o DAT e o Controle daqui têm só o vínculo EQUIPE na gerência
do perfil, sem grupo.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false

from __future__ import annotations

from django.core.cache import cache
from rest_framework.test import APIClient

import pytest

from apps.core.tests.factories import (
    GerenciaFactory,
    UsuarioFactory,
    com_pacote_do_controle,
    com_pacote_do_dat,
    com_papel,
)

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _cache_limpo():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def formadores():
    """Um formador em cada uma de duas gerências; nenhuma é a do DAT nem a do Controle."""
    lista = []
    for _ in range(2):
        formador = UsuarioFactory(groups__vinculo=False)
        com_papel(formador, "FORMADOR", GerenciaFactory())
        lista.append(formador)
    return lista


def _dat_equipe():
    user = UsuarioFactory(groups=None, groups__vinculo=False)
    com_pacote_do_dat(user)
    return user


def _controle_equipe():
    user = UsuarioFactory(groups=None, groups__vinculo=False)
    com_pacote_do_controle(user)
    return user


def _ids(user, rota: str) -> set[int]:
    client = APIClient()
    client.force_authenticate(user)
    resp = client.get(rota)
    assert resp.status_code == 200, resp.content
    return {item["id"] for item in resp.data}


def test_formadores_do_setor_dat_equipe_ve_todos(formadores):
    assert _ids(_dat_equipe(), "/api/options/formadores-do-setor/") >= {f.id for f in formadores}


def test_formadores_do_setor_controle_equipe_ve_todos(formadores):
    assert _ids(_controle_equipe(), "/api/options/formadores-do-setor/") >= {f.id for f in formadores}


@pytest.mark.parametrize("pessoa", [_dat_equipe, _controle_equipe], ids=["DAT", "Controle"])
def test_alvos_de_deslocamento_trazem_os_formadores_de_todas_as_gerencias(formadores, pessoa):
    assert _ids(pessoa(), "/api/deslocamentos/alvos/") >= {f.id for f in formadores}


def test_sem_lotacao_nao_ve_formadores(formadores):
    """Controle negativo: conta sem vínculo não vê ninguém (a lista cheia acima vem da lotação)."""
    user = UsuarioFactory(groups=None, groups__vinculo=False)
    assert _ids(user, "/api/options/formadores-do-setor/") == set()
    assert _ids(user, "/api/deslocamentos/alvos/") == set()


@pytest.mark.parametrize("rota", ["/api/options/formadores-do-setor/", "/api/deslocamentos/alvos/"])
def test_resposta_so_traz_id_e_nome(formadores, rota):
    """O docstring de `formadores_do_setor_options` mostrava e-mail; a resposta não leva (SEC-ENUM-01)."""
    client = APIClient()
    client.force_authenticate(_dat_equipe())
    resp = client.get(rota)
    assert resp.status_code == 200, resp.content
    assert resp.data
    assert all(set(item) == {"id", "first_name", "last_name"} for item in resp.data)
