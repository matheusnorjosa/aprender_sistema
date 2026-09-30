"""
C1 (decisão 5 do dono, 30/09) — a lista de Usuários ordena pelo NOME, não pelo username.

Em produção o username é o CPF: ordenar por ele dá uma ordem que ninguém reconhece (e a
grade do C1 nem mostra essa chave). O `UsuarioAdminViewSet` só aceitava ordenar por
username/email/date_joined/id; o `OrderingFilter` descarta em silêncio os campos fora de
`ordering_fields` e ordena pelo que sobra (em `first_name,last_name,id`, só o id). Só sem
nenhum campo válido ele cai no padrão (username).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOptionalSubscript=false

from __future__ import annotations

from rest_framework.test import APIClient

import pytest

from apps.core.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db

# Ordem de criação (id), de username e de nome são três ordens diferentes: se o filtro
# descartar first_name/last_name (e ficar só com o id, ou cair no padrão username), a
# ordem sai errada. id: Carla, Ana, Bruno · username: Bruno, Carla, Ana · nome: Ana, Bruno, Carla.
PESSOAS = [
    ("ord_2", "Carla", "Alves"),
    ("ord_3", "Ana", "Souza"),
    ("ord_1", "Bruno", "Lima"),
]


@pytest.fixture
def superuser():
    return UsuarioFactory(username="zz_su_ordem", superuser=True)


@pytest.fixture
def pessoas():
    return [UsuarioFactory(username=u, first_name=f, last_name=s) for u, f, s in PESSOAS]


def test_ordering_por_nome_e_sobrenome(superuser, pessoas):
    client = APIClient()
    client.force_authenticate(superuser)
    resp = client.get("/api/usuarios-admin/?ordering=first_name,last_name,id&page_size=1000", secure=True)
    assert resp.status_code == 200
    nomes = [u["first_name"] for u in resp.data["results"] if u["username"].startswith("ord_")]
    assert nomes == ["Ana", "Bruno", "Carla"]
