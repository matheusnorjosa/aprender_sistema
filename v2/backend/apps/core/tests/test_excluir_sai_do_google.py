"""Excluir um evento que está no Google tira dos dois lados (decisão do dono, opção A: sem poder novo).

Antes, `perform_destroy` recusava o evento PUBLISHED e deixava passar o ERROR com `external_event_id`
(o evento continuava no Google: órfão) e o `publicado_fora_do_sistema` (só pela API). Agora:

- Quem já pode excluir E já pode tirar do Google (`can_publish_solicitacao`) exclui numa ação só: o
  sistema tira do Google primeiro (síncrono) e só apaga a linha se o Google confirmar.
- Quem não pode tirar do Google recebe o 400 de sempre, sem chamada ao Google.
- As recusas de sempre (PENDING, SUPER fora de pendente, já aprovada) vêm ANTES do Google.
- Evento da planilha não adotado (`publicado_fora_do_sistema`) não se exclui.

O Google é sempre simulado (cliente falso); nada sai da máquina.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from collections.abc import Iterator
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.test import override_settings
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
    return Gerencia.objects.create(nome="GERENCIA EXCLUIR GCAL", nome_setor="Fluir", ativo=True)


@pytest.fixture
def apoio(gerencia):
    """Apoio de Coordenação da gerência: pode tirar do Google os eventos dela."""
    user = UsuarioFactory(username="apoio_excluir_gcal", cpf="64000000001")
    com_papel(user, "APOIO", gerencia)
    return user


@pytest.fixture
def formador(gerencia):
    """Dono de evento sem `can_publish_solicitacao`."""
    user = UsuarioFactory(username="formador_excluir_gcal", cpf="64000000002")
    com_papel(user, "FORMADOR", gerencia)
    return user


@pytest.fixture
def projeto(gerencia):
    return ProjetoFactory(nome="Projeto Excluir GCal", fluxo="NAO_SUPER", gerencia=gerencia)


@pytest.fixture
def projeto_super(gerencia):
    return ProjetoFactory(nome="Projeto Super Excluir GCal", fluxo="SUPER", gerencia=gerencia)


def _evento(dono, projeto, *, gcal_status="PUBLISHED", external_event_id="evt-excluir-1", **extra) -> Solicitacao:
    inicio = timezone.now() + timedelta(days=5)
    return SolicitacaoFactory(
        usuario=dono,
        municipio=MunicipioFactory(),
        projeto=projeto,
        tipo_evento=TipoEventoFactory(nome="Formacao Excluir GCal"),
        inicio=inicio,
        fim=inicio + timedelta(hours=2),
        status="aprovado",
        gcal_status=gcal_status,
        external_event_id=external_event_id,
        meet_link="https://meet.google.com/abc-defg-hij" if external_event_id else None,
        **extra,
    )


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


def _delete(user, sol):
    client = APIClient()
    client.force_authenticate(user=user)
    return client.delete(f"/api/solicitacoes/{sol.pk}/")


def _acoes_auditadas(sol_id: int) -> list[str]:
    return [
        a.action
        for a in AuditLog.objects.filter(model_name="Solicitacao").order_by("id")
        if (a.details or {}).get("solicitacao_id") == sol_id
        or ((a.details or {}).get("solicitacao_data") or {}).get("id") == sol_id
    ]


# ---------------------------------------------------------------------------
# Quem pode as duas coisas: sai do Google e do sistema
# ---------------------------------------------------------------------------


def test_apoio_dona_exclui_publicado_e_sai_do_google(apoio, projeto, google):
    sol = _evento(apoio, projeto)
    sol_id = sol.pk

    response = _delete(apoio, sol)

    assert response.status_code == 204, response.data
    google.delete.assert_called_once_with(CALENDARIO, "evt-excluir-1")
    assert not Solicitacao.objects.filter(pk=sol_id).exists()
    assert _acoes_auditadas(sol_id) == ["CANCEL_GCAL", "DELETE"]
    cancel = AuditLog.objects.get(action="CANCEL_GCAL", details__solicitacao_id=sol_id)
    assert cancel.usuario == apoio
    delete = AuditLog.objects.get(action="DELETE", details__solicitacao_data__id=sol_id)
    assert delete.details["removido_do_google"] is True
    assert delete.details["external_event_id"] == "evt-excluir-1"


def test_erro_com_id_tira_do_google_antes_de_apagar(apoio, projeto, google):
    """Fecha o órfão: ERROR com id é evento que continua no Google."""
    sol = _evento(apoio, projeto, gcal_status="ERROR", external_event_id="evt-com-erro")
    sol_id = sol.pk

    response = _delete(apoio, sol)

    assert response.status_code == 204, response.data
    google.delete.assert_called_once_with(CALENDARIO, "evt-com-erro")
    assert not Solicitacao.objects.filter(pk=sol_id).exists()


def test_excluir_nao_publicado_nao_chama_o_google(apoio, projeto, google):
    sol = _evento(apoio, projeto, gcal_status="NONE", external_event_id=None)

    response = _delete(apoio, sol)

    assert response.status_code == 204, response.data
    google.delete.assert_not_called()
    delete = AuditLog.objects.get(action="DELETE", details__solicitacao_data__id=sol.pk)
    assert "removido_do_google" not in delete.details


# ---------------------------------------------------------------------------
# Google falhou: nada é apagado
# ---------------------------------------------------------------------------


def _http_error(status: int, motivo: str):
    from googleapiclient.errors import HttpError
    from httplib2 import Response

    return HttpError(Response({"status": status}), f'{{"error": {{"message": "{motivo}"}}}}'.encode())


def test_evento_ja_apagado_no_google_410_conta_como_removido(apoio, projeto, google):
    """Evento apagado direto no Google: o DELETE volta 410 (Gone). Já saiu de lá, então a exclusão segue."""
    google.delete.side_effect = _http_error(410, "Resource has been deleted")
    sol = _evento(apoio, projeto)
    sol_id = sol.pk

    response = _delete(apoio, sol)

    assert response.status_code == 204, response.data
    assert not Solicitacao.objects.filter(pk=sol_id).exists()


def test_retentativa_depois_da_falha_ao_gravar_recebe_410_e_exclui(apoio, projeto, google):
    """A promessa da falha parcial: o Google já tirou, a gravação caiu; tentar de novo (410) resolve."""
    from django.db import DatabaseError

    sol = _evento(apoio, projeto)
    with patch.object(Solicitacao, "save", side_effect=DatabaseError("db fora")):
        assert _delete(apoio, sol).status_code == 400
    google.delete.side_effect = _http_error(410, "Resource has been deleted")

    response = _delete(apoio, sol)

    assert response.status_code == 204, response.data
    assert not Solicitacao.objects.filter(pk=sol.pk).exists()


def test_google_com_erro_nao_apaga_nada(apoio, projeto, google):
    google.delete.side_effect = Exception("<HttpError 500 backendError>")
    sol = _evento(apoio, projeto)

    response = _delete(apoio, sol)

    assert response.status_code == 400
    # Quem exclui lê o motivo no aviso da tela: o erro cru do Google não diz nada a ela.
    detail = response.data["detail"]
    assert "HttpError" not in detail and "500" not in detail
    assert "nada foi excluído" in detail.lower()
    assert "tente excluir de novo" in detail.lower()
    sol.refresh_from_db()
    assert sol.external_event_id == "evt-excluir-1"
    assert sol.gcal_status == "PUBLISHED"
    assert not AuditLog.objects.filter(action="DELETE", details__solicitacao_data__id=sol.pk).exists()
    assert not AuditLog.objects.filter(action="CANCEL_GCAL", details__solicitacao_id=sol.pk).exists()


def test_google_recusa_403_diz_o_que_fazer_e_nao_apaga(apoio, projeto, google):
    erro = Exception("<HttpError 403 forbidden>")
    erro.resp = MagicMock(status=403)
    google.delete.side_effect = erro
    sol = _evento(apoio, projeto)

    response = _delete(apoio, sol)

    assert response.status_code == 400
    detail = response.data["detail"]
    assert "HttpError" not in detail
    assert "nada foi excluído" in detail.lower()
    assert "compartilhamento" in detail
    assert Solicitacao.objects.filter(pk=sol.pk, external_event_id="evt-excluir-1").exists()


def test_sem_acesso_ao_calendario_nao_apaga_nada(apoio, projeto, google):
    google.calendar_accessible.return_value = False
    sol = _evento(apoio, projeto)

    response = _delete(apoio, sol)

    assert response.status_code == 400
    assert "acesso ao calendário" in response.data["detail"]
    assert "nada foi excluído" in response.data["detail"].lower()
    google.delete.assert_not_called()
    sol.refresh_from_db()
    assert sol.external_event_id == "evt-excluir-1"


@override_settings(GCAL_AUTH_MODE="oauth")
def test_oauth_sem_conta_google_conectada_da_400_e_nao_apaga(apoio, projeto, google):
    sol = _evento(apoio, projeto)

    response = _delete(apoio, sol)

    assert response.status_code == 400
    assert response.data["detail"] == "Conecte sua conta Google"
    google.delete.assert_not_called()
    assert Solicitacao.objects.filter(pk=sol.pk, external_event_id="evt-excluir-1").exists()


# ---------------------------------------------------------------------------
# Sem poder novo: quem não tira do Google não exclui o que está lá
# ---------------------------------------------------------------------------


def test_dono_sem_can_publish_recebe_400_sem_chamar_o_google(formador, projeto, google):
    sol = _evento(formador, projeto)

    response = _delete(formador, sol)

    assert response.status_code == 400
    assert "Google Calendar" in response.data["detail"]
    google.delete.assert_not_called()
    assert Solicitacao.objects.filter(pk=sol.pk).exists()


def test_dono_sem_can_publish_nao_exclui_erro_com_id(formador, projeto, google):
    """Antes passava e deixava o evento no Google."""
    sol = _evento(formador, projeto, gcal_status="ERROR", external_event_id="evt-com-erro")

    response = _delete(formador, sol)

    assert response.status_code == 400
    google.delete.assert_not_called()
    assert Solicitacao.objects.filter(pk=sol.pk).exists()


def test_publicado_fora_do_sistema_nao_se_exclui(apoio, projeto, google):
    sol = _evento(apoio, projeto, gcal_status="NONE", external_event_id=None, publicado_fora_do_sistema=True)

    response = _delete(apoio, sol)

    assert response.status_code == 400
    assert "planilha" in response.data["detail"]
    google.delete.assert_not_called()
    assert Solicitacao.objects.filter(pk=sol.pk).exists()


# ---------------------------------------------------------------------------
# As recusas de sempre vêm antes do Google
# ---------------------------------------------------------------------------


def test_super_aprovada_publicada_recusa_sem_chamar_o_google(apoio, projeto_super, google):
    sol = _evento(apoio, projeto_super)

    response = _delete(apoio, sol)

    assert response.status_code == 400
    assert "SUPER" in response.data["detail"]
    google.delete.assert_not_called()
    sol.refresh_from_db()
    assert sol.external_event_id == "evt-excluir-1"


def test_com_approve_publicada_recusa_sem_chamar_o_google(apoio, projeto, google):
    sol = _evento(apoio, projeto)
    AuditLog.objects.create(
        usuario=None, action=AuditLog.Action.APPROVE, model_name="Solicitacao", details={"solicitacao_id": sol.pk}
    )

    response = _delete(apoio, sol)

    assert response.status_code == 400
    assert "já foi aprovada" in response.data["detail"]
    google.delete.assert_not_called()
    sol.refresh_from_db()
    assert sol.external_event_id == "evt-excluir-1"


def test_pending_continua_recusado_sem_chamar_o_google(apoio, projeto, google):
    sol = _evento(apoio, projeto, gcal_status="PENDING")

    response = _delete(apoio, sol)

    assert response.status_code == 400
    google.delete.assert_not_called()


# ---------------------------------------------------------------------------
# Lista: a tela sabe a quem mostrar Excluir num evento publicado
# ---------------------------------------------------------------------------


def test_lista_diz_quem_pode_tirar_do_google(apoio, formador, projeto):
    sol_apoio = _evento(apoio, projeto)
    sol_formador = _evento(formador, projeto)

    client = APIClient()
    client.force_authenticate(user=apoio)
    linhas = client.get("/api/solicitacoes/", {"mine": "true"}).data["results"]
    assert [(r["id"], r["pode_tirar_do_google"]) for r in linhas] == [(sol_apoio.pk, True)]

    client.force_authenticate(user=formador)
    linhas = client.get("/api/solicitacoes/", {"mine": "true"}).data["results"]
    assert [(r["id"], r["pode_tirar_do_google"]) for r in linhas] == [(sol_formador.pk, False)]


def test_lista_calcula_o_escopo_de_publicacao_uma_vez_por_request(apoio, projeto):
    for _ in range(3):
        _evento(apoio, projeto)
    from apps.core.services import solicitacao_scope

    client = APIClient()
    client.force_authenticate(user=apoio)
    with patch.object(solicitacao_scope, "_publish_tier", wraps=solicitacao_scope._publish_tier) as tier:
        linhas = client.get("/api/solicitacoes/", {"mine": "true"}).data["results"]

    assert len(linhas) == 3
    assert all(r["pode_tirar_do_google"] for r in linhas)
    assert tier.call_count == 1


# ---------------------------------------------------------------------------
# ERROR sem id: a publicação que falhou pode ter criado o evento no Google
# ---------------------------------------------------------------------------


def test_erro_sem_id_tenta_o_id_deterministico_antes_de_apagar(apoio, projeto, google):
    """O insert usa `_event_id_for(s)` e não grava o id quando falha: o evento pode estar lá."""
    from apps.core.services.gcal_sync_service import _event_id_for

    sol = _evento(apoio, projeto, gcal_status="ERROR", external_event_id=None)
    sol_id = sol.pk

    response = _delete(apoio, sol)

    assert response.status_code == 204, response.data
    google.delete.assert_called_once_with(CALENDARIO, _event_id_for(sol))
    assert not Solicitacao.objects.filter(pk=sol_id).exists()


def test_dono_sem_can_publish_nao_exclui_erro_sem_id(formador, projeto, google):
    sol = _evento(formador, projeto, gcal_status="ERROR", external_event_id=None)

    response = _delete(formador, sol)

    assert response.status_code == 400
    google.delete.assert_not_called()
    assert Solicitacao.objects.filter(pk=sol.pk).exists()


# ---------------------------------------------------------------------------
# Concorrência: o delete confere de novo, com a linha travada
# ---------------------------------------------------------------------------


def _publica_por_fora(sol_id: int):
    """Simula a task de publicação que gravou o evento entre as checagens e o delete."""

    def efeito(request):
        Solicitacao.objects.filter(pk=sol_id).update(gcal_status="PUBLISHED", external_event_id="evt-concorrente")
        return "127.0.0.1"

    return efeito


def test_publicacao_concorrente_antes_do_delete_nao_apaga(apoio, projeto, google):
    sol = _evento(apoio, projeto, gcal_status="NONE", external_event_id=None)

    with patch("apps.core.views_solicitacao.get_client_ip", side_effect=_publica_por_fora(sol.pk)):
        response = _delete(apoio, sol)

    assert response.status_code == 400
    assert "mudou no Google Agenda" in response.data["detail"]
    assert Solicitacao.objects.filter(pk=sol.pk, external_event_id="evt-concorrente").exists()
    assert not AuditLog.objects.filter(action="DELETE", details__solicitacao_data__id=sol.pk).exists()


def test_reenvio_concorrente_depois_de_tirar_do_google_nao_apaga(apoio, projeto, google):
    sol = _evento(apoio, projeto)

    with patch("apps.core.views_solicitacao.get_client_ip", side_effect=_publica_por_fora(sol.pk)):
        response = _delete(apoio, sol)

    assert response.status_code == 400
    google.delete.assert_called_once_with(CALENDARIO, "evt-excluir-1")
    assert Solicitacao.objects.filter(pk=sol.pk, external_event_id="evt-concorrente").exists()


def test_pending_que_apareceu_depois_da_checagem_nao_chama_o_google(apoio, projeto, google):
    """A linha relida com lock está PENDING (publicação ou reenvio enfileirado): não mexe no Google."""
    sol = _evento(apoio, projeto)

    def pode_e_enfileira(user, obj):
        Solicitacao.objects.filter(pk=obj.pk).update(gcal_status="PENDING")
        return True

    with patch("apps.core.views_solicitacao.can_publish_solicitacao", side_effect=pode_e_enfileira):
        response = _delete(apoio, sol)

    assert response.status_code == 400
    assert "sincronização" in response.data["detail"]
    google.delete.assert_not_called()
    assert Solicitacao.objects.filter(pk=sol.pk, gcal_status="PENDING").exists()


# ---------------------------------------------------------------------------
# O que vem depois do Google não desfaz em silêncio a saída de lá
# ---------------------------------------------------------------------------


def test_auditoria_do_cancelamento_vem_antes_do_google(apoio, projeto, google):
    """Se o AuditLog falhar, o Google não foi chamado: a resposta 'nada mudou' é verdadeira."""
    from django.db import DatabaseError

    sol = _evento(apoio, projeto)

    with patch.object(AuditLog.objects, "create", side_effect=DatabaseError("audit fora")):
        response = _delete(apoio, sol)

    assert response.status_code == 400
    google.delete.assert_not_called()
    sol.refresh_from_db()
    assert sol.external_event_id == "evt-excluir-1"


def test_falha_ao_gravar_depois_do_google_diz_que_pode_ter_saido(apoio, projeto, google):
    from django.db import DatabaseError

    sol = _evento(apoio, projeto)

    with patch.object(Solicitacao, "save", side_effect=DatabaseError("db fora")):
        response = _delete(apoio, sol)

    assert response.status_code == 400
    google.delete.assert_called_once()
    assert "pode já ter saído do Google Agenda" in response.data["detail"]
    assert Solicitacao.objects.filter(pk=sol.pk).exists()
