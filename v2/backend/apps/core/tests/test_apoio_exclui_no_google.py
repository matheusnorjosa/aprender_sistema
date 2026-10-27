"""A Apoio de Coordenação exclui, dos dois lados, o evento de outra pessoa que já está no Google.

Decisão do dono de 27/10/2026 ("B só o que está no Google"): a Apoio passa a excluir (do sistema e do
Google, numa ação) o evento criado por OUTRA pessoa só quando (a) o projeto é de uma gerência onde ela é
APOIO vigente, (b) o evento já está no Google (`PUBLISHED`, `ERROR` ou `external_event_id`) e (c) não é
`publicado_fora_do_sistema`. Pedido que não está no Google continua fora do alcance dela, a edição não
muda e ninguém além dela ganha poder. As travas de sempre do `perform_destroy` continuam valendo.

O campo `pode_excluir` da lista diz à tela se quem lê pode excluir a linha: tem de bater com o DELETE.

O Google é sempre simulado (cliente falso); nada sai da máquina.
"""

# pyright: reportUnknownLambdaType=false, reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOptionalSubscript=false

from __future__ import annotations

from collections.abc import Iterator
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import AuditLog, Gerencia, Solicitacao
from apps.core.tests.factories import (
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
    com_papel,
)

pytestmark = pytest.mark.django_db

CALENDARIO = "org@group.calendar.google.com"


@pytest.fixture
def gerencia():
    return Gerencia.objects.create(nome="GERENCIA APOIO EXCLUI", nome_setor="Fluir", ativo=True)


@pytest.fixture
def outra_gerencia():
    return Gerencia.objects.create(nome="GERENCIA SEM A APOIO", nome_setor="Vidas", ativo=True)


@pytest.fixture
def apoio(gerencia):
    user = UsuarioFactory(username="apoio_exclui_outro", cpf="64100000001")
    com_papel(user, "APOIO", gerencia)
    return user


@pytest.fixture
def coordenadora(gerencia, outra_gerencia):
    """Quem criou os eventos: coordena nas duas gerências."""
    user = UsuarioFactory(username="coord_dona_evento", cpf="64100000002")
    com_papel(user, "COORDENADOR", gerencia)
    com_papel(user, "COORDENADOR", outra_gerencia)
    return user


@pytest.fixture
def projeto(gerencia):
    return ProjetoFactory(nome="Projeto Apoio Exclui", fluxo="NAO_SUPER", gerencia=gerencia)


@pytest.fixture
def projeto_super(gerencia):
    return ProjetoFactory(nome="Projeto Super Apoio Exclui", fluxo="SUPER", gerencia=gerencia)


@pytest.fixture
def projeto_de_outra(outra_gerencia):
    return ProjetoFactory(nome="Projeto Outra Gerencia", fluxo="NAO_SUPER", gerencia=outra_gerencia)


def _evento(dono, projeto, *, gcal_status="PUBLISHED", external_event_id="evt-apoio-1", **extra) -> Solicitacao:
    inicio = timezone.now() + timedelta(days=5)
    dados = {
        "usuario": dono,
        "municipio": MunicipioFactory(),
        "projeto": projeto,
        "tipo_evento": TipoEventoFactory(nome="Formacao Apoio Exclui"),
        "inicio": inicio,
        "fim": inicio + timedelta(hours=2),
        "status": "aprovado",
        "gcal_status": gcal_status,
        "external_event_id": external_event_id,
        "meet_link": "https://meet.google.com/abc-defg-hij" if external_event_id else None,
        **extra,
    }
    return SolicitacaoFactory(**dados)


@pytest.fixture
def google() -> Iterator[MagicMock]:
    """Cliente Google falso (service account): acesso ao calendário e delete que dá certo."""
    client = MagicMock()
    client.calendar_accessible.return_value = True
    with (
        patch(
            "apps.core.services.gcal_client_factory.get_gcal_client_and_calendar_id",
            return_value=(client, CALENDARIO),
        ),
        patch(
            "apps.core.services.gcal.sync._retry_with_circuit_breaker",
            side_effect=lambda func, operation_name=None: func(),
        ),
    ):
        yield client


