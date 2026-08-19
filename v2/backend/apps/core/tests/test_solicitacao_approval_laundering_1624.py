"""
M10-02 (#1624) — trocar o projeto de um item aprovado não pode lavar a aprovação.

Vetor: uma solicitação criada num projeto de fluxo NAO_SUPER nasce `aprovado`
(auto-aprovada, PA-01). Se o dono depois troca o projeto para um de fluxo SUPER
via PATCH, `perform_update` salvava sem re-resolver o status → o item continuava
`aprovado`, e `publish_to_gcal` (que só checa `status == "aprovado"`) publicava
um evento de fluxo SUPER **sem a aprovação obrigatória da Superintendência**
(lavagem de aprovação — viola CP-02/PA-01).

Contrato: ao trocar o projeto de um item aprovado para um fluxo que exige
aprovação, o status é rebaixado para `pendente` (força reaprovação). Fluxo
NAO_SUPER (auto-aprovado) e edições que não trocam o projeto não são afetados.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOptionalSubscript=false

from __future__ import annotations

import itertools
from datetime import date, timedelta

from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import Compra
from apps.core.tests.factories import (
    GroupFactory,
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
)

pytestmark = pytest.mark.django_db

_HASH = itertools.count(1)


def _registra_compra(municipio, projeto) -> Compra:
    """#1738: trocar/vincular par município+projeto exige Compra registrada."""
    return Compra.objects.create(
        codigo=f"C-{projeto.codigo}",
        projeto=projeto,
        municipio=municipio,
        quantidade=1,
        data=date(2026, 3, 1),
        uso="teste laundering",
        external_hash=f"{next(_HASH):064d}",
    )


@pytest.fixture
def coordenador():
    user = UsuarioFactory(username="coord_1624", cpf="75000000001")
    user.groups.add(GroupFactory(name="Coordenador"))
    return user


@pytest.fixture
def municipio():
    return MunicipioFactory(nome="Fortaleza", uf="CE", ativo=True)


@pytest.fixture
def tipo_evento():
    return TipoEventoFactory(nome="Formacao M1624")


@pytest.fixture
def projeto_nao_super():
    return ProjetoFactory(nome="NaoSuper 1624", codigo="NS1624", fluxo="NAO_SUPER", ativo=True)


@pytest.fixture
def projeto_super():
    return ProjetoFactory(nome="Super 1624", codigo="SU1624", fluxo="SUPER", ativo=True)


def _solicitacao(coordenador, municipio, tipo_evento, projeto, status="aprovado"):
    inicio = timezone.now() + timedelta(days=5)
    return SolicitacaoFactory(
        usuario=coordenador,
        municipio=municipio,
        projeto=projeto,
        tipo_evento=tipo_evento,
        inicio=inicio,
        fim=inicio + timedelta(hours=2),
        status=status,
    )


@pytest.fixture
def client_coord(coordenador):
    c = APIClient()
    c.force_authenticate(coordenador)
    return c


def _url(sol_id: int) -> str:
    return f"/api/solicitacoes/{sol_id}/"


class TestApprovalLaunderingBlocked:
    def test_switch_approved_to_super_project_demotes_to_pendente(
        self, client_coord, coordenador, municipio, tipo_evento, projeto_nao_super, projeto_super
    ):
        """RED: hoje o status continua 'aprovado' após trocar para projeto SUPER."""
        sol = _solicitacao(coordenador, municipio, tipo_evento, projeto_nao_super, status="aprovado")
        _registra_compra(municipio, projeto_super)

        resp = client_coord.patch(_url(sol.id), {"projeto": projeto_super.id}, format="json")

        assert resp.status_code == 200, resp.data
        sol.refresh_from_db()
        assert sol.projeto_id == projeto_super.id
        assert sol.status == "pendente"  # RED: continuava "aprovado" (lavagem)

    def test_demotion_registra_auditlog(
        self, client_coord, coordenador, municipio, tipo_evento, projeto_nao_super, projeto_super
    ):
        from apps.core.models import AuditLog

        sol = _solicitacao(coordenador, municipio, tipo_evento, projeto_nao_super, status="aprovado")
        _registra_compra(municipio, projeto_super)
        client_coord.patch(_url(sol.id), {"projeto": projeto_super.id}, format="json")

        log = AuditLog.objects.filter(action="UPDATE", model_name="Solicitacao", details__solicitacao_id=sol.id).latest(
            "created_at"
        )
        changed = log.details["changed_fields"]
        assert "status" in changed
        assert changed["status"]["old"] == "aprovado"
        assert changed["status"]["new"] == "pendente"


class TestLegitimateEditsUnaffected:
    def test_edit_non_project_field_keeps_approved(
        self, client_coord, coordenador, municipio, tipo_evento, projeto_nao_super
    ):
        """Editar campo que não é o projeto num item aprovado não rebaixa."""
        sol = _solicitacao(coordenador, municipio, tipo_evento, projeto_nao_super, status="aprovado")

        resp = client_coord.patch(_url(sol.id), {"observacoes": "nova obs"}, format="json")

        assert resp.status_code == 200, resp.data
        sol.refresh_from_db()
        assert sol.status == "aprovado"

    def test_switch_between_nao_super_keeps_approved(
        self, client_coord, coordenador, municipio, tipo_evento, projeto_nao_super
    ):
        """Trocar entre dois projetos NAO_SUPER mantém auto-aprovado (não exige aprovação)."""
        outro_nao_super = ProjetoFactory(nome="NaoSuper2 1624", codigo="NS21624", fluxo="NAO_SUPER", ativo=True)
        sol = _solicitacao(coordenador, municipio, tipo_evento, projeto_nao_super, status="aprovado")
        _registra_compra(municipio, outro_nao_super)

        resp = client_coord.patch(_url(sol.id), {"projeto": outro_nao_super.id}, format="json")

        assert resp.status_code == 200, resp.data
        sol.refresh_from_db()
        assert sol.projeto_id == outro_nao_super.id
        assert sol.status == "aprovado"
