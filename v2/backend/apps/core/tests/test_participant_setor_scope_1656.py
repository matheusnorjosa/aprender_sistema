"""
#1656 / M10-04 Wave 1 (Slice 1) — escopo do ALVO por SETOR em extra_participants.

Regra (decidida pelo dono, medida em prod 2026-09-15): o coordenador REGULAR só
pode adicionar como formador/coord-acompanha quem compartilha um SETOR
(`Gerencia.setor_canonico`, via EquipeGerencia vigente) com ele. Cross-setor por
um criador regular = 400 (o FE só mostra opções do setor; o backend é o gate).

Nuances medidas:
- Granularidade = SETOR (setor_canonico), não a Gerencia fina (Vidas L≠M colapsam
  em "Vidas"). Em prod só 3 cross-setor reais, todos da Superintendência.
- Privilegiado/global (superuser, Superintendência, Controle, DAT) é ISENTO
  (`user_is_solicitacao_global`) — cobre os 3 casos da Superintendência.
- Criador SEM setor = fail-open (não dá p/ escopar; 0 em prod; não quebra criador
  sem vínculo). Participante sem setor, com criador COM setor = fail-closed.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportMissingTypeStubs=false

from __future__ import annotations

import itertools
from datetime import date, timedelta

from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import Compra, EquipeGerencia, Gerencia, Participation
from apps.core.tests.factories import (
    GroupFactory,
    MunicipioFactory,
    ProjetoFactory,
    TipoEventoFactory,
    UsuarioFactory,
)

pytestmark = pytest.mark.django_db

_HASH = itertools.count(1)
_CPF = itertools.count(79100000001)


def _gerencia(nome, setor):
    return Gerencia.objects.create(nome=nome, setor_canonico=setor)


def _vincula(user, gerencia, papel="FORMADOR"):
    EquipeGerencia.objects.create(usuario=user, gerencia=gerencia, papel=papel, ativo=True)


def _formador(n, gerencia=None):
    u = UsuarioFactory(username=f"form_setor_{n}", cpf=str(next(_CPF)))
    u.groups.add(GroupFactory(name="Formador"))
    if gerencia is not None:
        _vincula(u, gerencia, "FORMADOR")
    return u


@pytest.fixture
def gerencias():
    return {"vidas": _gerencia("G-Vidas-1656", "Vidas"), "fluir": _gerencia("G-Fluir-1656", "Fluir")}


@pytest.fixture
def coordenador(gerencias):
    u = UsuarioFactory(username="coord_setor_1656", cpf=str(next(_CPF)))
    u.groups.add(GroupFactory(name="Coordenador"))
    _vincula(u, gerencias["vidas"], "COORDENADOR")  # criador é do setor Vidas
    return u


@pytest.fixture
def municipio():
    return MunicipioFactory(nome="Fortaleza setor 1656", uf="CE", ativo=True)


@pytest.fixture
def tipo_evento():
    return TipoEventoFactory(nome="Formacao setor 1656")


@pytest.fixture
def projeto(municipio):
    proj = ProjetoFactory(nome="Projeto setor 1656", codigo="PS1656", fluxo="NAO_SUPER", ativo=True)
    Compra.objects.create(
        codigo="C-S1656",
        projeto=proj,
        municipio=municipio,
        quantidade=1,
        data=date(2026, 3, 1),
        uso="teste",
        external_hash=f"{next(_HASH):064d}",
    )
    return proj


def _payload(municipio, projeto, tipo_evento, extra):
    inicio = timezone.now() + timedelta(days=3)
    return {
        "municipio": municipio.id,
        "projeto": projeto.id,
        "tipo_evento": tipo_evento.id,
        "tipo": "PRESENCIAL",
        "inicio": inicio.isoformat(),
        "fim": (inicio + timedelta(hours=2)).isoformat(),
        "extra_participants": extra,
    }


def _client(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


class TestCreateSetorScope:
    def test_cross_setor_formador_rejected_on_create(self, coordenador, gerencias, municipio, projeto, tipo_evento):
        """RED: criador do setor Vidas NÃO pode adicionar formador do setor Fluir."""
        outro = _formador("fluir", gerencias["fluir"])
        resp = _client(coordenador).post(
            "/api/solicitacoes/", _payload(municipio, projeto, tipo_evento, {"formador_ids": [outro.id]}), format="json"
        )
        assert resp.status_code == 400, f"esperava 400 (formador de outro setor), veio {resp.status_code}: {resp.data}"

    def test_same_setor_formador_allowed_on_create(self, coordenador, gerencias, municipio, projeto, tipo_evento):
        """Não-regressão: formador do MESMO setor (Vidas) é aceito."""
        mesmo = _formador("vidas", gerencias["vidas"])
        resp = _client(coordenador).post(
            "/api/solicitacoes/", _payload(municipio, projeto, tipo_evento, {"formador_ids": [mesmo.id]}), format="json"
        )
        assert resp.status_code == 201, resp.data
        sol_id = resp.json()["id"]
        assert mesmo.id in set(
            Participation.objects.filter(solicitacao_id=sol_id, role="FORMADOR").values_list("usuario_id", flat=True)
        )

    def test_cross_setor_coord_acompanha_rejected(self, coordenador, gerencias, municipio, projeto, tipo_evento):
        """RED: mesma regra para coord_acompanha (não só formador)."""
        outro = _formador("fluir_ca", gerencias["fluir"])
        resp = _client(coordenador).post(
            "/api/solicitacoes/",
            _payload(municipio, projeto, tipo_evento, {"coord_acompanha_ids": [outro.id]}),
            format="json",
        )
        assert resp.status_code == 400, resp.data


class TestUpdateSetorScope:
    def test_cross_setor_formador_rejected_on_update(self, coordenador, gerencias, municipio, projeto, tipo_evento):
        """RED: o mesmo gate vale no PATCH (editar), não só no criar."""
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
        assert patch.status_code == 400, f"esperava 400 no update cross-setor, veio {patch.status_code}: {patch.data}"


class TestPrivilegedExempt:
    def test_superuser_creator_may_add_cross_setor(self, gerencias, municipio, projeto, tipo_evento):
        """Isenção: criador global (superuser) pode cruzar setor (cobre os 3 casos da Superintendência)."""
        su = UsuarioFactory(username="su_setor_1656", cpf=str(next(_CPF)), superuser=True)
        outro = _formador("fluir_su", gerencias["fluir"])
        resp = _client(su).post(
            "/api/solicitacoes/", _payload(municipio, projeto, tipo_evento, {"formador_ids": [outro.id]}), format="json"
        )
        assert resp.status_code == 201, resp.data


class TestCreatorWithoutSetorFailOpen:
    def test_creator_without_vinculo_is_not_blocked(self, gerencias, municipio, projeto, tipo_evento):
        """Fail-open: criador SEM setor não é escopado (0 em prod; protege transição/suíte)."""
        criador = UsuarioFactory(username="coord_sem_setor_1656", cpf=str(next(_CPF)))
        criador.groups.add(GroupFactory(name="Coordenador"))  # sem EquipeGerencia
        f = _formador("qualquer", gerencias["fluir"])
        resp = _client(criador).post(
            "/api/solicitacoes/", _payload(municipio, projeto, tipo_evento, {"formador_ids": [f.id]}), format="json"
        )
        assert resp.status_code == 201, resp.data


class TestUsuarioLookupSetorScope:
    """O /lookup/usuarios/ (que alimenta o picker do wizard) já filtra por setor →
    o FE mostra só o setor do coordenador sem mudar código de FE (FE-first satisfeito)."""

    def _ids(self, resp):
        return {item["id"] for item in resp.json()}

    def test_regular_coordenador_lookup_only_own_setor(self, coordenador, gerencias):
        vidas = _formador("lk_vidas", gerencias["vidas"])
        fluir = _formador("lk_fluir", gerencias["fluir"])
        resp = _client(coordenador).get("/api/lookup/usuarios/", {"role": "Formador"})
        assert resp.status_code == 200, resp.data
        ids = self._ids(resp)
        assert vidas.id in ids, "formador do MESMO setor deve aparecer no lookup"
        assert fluir.id not in ids, "formador de OUTRO setor NÃO pode aparecer no lookup do coordenador regular"

    def test_superuser_lookup_sees_all_setores(self, gerencias):
        su = UsuarioFactory(username="su_lk_1656", cpf=str(next(_CPF)), superuser=True)
        vidas = _formador("lk2_vidas", gerencias["vidas"])
        fluir = _formador("lk2_fluir", gerencias["fluir"])
        resp = _client(su).get("/api/lookup/usuarios/", {"role": "Formador"})
        assert resp.status_code == 200, resp.data
        ids = self._ids(resp)
        assert {vidas.id, fluir.id} <= ids, "privilegiado/global vê todos os setores"
