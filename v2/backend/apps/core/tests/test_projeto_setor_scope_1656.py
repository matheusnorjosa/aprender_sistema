"""
#1656 / Wave 1 (Slice 2) — escopo do PROJETO pela GERÊNCIA do criador.

Regra (PR 9 das permissões, 16/10/2026): o coordenador REGULAR só vê/escolhe projetos das
gerências onde atua (papel GERENTE, COORDENADOR ou APOIO vigente em gerência ativa;
`EquipeGerencia.gerencias_de_atuacao`). Projeto de outra gerência → 400 (o FE só mostra os da
gerência via `/lookup/projetos/`; o backend é o gate).

Fail-closed (antes era fail-open por setor):
- projeto SEM gerência → 400 no create/update e fora do lookup;
- `Projeto.setor` e `Gerencia.setor_canonico` não dão escopo;
- global/privilegiado (superuser, Superintendência, Controle, DAT) → isento.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportMissingTypeStubs=false

from __future__ import annotations

import itertools
from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.tests.factories import (
    GerenciaFactory,
    MunicipioFactory,
    ProjetoFactory,
    TipoEventoFactory,
    UsuarioFactory,
    com_papel,
    liberar_par,
)

pytestmark = pytest.mark.django_db

_CPF = itertools.count(79300000001)


def _projeto_com_compra(nome, codigo, gerencia, municipio):
    proj = ProjetoFactory(nome=nome, codigo=codigo, gerencia=gerencia, fluxo="NAO_SUPER", ativo=True)
    liberar_par(municipio, proj)
    return proj


@pytest.fixture
def municipio():
    return MunicipioFactory(nome="Mun projeto-setor 1656", uf="CE", ativo=True)


@pytest.fixture
def tipo_evento():
    return TipoEventoFactory(nome="Formacao proj-setor 1656")


@pytest.fixture
def gerencias():
    return {"vidas": GerenciaFactory(nome="G-Vidas-S2"), "fluir": GerenciaFactory(nome="G-Fluir-S2")}


@pytest.fixture
def coordenador(gerencias):
    u = UsuarioFactory(username="coord_proj_1656", cpf=str(next(_CPF)))
    com_papel(u, "COORDENADOR", gerencias["vidas"])
    return u


@pytest.fixture
def projetos(municipio, gerencias):
    # O "SS" no lugar de "S2" vem de quando o ProjetoLookup escondia nome terminado em dígito.
    # Hoje quem esconde é a marca `Projeto.eh_serie`; o nome ficou.
    return {
        "vidas": _projeto_com_compra("Proj Vidas SS", "PVID-S2", gerencias["vidas"], municipio),
        "fluir": _projeto_com_compra("Proj Fluir SS", "PFLU-S2", gerencias["fluir"], municipio),
        "sem_gerencia": _projeto_com_compra("Proj Sem Gerencia SS", "PSEM-S2", None, municipio),
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
        "coordenador_acompanha": False,
        "tipo": "PRESENCIAL",
        "inicio": inicio.isoformat(),
        "fim": (inicio + timedelta(hours=2)).isoformat(),
    }


def _erros(resp):
    """Campos com erro de um 400 (o handler embrulha em `errors`)."""
    return resp.data.get("errors", resp.data)


class TestCreateProjetoScope:
    def test_cross_gerencia_projeto_rejected(self, coordenador, projetos, municipio, tipo_evento):
        """Coordenadora da gerência Vidas NÃO cria solicitação em projeto da gerência Fluir."""
        resp = _client(coordenador).post(
            "/api/solicitacoes/", _payload(municipio, projetos["fluir"], tipo_evento), format="json"
        )
        assert (
            resp.status_code == 400
        ), f"esperava 400 (projeto de outra gerência), veio {resp.status_code}: {resp.data}"
        assert "projeto" in _erros(resp)

    def test_same_gerencia_projeto_allowed(self, coordenador, projetos, municipio, tipo_evento):
        resp = _client(coordenador).post(
            "/api/solicitacoes/", _payload(municipio, projetos["vidas"], tipo_evento), format="json"
        )
        assert resp.status_code == 201, resp.data

    def test_projeto_sem_gerencia_rejected_fail_closed(self, coordenador, projetos, municipio, tipo_evento):
        """PR 9: projeto sem gerência não é de ninguém → 400 (antes, sem setor, era fail-open)."""
        resp = _client(coordenador).post(
            "/api/solicitacoes/", _payload(municipio, projetos["sem_gerencia"], tipo_evento), format="json"
        )
        assert resp.status_code == 400, resp.data
        assert "projeto" in _erros(resp)


class TestPrivilegedExemptProjeto:
    def test_superuser_may_use_cross_gerencia_projeto(self, projetos, municipio, tipo_evento):
        su = UsuarioFactory(username="su_proj_1656", cpf=str(next(_CPF)), superuser=True)
        payload = _payload(municipio, projetos["fluir"], tipo_evento)
        payload["coordenador"] = UsuarioFactory(groups=["Coordenador"]).id  # 05/10/2026: responsável obrigatório
        resp = _client(su).post("/api/solicitacoes/", payload, format="json")
        assert resp.status_code == 201, resp.data


class TestProjetoLookupScope:
    def _ids(self, resp):
        return {item["id"] for item in resp.json()}

    def test_regular_coordenador_lookup_only_own_gerencia(self, coordenador, projetos):
        resp = _client(coordenador).get("/api/lookup/projetos/")
        assert resp.status_code == 200, resp.data
        ids = self._ids(resp)
        assert projetos["vidas"].id in ids, "projeto da mesma gerência aparece"
        assert projetos["sem_gerencia"].id not in ids, "projeto sem gerência NÃO aparece (fail-closed)"
        assert projetos["fluir"].id not in ids, "projeto de outra gerência NÃO aparece p/ coordenador regular"

    def test_superuser_lookup_sees_all(self, projetos):
        su = UsuarioFactory(username="su_projlk_1656", cpf=str(next(_CPF)), superuser=True)
        resp = _client(su).get("/api/lookup/projetos/")
        assert resp.status_code == 200, resp.data
        assert {projetos["vidas"].id, projetos["fluir"].id, projetos["sem_gerencia"].id} <= self._ids(resp)


class TestUpdateProjetoScope:
    def test_change_to_cross_gerencia_projeto_rejected(self, coordenador, projetos, municipio, tipo_evento):
        """Trocar o projeto para um de outra gerência no PATCH → 400."""
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
        ), f"esperava 400 no update cross-gerência de projeto, veio {patch.status_code}: {patch.data}"
        assert "projeto" in _erros(patch)
