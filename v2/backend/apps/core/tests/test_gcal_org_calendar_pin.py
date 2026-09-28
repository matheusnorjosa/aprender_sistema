"""Calendário da organização fixo nas escritas OAuth (`GCAL_OAUTH_CALENDAR_ID`) — #1656, achado F4.

Antes, o calendário era re-derivado de QUEM AGE: `credential.default_calendar_id`, senão o e-mail da
conta (→ 'primary', o calendário PESSOAL). Consequências:
- uma Apoio recém-conectada (sem escolha de calendário) publicaria no calendário pessoal dela;
- resync/cancel feitos por OUTRO operador procuravam o evento no calendário DELE: o resync criava um
  duplicado e o cancel via 404 (= sucesso), limpava os campos e deixava o evento órfão.
Agora toda escrita OAuth vai para o pino da organização (ou, sem pino, para a escolha explícita da
credencial) — nunca para o pessoal. E o cancel confere o acesso ao calendário antes de apagar.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false, reportIncompatibleMethodOverride=false, reportMissingSuperCall=false

from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

import pytest
from googleapiclient.errors import HttpError

from apps.core.models import GoogleOAuthCredential, Solicitacao
from apps.core.services.gcal_oauth_client import OAuthCalendarClient, resolve_publish_calendar_id
from apps.core.services.oauth.token_manager import encrypt_token
from apps.core.tests.factories import GroupFactory, SolicitacaoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

ORG = "org-formacoes@group.calendar.google.com"
SEM_THROTTLE = (
    patch("rest_framework.throttling.AnonRateThrottle.allow_request", return_value=True),
    patch("rest_framework.throttling.UserRateThrottle.allow_request", return_value=True),
)


def _cred(default_calendar_id=""):
    return SimpleNamespace(
        default_calendar_id=default_calendar_id, google_email="operador@aprendereditora.com.br", user_id=1
    )


def _http_error(codigo):
    return HttpError(resp=Mock(status=codigo, reason="x"), content=b'{"error": {"message": "x"}}')


def _cliente_sem_rede(default_calendar_id=""):
    cliente = OAuthCalendarClient.__new__(OAuthCalendarClient)  # sem __init__: nada de refresh/Google
    cliente.credential = _cred(default_calendar_id)
    cliente.service = Mock()
    return cliente


# ---------------------------------------------------------------------------
# A. Resolução do calendário de publicação
# ---------------------------------------------------------------------------


@override_settings(GCAL_OAUTH_CALENDAR_ID=ORG)
def test_pino_prevalece_sobre_selecao_da_credencial():
    assert resolve_publish_calendar_id(_cred("calendario-escolhido@group.calendar.google.com")) == ORG


@override_settings(GCAL_OAUTH_CALENDAR_ID="")
def test_sem_pino_usa_selecao_da_credencial():
    """Guarda: sem pino, a escolha explícita da credencial segue valendo (é o caso de prod hoje)."""
    escolhido = "formacoes@group.calendar.google.com"
    assert resolve_publish_calendar_id(_cred(escolhido)) == escolhido
    assert _cliente_sem_rede(escolhido).get_default_calendar_id() == escolhido


@override_settings(GCAL_OAUTH_CALENDAR_ID="")
def test_sem_pino_sem_selecao_nao_publica_no_calendario_pessoal():
    """Antes caía no e-mail da conta → 'primary' (calendário PESSOAL). Agora falha fechado."""
    cliente = _cliente_sem_rede("")
    assert resolve_publish_calendar_id(cliente.credential) == ""
    with pytest.raises(ValueError, match="não configurado"):
        cliente.get_default_calendar_id()


@pytest.mark.parametrize(
    "efeito, esperado",
    [(None, True), (_http_error(403), False), (_http_error(404), False)],
    ids=["200", "403", "404"],
)
def test_calendar_accessible_200_true_403_404_false(efeito, esperado):
    cliente = _cliente_sem_rede()
    execute = cliente.service.calendars.return_value.get.return_value.execute
    if efeito is None:
        execute.return_value = {"id": ORG}
    else:
        execute.side_effect = efeito
    assert cliente.calendar_accessible(ORG) is esperado


def test_calendar_accessible_500_propaga():
    cliente = _cliente_sem_rede()
    cliente.service.calendars.return_value.get.return_value.execute.side_effect = _http_error(500)
    with patch("apps.core.services.gcal_oauth_client.time.sleep"), pytest.raises(HttpError):
        cliente.calendar_accessible(ORG)


# ---------------------------------------------------------------------------
# B. Recusa no request, ANTES de marcar PENDING
# ---------------------------------------------------------------------------


def _controle_conectado(default_calendar_id=""):
    user = UsuarioFactory()
    user.groups.add(GroupFactory(name="Controle"))
    GoogleOAuthCredential.objects.create(
        user=user,
        google_email="controle@aprendereditora.com.br",
        access_token_encrypted=encrypt_token("acesso"),
        refresh_token_encrypted=encrypt_token("refresh"),
        token_expiry=timezone.now() + timedelta(hours=1),
        scope="https://www.googleapis.com/auth/calendar",
        default_calendar_id=default_calendar_id,
    )
    client = APIClient()
    client.force_authenticate(user)
    return user, client


@override_settings(GCAL_CLIENT="google", GCAL_AUTH_MODE="oauth", GCAL_OAUTH_CALENDAR_ID="")
@patch("apps.core.tasks.task_publish_solicitacao_to_gcal.delay")
def test_publish_oauth_sem_calendario_409_sem_pending_sem_task(mock_delay):
    mock_delay.return_value = Mock(id="task-x")
    _user, client = _controle_conectado(default_calendar_id="")
    sol = SolicitacaoFactory(status="aprovado")

    with SEM_THROTTLE[0], SEM_THROTTLE[1]:
        resp = client.post(f"/api/solicitacoes/{sol.id}/publish/", {}, format="json")

    assert resp.status_code == status.HTTP_409_CONFLICT
    assert resp.data["code"] == "google_calendar_not_configured"
    mock_delay.assert_not_called()
    sol.refresh_from_db()
    assert sol.gcal_status == Solicitacao.GCalStatus.NONE


@override_settings(GCAL_CLIENT="google", GCAL_AUTH_MODE="oauth", GCAL_OAUTH_CALENDAR_ID="")
@patch("apps.core.tasks.task_cancel_solicitacao_from_gcal.delay")
@patch("apps.core.tasks.task_publish_solicitacao_to_gcal.delay")
def test_resync_e_cancel_oauth_sem_calendario_409(mock_publish, mock_cancel):
    mock_publish.return_value = Mock(id="task-p")
    mock_cancel.return_value = Mock(id="task-c")
    _user, client = _controle_conectado(default_calendar_id="")
    sol = SolicitacaoFactory(status="aprovado", external_event_id="asv2abc")
    sol.gcal_status = Solicitacao.GCalStatus.PUBLISHED
    sol.save(update_fields=["gcal_status"])

    with SEM_THROTTLE[0], SEM_THROTTLE[1]:
        resync = client.post(f"/api/solicitacoes/{sol.id}/resync-gcal/", {}, format="json")
        cancel = client.post(f"/api/solicitacoes/{sol.id}/cancel-gcal/", {}, format="json")

    assert resync.status_code == status.HTTP_409_CONFLICT
    assert resync.data["code"] == "google_calendar_not_configured"
    assert cancel.status_code == status.HTTP_409_CONFLICT
    assert cancel.data["code"] == "google_calendar_not_configured"
    mock_publish.assert_not_called()
    mock_cancel.assert_not_called()
    sol.refresh_from_db()
    assert sol.gcal_status == Solicitacao.GCalStatus.PUBLISHED


@override_settings(GCAL_CLIENT="google", GCAL_AUTH_MODE="oauth", GCAL_OAUTH_CALENDAR_ID=ORG)
@patch("apps.core.tasks.task_publish_solicitacao_to_gcal.delay")
def test_publish_oauth_com_pino_202_despacha_operator_user_id(mock_delay):
    """Guarda: com o pino, mesmo sem escolha na credencial, publica — e despacha o operador."""
    mock_delay.return_value = Mock(id="task-1")
    user, client = _controle_conectado(default_calendar_id="")
    sol = SolicitacaoFactory(status="aprovado")

    with SEM_THROTTLE[0], SEM_THROTTLE[1]:
        resp = client.post(f"/api/solicitacoes/{sol.id}/publish/", {}, format="json")

    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert mock_delay.call_args.kwargs["operator_user_id"] == user.pk


# ---------------------------------------------------------------------------
# C. F4 — outro operador age sobre o MESMO calendário (sem duplicar, sem órfão)
# ---------------------------------------------------------------------------


class _GoogleEmMemoria:
    def __init__(self):
        self.eventos = {}
        self.chamadas = []


class _ClienteGravador(OAuthCalendarClient):
    """OAuthCalendarClient sem rede: usa a resolução REAL do calendário e grava num 'Google' em memória."""

    def __init__(self, default_calendar_id, google, *, acessivel=True):  # sem super(): nada de refresh
        self.credential = _cred(default_calendar_id)
        self.google = google
        self.acessivel = acessivel

    def get(self, calendar_id, event_id):
        self.google.chamadas.append(("get", calendar_id))
        return self.google.eventos.get((calendar_id, event_id))

    def insert(self, calendar_id, event_id, payload):
        self.google.chamadas.append(("insert", calendar_id))
        self.google.eventos[(calendar_id, event_id)] = {"id": event_id}
        return {"id": event_id}

    def update(self, calendar_id, event_id, payload):
        self.google.chamadas.append(("update", calendar_id))
        self.google.eventos[(calendar_id, event_id)] = {"id": event_id}
        return {"id": event_id}

    def delete(self, calendar_id, event_id):
        self.google.chamadas.append(("delete", calendar_id))
        self.google.eventos.pop((calendar_id, event_id), None)

    def calendar_accessible(self, calendar_id):
        self.google.chamadas.append(("acessivel", calendar_id))
        return self.acessivel


@override_settings(GCAL_CLIENT="google", GCAL_AUTH_MODE="oauth", GCAL_OAUTH_CALENDAR_ID=ORG)
def test_resync_e_cancel_de_outro_operador_usam_o_mesmo_calendario():
    from apps.core.services.gcal_sync_service import apply_one_solicitacao, cancel_solicitacao

    google = _GoogleEmMemoria()
    operador_a = _ClienteGravador("calendario-de-A", google)
    operador_b = _ClienteGravador("calendario-de-B", google)
    sol = SolicitacaoFactory(status="aprovado")

    apply_one_solicitacao(sol, dry_run=False, apply_blocked=False, client=operador_a)  # A publica
    sol.refresh_from_db()
    sol.gcal_payload_hash = None  # o resync zera o hash para forçar UPDATE
    sol.save(update_fields=["gcal_payload_hash"])
    apply_one_solicitacao(sol, dry_run=False, apply_blocked=False, client=operador_b)  # B resincroniza
    sol.refresh_from_db()
    cancel_solicitacao(sol, client=operador_b)  # B cancela

    calendarios = {calendario for _op, calendario in google.chamadas}
    assert calendarios == {ORG}, google.chamadas
    assert [op for op, _cal in google.chamadas].count("insert") == 1  # sem duplicado
    assert google.eventos == {}  # removido do calendário da organização, sem órfão


@override_settings(GCAL_CLIENT="google", GCAL_AUTH_MODE="oauth", GCAL_OAUTH_CALENDAR_ID=ORG)
def test_cancel_sem_acesso_ao_calendario_nao_apaga_e_marca_error():
    from apps.core.tasks import task_cancel_solicitacao_from_gcal

    google = _GoogleEmMemoria()
    sem_acesso = _ClienteGravador("calendario-de-B", google, acessivel=False)
    operador = UsuarioFactory()
    sol = SolicitacaoFactory(status="aprovado", external_event_id="asv2abc")
    sol.gcal_status = Solicitacao.GCalStatus.PENDING
    sol.save(update_fields=["gcal_status"])

    with patch("apps.core.services.gcal_client_factory.get_oauth_client_for_user", return_value=(sem_acesso, ORG)):
        task_cancel_solicitacao_from_gcal(sol.id, operator_user_id=operador.pk)

    assert not [c for c in google.chamadas if c[0] == "delete"]
    sol.refresh_from_db()
    assert sol.gcal_status == Solicitacao.GCalStatus.ERROR
    assert sol.external_event_id == "asv2abc"
    assert "acesso ao calendário" in sol.gcal_last_error


@override_settings(GCAL_CLIENT="google", GCAL_AUTH_MODE="oauth", GCAL_OAUTH_CALENDAR_ID=ORG)
def test_cancel_com_acesso_limpa_campos():
    """Guarda: com acesso confirmado, o cancel apaga e limpa os campos (404 volta a significar 'já não existe')."""
    from apps.core.services.gcal_sync_service import cancel_solicitacao

    google = _GoogleEmMemoria()
    operador = _ClienteGravador("calendario-de-B", google)
    sol = SolicitacaoFactory(status="aprovado", external_event_id="asv2abc")
    sol.gcal_status = Solicitacao.GCalStatus.PUBLISHED
    sol.save(update_fields=["gcal_status"])

    cancel_solicitacao(sol, client=operador)

    assert ("delete", ORG) in google.chamadas
    sol.refresh_from_db()
    assert not sol.external_event_id
