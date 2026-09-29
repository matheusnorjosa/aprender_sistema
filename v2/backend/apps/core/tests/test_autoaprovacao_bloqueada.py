"""
PR B1 — bloqueio de autoaprovação (PA-02, adendo de segregação).

Quem criou a solicitação (`Solicitacao.usuario`) não aprova nem reprova a própria.
A trava vive no SERVICE (`services/solicitacao_approval.py`), depois do
`select_for_update` e antes do check de status — fora do alcance de corrida.

- approve/reject da própria → 403 `self_approval_forbidden`; nada muda, nenhum AuditLog.
- lote: o item próprio vai para `errors[]` com o código; o resto do lote segue.
- superuser pode (break-glass), e o AuditLog marca `details.autoaprovacao = true`.
- toda decisão grava `details.autoridade` (base da autoridade do ator).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOptionalSubscript=false, reportUnusedFunction=false

from __future__ import annotations

import logging
from datetime import timedelta

from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import AuditLog, EquipeGerencia, Gerencia, Solicitacao, Usuario
from apps.core.tests.factories import (
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
)

pytestmark = pytest.mark.django_db

_SERVICE_LOGGER = "apps.core.services.solicitacao_approval"


@pytest.fixture(autouse=True)
def _clear_rbac_cache(db):
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def aprovadora() -> Usuario:
    """GERENTE vigente na SUPERINTENDENCIA, sem grupos."""
    g1, _ = Gerencia.objects.get_or_create(nome="SUPERINTENDENCIA", defaults={"nome_setor": "Super"})
    user = UsuarioFactory()
    EquipeGerencia.objects.create(usuario=user, gerencia=g1, papel="GERENTE")
    return user


def _pendente(dono: Usuario) -> Solicitacao:
    inicio = timezone.now() + timedelta(days=5)
    return SolicitacaoFactory(
        usuario=dono,
        projeto=ProjetoFactory(fluxo="SUPER"),
        municipio=MunicipioFactory(),
        tipo_evento=TipoEventoFactory(nome="Formação B1 auto"),
        inicio=inicio,
        fim=inicio + timedelta(hours=2),
        status="pendente",
    )


def _client(user: Usuario) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _audit(sol: Solicitacao) -> list[AuditLog]:
    return list(AuditLog.objects.filter(model_name="Solicitacao", details__solicitacao_id=sol.id))


# =============================================================================
# Decisão individual
# =============================================================================


@pytest.mark.parametrize(
    ("acao", "verbo"),
    [("approve", "aprovar"), ("reject", "reprovar")],
)
def test_decidir_a_propria_da_403_e_nada_muda(aprovadora, acao, verbo):
    propria = _pendente(aprovadora)

    resp = _client(aprovadora).patch(f"/api/solicitacoes/{propria.id}/{acao}/", {"reason": "x"}, format="json")

    assert resp.status_code == 403, resp.content
    body = resp.json()
    assert body["code"] == "self_approval_forbidden"
    assert body["detail"] == (f"Você não pode {verbo} a própria solicitação. Outra pessoa aprovadora precisa decidir.")
    propria.refresh_from_db()
    assert propria.status == "pendente"
    assert _audit(propria) == []


def test_bloqueio_emite_warning_sem_username(aprovadora, caplog):
    propria = _pendente(aprovadora)

    with caplog.at_level(logging.WARNING, logger=_SERVICE_LOGGER):
        _client(aprovadora).patch(f"/api/solicitacoes/{propria.id}/approve/", format="json")

    registros = [r for r in caplog.records if r.getMessage() == "solicitacao_self_decision_blocked"]
    assert len(registros) == 1
    assert registros[0].user_id == aprovadora.pk
    assert registros[0].solicitacao_id == propria.id
    assert not hasattr(registros[0], "username")


def test_decidir_a_alheia_grava_autoridade(aprovadora):
    alheia = _pendente(UsuarioFactory(groups=["Coordenador"]))

    resp = _client(aprovadora).patch(f"/api/solicitacoes/{alheia.id}/approve/", format="json")

    assert resp.status_code == 200, resp.content
    (log,) = _audit(alheia)
    assert log.details["autoridade"] == "gerente_superintendencia"
    assert "autoaprovacao" not in log.details


def test_logs_de_decisao_nao_levam_username(aprovadora, caplog):
    """Username é o CPF em produção: o log estruturado usa só `user_id`."""
    alheia = _pendente(UsuarioFactory(groups=["Coordenador"]))

    with caplog.at_level(logging.INFO, logger=_SERVICE_LOGGER):
        _client(aprovadora).patch(f"/api/solicitacoes/{alheia.id}/approve/", format="json")

    registros = [r for r in caplog.records if r.getMessage() == "solicitacao_approved"]
    assert len(registros) == 1
    assert registros[0].user_id == aprovadora.pk
    assert not hasattr(registros[0], "username")


@pytest.mark.parametrize("acao", ["approve", "reject"])
def test_superuser_decide_a_propria_e_fica_marcado(acao):
    superuser = UsuarioFactory(superuser=True)
    propria = _pendente(superuser)

    resp = _client(superuser).patch(f"/api/solicitacoes/{propria.id}/{acao}/", {"reason": "x"}, format="json")

    assert resp.status_code == 200, resp.content
    (log,) = _audit(propria)
    assert log.details["autoaprovacao"] is True
    assert log.details["autoridade"] == "superuser"


# =============================================================================
# Lote
# =============================================================================


@pytest.mark.parametrize(
    ("url", "contador", "status_final"),
    [
        ("/api/solicitacoes/batch-approve/", "approved", "aprovado"),
        ("/api/solicitacoes/batch-reject/", "rejected", "reprovado"),
    ],
)
def test_lote_com_propria_e_alheia(aprovadora, url, contador, status_final):
    propria = _pendente(aprovadora)
    alheia = _pendente(UsuarioFactory(groups=["Coordenador"]))

    resp = _client(aprovadora).post(url, {"ids": [propria.id, alheia.id]}, format="json")

    assert resp.status_code == 200, resp.content
    body = resp.json()
    assert body[contador] == 1
    erros = [e for e in body["errors"] if e["id"] == propria.id]
    assert len(erros) == 1
    assert erros[0]["code"] == "self_approval_forbidden"
    propria.refresh_from_db()
    alheia.refresh_from_db()
    assert propria.status == "pendente"
    assert alheia.status == status_final
    assert _audit(propria) == []
    (log,) = _audit(alheia)
    assert log.details["autoridade"] == "gerente_superintendencia"


def test_superuser_aprova_a_propria_em_lote_e_fica_marcado():
    superuser = UsuarioFactory(superuser=True)
    propria = _pendente(superuser)

    resp = _client(superuser).post("/api/solicitacoes/batch-approve/", {"ids": [propria.id]}, format="json")

    assert resp.status_code == 200, resp.content
    assert resp.json()["approved"] == 1
    (log,) = _audit(propria)
    assert log.details["autoaprovacao"] is True
    assert log.details["autoridade"] == "superuser"
