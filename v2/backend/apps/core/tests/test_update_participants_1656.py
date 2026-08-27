"""
#1656 / D6 — reconciliação de participantes no UPDATE (perform_update).

`_update_formadores` tinha dois defeitos confirmados (crosscheck 2026-08-26):
- NÃO filtrava `is_active` (o create filtra) → um usuário INATIVO (ex.: pessoa
  desligada ainda marcada ativa) voltava a ser anexado como FORMADOR no PATCH;
- era assimétrico: reconciliava só FORMADOR, nunca COORD_ACOMPANHA.

Contrato: o UPDATE reconcilia FORMADOR e COORD_ACOMPANHA por id, e só adiciona
usuários ATIVOS (espelha `_create_participants`). Guests por e-mail não são
reconciliados aqui (só no create) — ver D6c.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOptionalSubscript=false

from __future__ import annotations

import itertools
from datetime import date, timedelta

from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import Compra, Participation
from apps.core.tests.factories import (
    GroupFactory,
    MunicipioFactory,
    ProjetoFactory,
    TipoEventoFactory,
    UsuarioFactory,
)

pytestmark = pytest.mark.django_db

_HASH = itertools.count(1)
_CPF = itertools.count(78000000001)


@pytest.fixture
def coordenador():
    user = UsuarioFactory(username="coord_1656", cpf=str(next(_CPF)))
    user.groups.add(GroupFactory(name="Coordenador"))
    return user


@pytest.fixture
def municipio():
    return MunicipioFactory(nome="Fortaleza 1656", uf="CE", ativo=True)


@pytest.fixture
def tipo_evento():
    return TipoEventoFactory(nome="Formacao M1656")


@pytest.fixture
def projeto(municipio):
    proj = ProjetoFactory(nome="Projeto 1656", codigo="P1656", fluxo="NAO_SUPER", ativo=True)
    # #1738: criar exige Compra para o par município+projeto.
    Compra.objects.create(
        codigo="C-1656",
        projeto=proj,
        municipio=municipio,
        quantidade=1,
        data=date(2026, 3, 1),
        uso="teste",
        external_hash=f"{next(_HASH):064d}",
    )
    return proj


@pytest.fixture
def client_coord(coordenador):
    c = APIClient()
    c.force_authenticate(coordenador)
    return c


def _formador(n):
    u = UsuarioFactory(username=f"form_1656_{n}", cpf=str(next(_CPF)))
    u.groups.add(GroupFactory(name="Formador"))
    return u


def _create_sol(client, municipio, projeto, tipo_evento, extra):
    inicio = timezone.now() + timedelta(days=3)
    resp = client.post(
        "/api/solicitacoes/",
        {
            "municipio": municipio.id,
            "projeto": projeto.id,
            "tipo_evento": tipo_evento.id,
            "tipo": "PRESENCIAL",
            "inicio": inicio.isoformat(),
            "fim": (inicio + timedelta(hours=2)).isoformat(),
            "extra_participants": extra,
        },
        format="json",
    )
    assert resp.status_code == 201, resp.data
    return resp.json()["id"]


def _ids(sol_id, role):
    return set(
        Participation.objects.filter(solicitacao_id=sol_id, role=role, usuario_id__isnull=False).values_list(
            "usuario_id", flat=True
        )
    )


class TestUpdateFiltersInactive:
    def test_inactive_formador_not_added_on_update(self, client_coord, municipio, projeto, tipo_evento):
        """RED: o UPDATE não filtrava is_active → um formador INATIVO é anexado no PATCH."""
        ativo = _formador("a")
        inativo = UsuarioFactory(username="form_1656_inativo", cpf=str(next(_CPF)), is_active=False)
        sol_id = _create_sol(client_coord, municipio, projeto, tipo_evento, {"formador_ids": [ativo.id]})

        resp = client_coord.patch(
            f"/api/solicitacoes/{sol_id}/",
            {"extra_participants": {"formador_ids": [ativo.id, inativo.id]}},
            format="json",
        )
        assert resp.status_code in (200, 202), resp.data
        formadores = _ids(sol_id, "FORMADOR")
        assert ativo.id in formadores
        assert inativo.id not in formadores, "usuário INATIVO não pode ser anexado como formador no update"


class TestUpdateReconcilesCoordAcompanha:
    def test_coord_acompanha_replaced_on_update(self, client_coord, municipio, projeto, tipo_evento):
        """RED: _update_formadores nunca reconciliava COORD_ACOMPANHA."""
        coord_a = _formador("ca")
        coord_b = _formador("cb")
        sol_id = _create_sol(client_coord, municipio, projeto, tipo_evento, {"coord_acompanha_ids": [coord_a.id]})
        assert _ids(sol_id, "COORD_ACOMPANHA") == {coord_a.id}

        resp = client_coord.patch(
            f"/api/solicitacoes/{sol_id}/",
            {"extra_participants": {"coord_acompanha_ids": [coord_b.id]}},
            format="json",
        )
        assert resp.status_code in (200, 202), resp.data
        assert _ids(sol_id, "COORD_ACOMPANHA") == {coord_b.id}, "update deve reconciliar COORD_ACOMPANHA (troca A→B)"


class TestUpdateReconcilesFormadores:
    def test_formadores_add_remove_still_works(self, client_coord, municipio, projeto, tipo_evento):
        """Não-regressão: reconciliação de FORMADOR por id (add/remove) segue funcionando."""
        f_a = _formador("na")
        f_b = _formador("nb")
        sol_id = _create_sol(client_coord, municipio, projeto, tipo_evento, {"formador_ids": [f_a.id]})
        assert _ids(sol_id, "FORMADOR") == {f_a.id}

        resp = client_coord.patch(
            f"/api/solicitacoes/{sol_id}/",
            {"extra_participants": {"formador_ids": [f_b.id]}},
            format="json",
        )
        assert resp.status_code in (200, 202), resp.data
        assert _ids(sol_id, "FORMADOR") == {f_b.id}
