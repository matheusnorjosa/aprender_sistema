"""
#1656 / M10-04 Wave 1 (Slice 1) — escopo do ALVO por GERÊNCIA em extra_participants.

Regra (PR 9 das permissões, 16/10/2026; P9-5 do dono): num evento da gerência A só entram pessoas
da A. O coordenador REGULAR só adiciona como formador quem tem vínculo vigente (papel ≠ EQUIPE) na
gerência DO PROJETO do evento, e só se ele mesmo atua nela (papel GERENTE, COORDENADOR ou APOIO
vigente; `participantes_fora_da_gerencia`). Fora disso = 400 em `extra_participants` (o FE só mostra
as opções da gerência via `/lookup/usuarios/`; o backend é o gate).

Nuances:
- Granularidade = GERÊNCIA do projeto (`projeto.gerencia_id`); `Gerencia.setor_canonico` não dá
  escopo (antes o setor colapsava gerências).
- Privilegiado/global (superuser, Superintendência, Controle, DAT) é ISENTO
  (`user_is_solicitacao_global`).
- Criador sem papel de atuação na gerência do projeto = fail-closed (antes, sem setor, era
  fail-open): não põe ninguém.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportMissingTypeStubs=false

from __future__ import annotations

import itertools
from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import Participation
from apps.core.tests.factories import (
    GerenciaFactory,
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
    com_papel,
    liberar_par,
)

pytestmark = pytest.mark.django_db

_CPF = itertools.count(79100000001)


def _formador(n, gerencia=None):
    u = UsuarioFactory(username=f"form_setor_{n}", cpf=str(next(_CPF)))
    com_papel(u, "FORMADOR", gerencia)
    return u


@pytest.fixture
def gerencias():
    return {"vidas": GerenciaFactory(nome="G-Vidas-1656"), "fluir": GerenciaFactory(nome="G-Fluir-1656")}


@pytest.fixture
def coordenador(gerencias):
    u = UsuarioFactory(username="coord_setor_1656", cpf=str(next(_CPF)))
    com_papel(u, "COORDENADOR", gerencias["vidas"])  # criador é da gerência Vidas
    return u


@pytest.fixture
def municipio():
    return MunicipioFactory(nome="Fortaleza setor 1656", uf="CE", ativo=True)


@pytest.fixture
def tipo_evento():
    return TipoEventoFactory(nome="Formacao setor 1656")


@pytest.fixture
def projeto(municipio, gerencias):
    """Projeto da gerência Vidas (a do coordenador)."""
    proj = ProjetoFactory(
        nome="Projeto setor 1656", codigo="PS1656", gerencia=gerencias["vidas"], fluxo="NAO_SUPER", ativo=True
    )
    liberar_par(municipio, proj)
    return proj


def _payload(municipio, projeto, tipo_evento, extra):
    inicio = timezone.now() + timedelta(days=3)
    return {
        "municipio": municipio.id,
        "projeto": projeto.id,
        "tipo_evento": tipo_evento.id,
        "coordenador_acompanha": False,
        "pretende_avaliar_formador": False,
        "tipo": "PRESENCIAL",
        "inicio": inicio.isoformat(),
        "fim": (inicio + timedelta(hours=2)).isoformat(),
        "extra_participants": extra,
    }


def _client(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


def _erros(resp):
    """Campos com erro de um 400 (o handler embrulha em `errors`)."""
    return resp.data.get("errors", resp.data)


class TestCreateGerenciaScope:
    def test_cross_gerencia_formador_rejected_on_create(self, coordenador, gerencias, municipio, projeto, tipo_evento):
        """Evento de projeto da gerência Vidas NÃO aceita formador da gerência Fluir."""
        outro = _formador("fluir", gerencias["fluir"])
        resp = _client(coordenador).post(
            "/api/solicitacoes/", _payload(municipio, projeto, tipo_evento, {"formador_ids": [outro.id]}), format="json"
        )
        assert (
            resp.status_code == 400
        ), f"esperava 400 (formador de outra gerência), veio {resp.status_code}: {resp.data}"
        assert "extra_participants" in _erros(resp)

    def test_same_gerencia_formador_allowed_on_create(self, coordenador, gerencias, municipio, projeto, tipo_evento):
        """Não-regressão: formador da MESMA gerência (Vidas) é aceito."""
        mesmo = _formador("vidas", gerencias["vidas"])
        resp = _client(coordenador).post(
            "/api/solicitacoes/", _payload(municipio, projeto, tipo_evento, {"formador_ids": [mesmo.id]}), format="json"
        )
        assert resp.status_code == 201, resp.data
        sol_id = resp.json()["id"]
        assert mesmo.id in set(
            Participation.objects.filter(solicitacao_id=sol_id, role="FORMADOR").values_list("usuario_id", flat=True)
        )

    def test_cross_gerencia_coord_acompanha_rejected(self, coordenador, gerencias, municipio, projeto, tipo_evento):
        """`coord_acompanha_ids` com itens também é recusado (desde 05/10/2026 a lista não aceita itens)."""
        outro = _formador("fluir_ca", gerencias["fluir"])
        resp = _client(coordenador).post(
            "/api/solicitacoes/",
            _payload(municipio, projeto, tipo_evento, {"coord_acompanha_ids": [outro.id]}),
            format="json",
        )
        assert resp.status_code == 400, resp.data


class TestUpdateGerenciaScope:
    def test_cross_gerencia_formador_rejected_on_update(self, coordenador, gerencias, municipio, projeto, tipo_evento):
        """O mesmo gate vale no PATCH (editar), não só no criar."""
        mesmo = _formador("vidas_u", gerencias["vidas"])
        outro = _formador("fluir_u", gerencias["fluir"])
        resp = _client(coordenador).post(
            "/api/solicitacoes/", _payload(municipio, projeto, tipo_evento, {"formador_ids": [mesmo.id]}), format="json"
        )
        assert resp.status_code == 201, resp.data
        sol_id = resp.json()["id"]
        patch = _client(coordenador).patch(
            f"/api/solicitacoes/{sol_id}/",
            {"extra_participants": {"formador_ids": [mesmo.id, outro.id]}},
            format="json",
        )
        assert (
            patch.status_code == 400
        ), f"esperava 400 no update cross-gerência, veio {patch.status_code}: {patch.data}"
        assert "extra_participants" in _erros(patch)


class TestPrivilegedExempt:
    def test_superuser_creator_may_add_cross_gerencia(self, gerencias, municipio, projeto, tipo_evento):
        """Isenção: criador global (superuser) pode pôr formador de outra gerência."""
        su = UsuarioFactory(username="su_setor_1656", cpf=str(next(_CPF)), superuser=True)
        outro = _formador("fluir_su", gerencias["fluir"])
        payload = _payload(municipio, projeto, tipo_evento, {"formador_ids": [outro.id]})
        payload["coordenador"] = UsuarioFactory(groups=["Coordenador"]).id  # 05/10/2026: responsável obrigatório
        resp = _client(su).post("/api/solicitacoes/", payload, format="json")
        assert resp.status_code == 201, resp.data


class TestCreatorSemAtuacaoFailClosed:
    def test_creator_sem_atuacao_na_gerencia_do_projeto_is_blocked(self, gerencias, municipio, projeto, tipo_evento):
        """Fail-closed (PR 9): quem não atua na gerência do projeto não põe ninguém no evento.

        Antes o criador sem setor era fail-open. Agora a dona do evento que só é FORMADOR na gerência
        do projeto (papel que não atua) não adiciona nem formador da própria gerência.
        """
        criador = UsuarioFactory(username="coord_sem_setor_1656", cpf=str(next(_CPF)))
        com_papel(criador, "FORMADOR", gerencias["vidas"])
        propria = SolicitacaoFactory(usuario=criador, projeto=projeto)
        f = _formador("qualquer", gerencias["vidas"])
        resp = _client(criador).patch(
            f"/api/solicitacoes/{propria.id}/", {"extra_participants": {"formador_ids": [f.id]}}, format="json"
        )
        assert resp.status_code == 400, resp.data
        assert "extra_participants" in _erros(resp)


class TestUsuarioLookupGerenciaScope:
    """O /lookup/usuarios/ (que alimenta o picker do wizard) já filtra pelas gerências de atuação →
    o FE mostra só a gerência do coordenador sem mudar código de FE (FE-first satisfeito)."""

    def _ids(self, resp):
        return {item["id"] for item in resp.json()}

    def test_regular_coordenador_lookup_only_own_gerencia(self, coordenador, gerencias):
        vidas = _formador("lk_vidas", gerencias["vidas"])
        fluir = _formador("lk_fluir", gerencias["fluir"])
        resp = _client(coordenador).get("/api/lookup/usuarios/", {"role": "Formador"})
        assert resp.status_code == 200, resp.data
        ids = self._ids(resp)
        assert vidas.id in ids, "formador da MESMA gerência deve aparecer no lookup"
        assert fluir.id not in ids, "formador de OUTRA gerência NÃO pode aparecer no lookup do coordenador regular"

    def test_superuser_lookup_sees_all_gerencias(self, gerencias):
        su = UsuarioFactory(username="su_lk_1656", cpf=str(next(_CPF)), superuser=True)
        vidas = _formador("lk2_vidas", gerencias["vidas"])
        fluir = _formador("lk2_fluir", gerencias["fluir"])
        resp = _client(su).get("/api/lookup/usuarios/", {"role": "Formador"})
        assert resp.status_code == 200, resp.data
        ids = self._ids(resp)
        assert {vidas.id, fluir.id} <= ids, "privilegiado/global vê todas as gerências"
