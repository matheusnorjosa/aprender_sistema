"""
#1656 / Wave 1 (Slice 2) — escopo do PROJETO por SETOR do criador.

Regra (decidida pelo dono; mesma do S1, eixo projeto): o coordenador REGULAR só
vê/escolhe projetos do próprio SETOR (`Projeto.setor` == `Gerencia.setor_canonico`
de alguma gerência vigente do criador). Projeto de outro setor → 400 (o FE só mostra
os do setor via `/lookup/projetos/`; o backend é o gate).

Fail-open (transição/dado incompleto, espelha o S1):
- criador SEM setor → não escopa;
- projeto SEM setor → pegável por qualquer um (Projeto.setor é gap conhecido, 21/128 no dev);
- global/privilegiado (superuser, Superintendência, Controle, DAT) → isento.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportMissingTypeStubs=false

from __future__ import annotations

import itertools
from datetime import date, timedelta

from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import Compra, EquipeGerencia, Gerencia
from apps.core.tests.factories import GroupFactory, MunicipioFactory, ProjetoFactory, TipoEventoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

_HASH = itertools.count(1)
_CPF = itertools.count(79300000001)


def _gerencia(nome, setor):
    return Gerencia.objects.create(nome=nome, setor_canonico=setor)


def _projeto_com_compra(nome, codigo, setor, municipio):
    proj = ProjetoFactory(nome=nome, codigo=codigo, setor=setor, fluxo="NAO_SUPER", ativo=True)
    Compra.objects.create(
        codigo=f"C-{codigo}",
        projeto=proj,
        municipio=municipio,
        quantidade=1,
        data=date(2026, 3, 1),
        uso="teste",
        external_hash=f"{next(_HASH):064d}",
    )
    return proj


@pytest.fixture
def municipio():
    return MunicipioFactory(nome="Mun projeto-setor 1656", uf="CE", ativo=True)


@pytest.fixture
def tipo_evento():
    return TipoEventoFactory(nome="Formacao proj-setor 1656")


@pytest.fixture
def gerencias():
    return {"vidas": _gerencia("G-Vidas-S2", "Vidas"), "fluir": _gerencia("G-Fluir-S2", "Fluir")}


@pytest.fixture
def coordenador(gerencias):
    u = UsuarioFactory(username="coord_proj_1656", cpf=str(next(_CPF)))
    u.groups.add(GroupFactory(name="Coordenador"))
    EquipeGerencia.objects.create(usuario=u, gerencia=gerencias["vidas"], papel="COORDENADOR", ativo=True)
    return u


@pytest.fixture
def projetos(municipio):
    # ⚑ nomes NÃO podem terminar em dígito: ProjetoLookup exclui "kits" por
    # `nome__regex=[0-9]+$` (views_lookup.py). Por isso "SS", não "S2".
    return {
        "vidas": _projeto_com_compra("Proj Vidas SS", "PVID-S2", "Vidas", municipio),
        "fluir": _projeto_com_compra("Proj Fluir SS", "PFLU-S2", "Fluir", municipio),
        "sem_setor": _projeto_com_compra("Proj Sem Setor SS", "PSEM-S2", "", municipio),
    }


def _client(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


def _payload(municipio, projeto, tipo_evento):
    inicio = timezone.now() + timedelta(days=3)
    return {
        "municipio": municipio.id,
        "projeto": projeto.id,
        "tipo_evento": tipo_evento.id,
        "tipo": "PRESENCIAL",
        "inicio": inicio.isoformat(),
        "fim": (inicio + timedelta(hours=2)).isoformat(),
    }


class TestCreateProjetoScope:
    def test_cross_setor_projeto_rejected(self, coordenador, projetos, municipio, tipo_evento):
        """RED: criador do setor Vidas NÃO pode criar solicitação de projeto do setor Fluir."""
        resp = _client(coordenador).post(
            "/api/solicitacoes/", _payload(municipio, projetos["fluir"], tipo_evento), format="json"
        )
        assert resp.status_code == 400, f"esperava 400 (projeto de outro setor), veio {resp.status_code}: {resp.data}"

    def test_same_setor_projeto_allowed(self, coordenador, projetos, municipio, tipo_evento):
        resp = _client(coordenador).post(
            "/api/solicitacoes/", _payload(municipio, projetos["vidas"], tipo_evento), format="json"
        )
        assert resp.status_code == 201, resp.data

    def test_projeto_sem_setor_allowed_fail_open(self, coordenador, projetos, municipio, tipo_evento):
        resp = _client(coordenador).post(
            "/api/solicitacoes/", _payload(municipio, projetos["sem_setor"], tipo_evento), format="json"
        )
        assert resp.status_code == 201, resp.data


class TestPrivilegedExemptProjeto:
    def test_superuser_may_use_cross_setor_projeto(self, projetos, municipio, tipo_evento):
        su = UsuarioFactory(username="su_proj_1656", cpf=str(next(_CPF)), superuser=True)
        resp = _client(su).post(
            "/api/solicitacoes/", _payload(municipio, projetos["fluir"], tipo_evento), format="json"
        )
        assert resp.status_code == 201, resp.data


class TestProjetoLookupScope:
    def _ids(self, resp):
        return {item["id"] for item in resp.json()}

    def test_regular_coordenador_lookup_only_own_setor_plus_setorless(self, coordenador, projetos):
        resp = _client(coordenador).get("/api/lookup/projetos/")
        assert resp.status_code == 200, resp.data
        ids = self._ids(resp)
        assert projetos["vidas"].id in ids, "projeto do mesmo setor aparece"
        assert projetos["sem_setor"].id in ids, "projeto sem setor aparece (fail-open)"
        assert projetos["fluir"].id not in ids, "projeto de outro setor NÃO aparece p/ coordenador regular"

    def test_superuser_lookup_sees_all(self, projetos):
        su = UsuarioFactory(username="su_projlk_1656", cpf=str(next(_CPF)), superuser=True)
        resp = _client(su).get("/api/lookup/projetos/")
        assert resp.status_code == 200, resp.data
        assert {projetos["vidas"].id, projetos["fluir"].id, projetos["sem_setor"].id} <= self._ids(resp)


class TestUpdateProjetoScope:
    def test_change_to_cross_setor_projeto_rejected(self, coordenador, projetos, municipio, tipo_evento):
        """RED: trocar o projeto para um de outro setor no PATCH → 400."""
        resp = _client(coordenador).post(
            "/api/solicitacoes/", _payload(municipio, projetos["vidas"], tipo_evento), format="json"
        )
        assert resp.status_code == 201, resp.data
        sol_id = resp.json()["id"]
        patch = _client(coordenador).patch(
            f"/api/solicitacoes/{sol_id}/", {"projeto": projetos["fluir"].id}, format="json"
        )
        assert (
            patch.status_code == 400
        ), f"esperava 400 no update cross-setor de projeto, veio {patch.status_code}: {patch.data}"
