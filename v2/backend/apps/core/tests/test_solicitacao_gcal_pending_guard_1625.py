"""
M10-03 (#1625) — bloquear edição/exclusão enquanto gcal_status == PENDING.

Os guards de edição (serializer) e exclusão (perform_destroy) só tratavam
`PUBLISHED` como imutável. A janela `PENDING` (a task Celery de publish/resync/
cancel já foi enfileirada, mas ainda não rodou) ficava editável/deletável — a
task então publicava/operava sobre o conteúdo corrente em vez do snapshot
aprovado (TOCTOU / drift; ou operava sobre um registro já removido).

Contrato: com gcal_status in (PUBLISHED, PENDING), PATCH/PUT e DELETE → 400.
Fora dessa janela (NONE/ERROR) as edições legítimas seguem.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOptionalSubscript=false

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import Solicitacao
from apps.core.tests.factories import (
    GroupFactory,
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def coordenador():
    user = UsuarioFactory(username="coord_1625", cpf="76000000001")
    user.groups.add(GroupFactory(name="Coordenador"))
    return user


@pytest.fixture
def municipio():
    return MunicipioFactory(nome="Fortaleza", uf="CE", ativo=True)


@pytest.fixture
def tipo_evento():
    return TipoEventoFactory(nome="Formacao M1625")


@pytest.fixture
def projeto_nao_super():
    return ProjetoFactory(nome="NaoSuper 1625", codigo="NS1625", fluxo="NAO_SUPER", ativo=True)


def _solicitacao(coordenador, municipio, tipo_evento, projeto, gcal_status):
    inicio = timezone.now() + timedelta(days=5)
    sol = SolicitacaoFactory(
        usuario=coordenador,
        municipio=municipio,
        projeto=projeto,
        tipo_evento=tipo_evento,
        inicio=inicio,
        fim=inicio + timedelta(hours=2),
        status="aprovado",
    )
    sol.gcal_status = gcal_status
    sol.save(update_fields=["gcal_status"])
    return sol


@pytest.fixture
def client_coord(coordenador):
    c = APIClient()
    c.force_authenticate(coordenador)
    return c


def _url(sol_id: int) -> str:
    return f"/api/solicitacoes/{sol_id}/"


class TestPendingWindowBlocksMutation:
    def test_patch_bloqueado_com_gcal_pending(
        self, client_coord, coordenador, municipio, tipo_evento, projeto_nao_super
    ):
        """RED: hoje o guard só cobre PUBLISHED; PENDING passa e edita."""
        sol = _solicitacao(coordenador, municipio, tipo_evento, projeto_nao_super, Solicitacao.GCalStatus.PENDING)

        resp = client_coord.patch(_url(sol.id), {"observacoes": "editado durante sync"}, format="json")

        assert resp.status_code == 400, f"esperado 400, obteve {resp.status_code}"
        sol.refresh_from_db()
        assert sol.observacoes != "editado durante sync"

    def test_delete_bloqueado_com_gcal_pending(
        self, client_coord, coordenador, municipio, tipo_evento, projeto_nao_super
    ):
        """RED: perform_destroy só cobre PUBLISHED; PENDING é deletável."""
        sol = _solicitacao(coordenador, municipio, tipo_evento, projeto_nao_super, Solicitacao.GCalStatus.PENDING)

        resp = client_coord.delete(_url(sol.id))

        assert resp.status_code == 400, f"esperado 400, obteve {resp.status_code}"
        assert Solicitacao.objects.filter(pk=sol.id).exists()


class TestOutsideWindowStillWorks:
    def test_patch_permitido_com_gcal_none(self, client_coord, coordenador, municipio, tipo_evento, projeto_nao_super):
        sol = _solicitacao(coordenador, municipio, tipo_evento, projeto_nao_super, Solicitacao.GCalStatus.NONE)

        resp = client_coord.patch(_url(sol.id), {"observacoes": "edicao legitima"}, format="json")

        assert resp.status_code == 200, resp.data
        sol.refresh_from_db()
        assert sol.observacoes == "edicao legitima"

    def test_patch_bloqueado_com_gcal_published(
        self, client_coord, coordenador, municipio, tipo_evento, projeto_nao_super
    ):
        """Não-regressão: PUBLISHED continua bloqueado."""
        sol = _solicitacao(coordenador, municipio, tipo_evento, projeto_nao_super, Solicitacao.GCalStatus.PUBLISHED)

        resp = client_coord.patch(_url(sol.id), {"observacoes": "x"}, format="json")

        assert resp.status_code == 400