def _cliente(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _delete(user, sol):
    return _cliente(user).delete(f"/api/solicitacoes/{sol.pk}/")


def _acoes_auditadas(sol_id: int) -> list[str]:
    return [
        a.action
        for a in AuditLog.objects.filter(model_name="Solicitacao").order_by("id")
        if (a.details or {}).get("solicitacao_id") == sol_id
        or ((a.details or {}).get("solicitacao_data") or {}).get("id") == sol_id
    ]


def _lista_da_publicacao(user) -> dict[int, bool]:
    """A carga da tela Publicar na agenda: {id: pode_excluir}."""
    resposta = _cliente(user).get("/api/solicitacoes/", {"status": "aprovado", "publishable": "true", "page_size": 100})
    assert resposta.status_code == 200, resposta.data
    return {linha["id"]: linha["pode_excluir"] for linha in resposta.data["results"]}


# ---------------------------------------------------------------------------
# O poder novo: evento de outra pessoa, na gerência dela, que está no Google
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("gcal_status", ["PUBLISHED", "ERROR"])
def test_apoio_exclui_evento_no_google_de_outra_pessoa_da_gerencia(apoio, coordenadora, projeto, google, gcal_status):
    sol = _evento(coordenadora, projeto, gcal_status=gcal_status)
    sol_id = sol.pk

    response = _delete(apoio, sol)

    assert response.status_code == 204, response.data
    google.delete.assert_called_once_with(CALENDARIO, "evt-apoio-1")
    assert not Solicitacao.objects.filter(pk=sol_id).exists()
    assert _acoes_auditadas(sol_id) == ["CANCEL_GCAL", "DELETE"]
    delete = AuditLog.objects.get(action="DELETE", details__solicitacao_data__id=sol_id)
    assert delete.usuario == apoio
    assert delete.details["removido_do_google"] is True


# ---------------------------------------------------------------------------
# Fora do Google, fora da gerência, editar: nada muda
# ---------------------------------------------------------------------------


def test_apoio_nao_exclui_pedido_super_pendente_de_outra_pessoa(apoio, coordenadora, projeto_super, google):
    """O pedido que espera a gerente não está no Google: a Apoio nem o enxerga (só aprovadas)."""
    sol = _evento(coordenadora, projeto_super, status="pendente", gcal_status="NONE", external_event_id=None)

    response = _delete(apoio, sol)

    assert response.status_code in (403, 404)
    google.delete.assert_not_called()
    assert Solicitacao.objects.filter(pk=sol.pk).exists()


def test_apoio_nao_exclui_evento_fora_do_google_de_outra_pessoa(apoio, coordenadora, projeto, google):
    sol = _evento(coordenadora, projeto, gcal_status="NONE", external_event_id=None)

    response = _delete(apoio, sol)

    assert response.status_code == 403
    # A recusa fala de excluir (não da mensagem de edição) e diz quando a Apoio pode.
    assert "excluir" in str(response.data["detail"])
    assert "editar" not in str(response.data["detail"])
    google.delete.assert_not_called()
    assert Solicitacao.objects.filter(pk=sol.pk).exists()


def test_apoio_nao_exclui_no_google_de_gerencia_onde_nao_e_apoio(apoio, coordenadora, projeto_de_outra, google):
    sol = _evento(coordenadora, projeto_de_outra)

    response = _delete(apoio, sol)

    assert response.status_code in (403, 404)
    google.delete.assert_not_called()
    assert Solicitacao.objects.filter(pk=sol.pk).exists()


def test_apoio_nao_exclui_evento_da_planilha_de_outra_pessoa(apoio, coordenadora, projeto, google):
    sol = _evento(coordenadora, projeto, gcal_status="NONE", external_event_id=None, publicado_fora_do_sistema=True)

    response = _delete(apoio, sol)

    assert response.status_code in (400, 403)
    google.delete.assert_not_called()
    assert Solicitacao.objects.filter(pk=sol.pk).exists()


def test_apoio_continua_sem_editar_evento_de_outra_pessoa_no_google(apoio, coordenadora, projeto, google):
    sol = _evento(coordenadora, projeto)

    response = _cliente(apoio).patch(f"/api/solicitacoes/{sol.pk}/", {"observacoes": "mudou"}, format="json")

    assert response.status_code == 403
    sol.refresh_from_db()
    assert sol.observacoes != "mudou"


@pytest.mark.parametrize("papel", ["FORMADOR", "COORDENADOR"])
def test_quem_nao_e_apoio_nao_ganha_nada(gerencia, coordenadora, projeto, google, papel):
    user = UsuarioFactory(username=f"sem_apoio_{papel.lower()}", cpf="64100000009")
    com_papel(user, papel, gerencia)
    sol = _evento(coordenadora, projeto)

    response = _delete(user, sol)

    assert response.status_code in (403, 404)
    google.delete.assert_not_called()
    assert Solicitacao.objects.filter(pk=sol.pk).exists()


# ---------------------------------------------------------------------------
# As travas de sempre valem para ela, antes do Google
# ---------------------------------------------------------------------------


def test_super_aprovada_no_google_de_outra_pessoa_recusa_sem_chamar_o_google(
    apoio, coordenadora, projeto_super, google
):
    sol = _evento(coordenadora, projeto_super)

    response = _delete(apoio, sol)

    assert response.status_code == 400
    assert "SUPER" in response.data["detail"]
    google.delete.assert_not_called()
    assert Solicitacao.objects.filter(pk=sol.pk, external_event_id="evt-apoio-1").exists()


def test_ja_aprovada_no_google_de_outra_pessoa_recusa_sem_chamar_o_google(apoio, coordenadora, projeto, google):
    sol = _evento(coordenadora, projeto)
    AuditLog.objects.create(
        usuario=None, action=AuditLog.Action.APPROVE, model_name="Solicitacao", details={"solicitacao_id": sol.pk}
    )

    response = _delete(apoio, sol)

    assert response.status_code == 400
    assert "já foi aprovada" in response.data["detail"]
    google.delete.assert_not_called()


def test_pending_com_id_de_outra_pessoa_recusa_sem_chamar_o_google(apoio, coordenadora, projeto, google):
    sol = _evento(coordenadora, projeto, gcal_status="PENDING")

    response = _delete(apoio, sol)

    assert response.status_code == 400
    google.delete.assert_not_called()


# ---------------------------------------------------------------------------
# `pode_excluir`: a tela sabe o que o DELETE vai fazer
# ---------------------------------------------------------------------------


def test_pode_excluir_da_lista_bate_com_o_delete_para_a_apoio(apoio, coordenadora, projeto, projeto_super, google):
    com_approve = _evento(coordenadora, projeto)
    AuditLog.objects.create(
        usuario=None,
        action=AuditLog.Action.APPROVE,
        model_name="Solicitacao",
        details={"solicitacao_id": com_approve.pk},
    )
    esperado = {
        _evento(coordenadora, projeto).pk: True,
        _evento(coordenadora, projeto, gcal_status="ERROR").pk: True,
        _evento(coordenadora, projeto, gcal_status="NONE", external_event_id=None).pk: False,
        _evento(coordenadora, projeto_super).pk: False,
        com_approve.pk: False,
        _evento(coordenadora, projeto, gcal_status="PENDING").pk: False,
        _evento(
            coordenadora, projeto, gcal_status="NONE", external_event_id=None, publicado_fora_do_sistema=True
        ).pk: False,
        _evento(apoio, projeto, gcal_status="NONE", external_event_id=None).pk: True,
        _evento(apoio, projeto).pk: True,
    }

    assert _lista_da_publicacao(apoio) == esperado

    for sol_id, pode in esperado.items():
        response = _cliente(apoio).delete(f"/api/solicitacoes/{sol_id}/")
        assert (response.status_code == 204) is pode, (sol_id, response.status_code, response.data)


def test_pode_excluir_dos_proprios_sem_tirar_do_google(gerencia, projeto, google):
    """Quem não tira do Google (formador dono) exclui o que não está lá e não exclui o publicado."""
    formador = UsuarioFactory(username="formador_dono_pode_excluir", cpf="64100000010")
    com_papel(formador, "FORMADOR", gerencia)
    publicado = _evento(formador, projeto)
    fora = _evento(formador, projeto, gcal_status="NONE", external_event_id=None)

    linhas = _cliente(formador).get("/api/solicitacoes/", {"mine": "true"}).data["results"]

    assert {r["id"]: r["pode_excluir"] for r in linhas} == {publicado.pk: False, fora.pk: True}
    assert _delete(formador, publicado).status_code == 400
    assert _delete(formador, fora).status_code == 204


def test_pode_excluir_nao_cresce_em_consultas_com_a_pagina(apoio, coordenadora, projeto):
    def consultas() -> int:
        with CaptureQueriesContext(connection) as ctx:
            _lista_da_publicacao(apoio)
        return len(ctx.captured_queries)

    for _ in range(2):
        _evento(coordenadora, projeto)
    consultas()  # aquece o cache das capacidades (a 1ª carga também as grava)
    com_duas = consultas()
    for _ in range(5):
        _evento(coordenadora, projeto)

    assert consultas() == com_duas


@pytest.mark.parametrize("status", ["pendente", "reprovado"])
def test_regra_da_apoio_so_vale_para_evento_aprovado(apoio, coordenadora, projeto_super, status):
    """Pedido de outra pessoa que não está aprovado (ex.: SUPER pendente com Event ID adotado) não é da Apoio.

    A lista dela só traz as aprovadas da gerência, mas quem é global para ver (a aprovadora da
    Superintendência que também é Apoio) passaria só por esta regra: ela tem de olhar o status.
    """
    from apps.core.services.solicitacao_scope import EscritaEmSolicitacao

    sol = _evento(coordenadora, projeto_super, gcal_status="ERROR", external_event_id="evt-adotado-1", status=status)
    assert EscritaEmSolicitacao(apoio).apoio_pode_excluir_do_google(sol) is False
