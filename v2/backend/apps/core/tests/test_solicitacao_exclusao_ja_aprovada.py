"""
Trava de exclusão (decisão do dono, 15/10/2026): «já aprovado não se exclui».

Com o S2, uma SUPER aprovada volta para `pendente` quando muda data, horário, município, formadores
ou projeto. Sem a trava, o criador apagaria pelo `DELETE` um evento que a Superintendência já
aprovou, e a aprovação sumiria sem decisão registrada. A marca de «já aprovada» é o AuditLog
`APPROVE` da solicitação, gravado pela aprovação individual e pela aprovação em lote (PA-05).
A auto-aprovação da NAO_SUPER não grava `APPROVE` (só o status inicial) e segue excluível.

Contrato:
- teve aprovação manual (individual ou em lote) → `DELETE` dá 400, o registro fica, e a mensagem
  manda reprovar ou cancelar (caminho registrado);
- vale para todos na API, superusuário incluso; o admin Django não muda;
- SUPER pendente nunca aprovada e NAO_SUPER auto-aprovada não publicada continuam excluíveis.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOptionalSubscript=false

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import AuditLog, Participation, Solicitacao
from apps.core.tests.factories import (
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
    liberar_par,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def coordenador():
    return UsuarioFactory(groups=["Coordenador"])


@pytest.fixture
def aprovador():
    return UsuarioFactory(is_superuser=True, is_staff=True)


@pytest.fixture
def municipio():
    return MunicipioFactory(nome="Municipio Exclusao", uf="CE", ativo=True)


def _projeto(municipio, fluxo):
    projeto = ProjetoFactory(nome=f"Projeto Exclusao {fluxo}", fluxo=fluxo)
    liberar_par(municipio, projeto)
    return projeto


def _solicitacao(coordenador, municipio, projeto, status):
    inicio = (timezone.now() + timedelta(days=10)).replace(hour=12, minute=0, second=0, microsecond=0)
    sol = SolicitacaoFactory(
        usuario=coordenador,
        coordenador=coordenador,
        municipio=municipio,
        projeto=projeto,
        tipo_evento=TipoEventoFactory(nome="Formacao Exclusao"),
        inicio=inicio,
        fim=inicio + timedelta(hours=3),
        status=status,
    )
    Participation.objects.create(solicitacao=sol, usuario=coordenador, role="COORDENADOR")
    Participation.objects.create(solicitacao=sol, usuario=UsuarioFactory(groups=["Formador"]), role="FORMADOR")
    return sol


def _client(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def _aprovar(aprovador, sol, lote):
    if lote:
        resp = _client(aprovador).post("/api/solicitacoes/batch-approve/", {"ids": [sol.id]}, format="json")
        assert resp.status_code == 200 and resp.data["approved"] == 1, resp.data
    else:
        resp = _client(aprovador).patch(f"/api/solicitacoes/{sol.id}/approve/", {}, format="json")
        assert resp.status_code == 200, resp.data
    sol.refresh_from_db()
    assert sol.status == "aprovado"


def _rebaixar_por_edicao(coordenador, sol):
    """S2: o criador muda o horário da aprovada e ela volta para pendente."""
    resp = _client(coordenador).patch(
        f"/api/solicitacoes/{sol.id}/", {"fim": (sol.fim + timedelta(hours=1)).isoformat()}, format="json"
    )
    assert resp.status_code == 200, resp.data
    sol.refresh_from_db()
    assert sol.status == "pendente"


@pytest.fixture
def super_aprovada_e_rebaixada(coordenador, aprovador, municipio, request):
    sol = _solicitacao(coordenador, municipio, _projeto(municipio, "SUPER"), "pendente")
    _aprovar(aprovador, sol, lote=getattr(request, "param", False))
    _rebaixar_por_edicao(coordenador, sol)
    return sol


class TestJaAprovadaNaoSeExclui:
    @pytest.mark.parametrize(
        "super_aprovada_e_rebaixada",
        [pytest.param(False, id="aprovacao_individual"), pytest.param(True, id="aprovacao_em_lote")],
        indirect=True,
    )
    def test_criador_nao_exclui_super_que_voltou_a_pendente(self, coordenador, super_aprovada_e_rebaixada):
        sol = super_aprovada_e_rebaixada

        resp = _client(coordenador).delete(f"/api/solicitacoes/{sol.id}/")

        assert resp.status_code == 400, resp.data
        assert Solicitacao.objects.filter(pk=sol.pk).exists()
        assert not AuditLog.objects.filter(action="DELETE", model_name="Solicitacao").exists()

    def test_mensagem_orienta_reprovar_ou_cancelar(self, coordenador, super_aprovada_e_rebaixada):
        resp = _client(coordenador).delete(f"/api/solicitacoes/{super_aprovada_e_rebaixada.id}/")

        detalhe = str(resp.data["detail"]).lower()
        assert "já foi aprovada" in detalhe
        assert "reprov" in detalhe and "cancel" in detalhe

    def test_superusuario_tambem_e_barrado_na_api(self, super_aprovada_e_rebaixada):
        """Decisão: a trava vale para todos na API; evento já aprovado sai por reprovação ou cancelamento."""
        sol = super_aprovada_e_rebaixada

        resp = _client(UsuarioFactory(is_superuser=True, is_staff=True)).delete(f"/api/solicitacoes/{sol.id}/")

        assert resp.status_code == 400, resp.data
        assert Solicitacao.objects.filter(pk=sol.pk).exists()


class TestSemAprovacaoManualContinuaExcluivel:
    def test_super_pendente_nunca_aprovada(self, coordenador, municipio):
        sol = _solicitacao(coordenador, municipio, _projeto(municipio, "SUPER"), "pendente")

        resp = _client(coordenador).delete(f"/api/solicitacoes/{sol.id}/")

        assert resp.status_code == 204, resp.data
        assert not Solicitacao.objects.filter(pk=sol.pk).exists()

    def test_nao_super_auto_aprovada_nao_publicada(self, coordenador, municipio):
        """Auto-aprovação (PA-01) é status inicial, não grava AuditLog APPROVE: segue excluível."""
        sol = _solicitacao(coordenador, municipio, _projeto(municipio, "NAO_SUPER"), "aprovado")

        resp = _client(coordenador).delete(f"/api/solicitacoes/{sol.id}/")

        assert resp.status_code == 204, resp.data
        assert not Solicitacao.objects.filter(pk=sol.pk).exists()

    def test_aprovacao_de_outra_solicitacao_nao_trava_esta(self, coordenador, aprovador, municipio):
        projeto = _projeto(municipio, "SUPER")
        outra = _solicitacao(coordenador, municipio, projeto, "pendente")
        _aprovar(aprovador, outra, lote=False)
        sol = _solicitacao(coordenador, municipio, projeto, "pendente")

        resp = _client(coordenador).delete(f"/api/solicitacoes/{sol.id}/")

        assert resp.status_code == 204, resp.data
