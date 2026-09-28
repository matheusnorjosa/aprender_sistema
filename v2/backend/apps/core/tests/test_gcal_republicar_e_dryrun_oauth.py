"""Republicar depois de remover e dry-run no modo OAuth (#1656, smoke em produção de 28/09).

1. Publicar → remover → publicar de novo deixava o evento OCULTO. O DELETE do Google é soft-delete:
   o evento fica `status=cancelled` e o GET pelo id determinístico (`asv2{id}`) ainda o devolve. O
   segundo publish o adotava (ADOPT → PATCH) e marcava PUBLISHED, mas o payload não mandava `status`,
   então o PATCH não "descancelava" e o evento seguia invisível no calendário.
2. O dry-run no modo OAuth pulava o cliente do operador e caía na service account, que não existe em
   produção ("Service Account credentials not found"). No dry-run a falha ainda gravava ERROR numa
   linha que ninguém marcou PENDING.

Só a borda é falsa: o `service` do Google por trás do OAuthCalendarClient real.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false, reportMissingTypeStubs=false

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import override_settings

import pytest
from googleapiclient.errors import HttpError

from apps.core.models import AuditLog, Solicitacao
from apps.core.services.gcal.payload import build_event_payload
from apps.core.services.gcal_oauth_client import OAuthCalendarClient
from apps.core.tasks import task_cancel_solicitacao_from_gcal, task_publish_solicitacao_to_gcal
from apps.core.tests.factories import SolicitacaoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

ORG = "org-formacoes@group.calendar.google.com"
OAUTH = override_settings(GCAL_CLIENT="google", GCAL_AUTH_MODE="oauth", GCAL_OAUTH_CALENDAR_ID=ORG)
FABRICA_OAUTH = "apps.core.services.gcal_client_factory.get_oauth_client_for_user"
FABRICA_SERVICE_ACCOUNT = "apps.core.services.gcal_client_factory.get_gcal_client_and_calendar_id"
CAMPOS_GCAL = (
    "gcal_status",
    "gcal_payload_hash",
    "gcal_last_error",
    "gcal_last_sync_at",
    "external_event_id",
    "last_synced_at",
    "last_sync_action",
    "last_sync_error",
    "meet_link",
)


def _http_error(codigo: int) -> HttpError:
    return HttpError(resp=Mock(status=codigo, reason="x"), content=b'{"error": {"message": "x"}}')


class _Chamada:
    def __init__(self, funcao):
        self._funcao = funcao

    def execute(self):
        return self._funcao()


class _EventosGoogle:
    """`events()` do Google em memória, com a semântica de que o bug depende.

    - delete é soft-delete: o evento fica `status=cancelled` e o get AINDA o devolve;
    - patch troca só os campos enviados (sem `status` no corpo, o cancelado continua cancelado);
    - insert de um id que já existe (mesmo cancelado) é 409.
    """

    def __init__(self):
        self.eventos: dict[str, dict] = {}
        self.escritas: list[str] = []

    def get(self, calendarId, eventId):
        def _get():
            if eventId not in self.eventos:
                raise _http_error(404)
            return dict(self.eventos[eventId])

        return _Chamada(_get)

    def insert(self, calendarId, body, **_kwargs):
        def _insert():
            self.escritas.append("insert")
            if body["id"] in self.eventos:
                raise _http_error(409)
            self.eventos[body["id"]] = {"status": "confirmed", **body}
            return dict(self.eventos[body["id"]])

        return _Chamada(_insert)

    def patch(self, calendarId, eventId, body, **_kwargs):
        def _patch():
            self.escritas.append("patch")
            if eventId not in self.eventos:
                raise _http_error(404)
            self.eventos[eventId].update(body)
            return dict(self.eventos[eventId])

        return _Chamada(_patch)

    def delete(self, calendarId, eventId, **_kwargs):
        def _delete():
            self.escritas.append("delete")
            if eventId not in self.eventos:
                raise _http_error(404)
            self.eventos[eventId]["status"] = "cancelled"

        return _Chamada(_delete)


class _ServiceGoogle:
    def __init__(self):
        self.eventos_api = _EventosGoogle()

    def events(self):
        return self.eventos_api

    def calendars(self):
        return SimpleNamespace(get=lambda calendarId: _Chamada(lambda: {"id": calendarId}))


def _cliente_oauth(service: _ServiceGoogle) -> OAuthCalendarClient:
    """OAuthCalendarClient real, sem __init__ (nada de refresh/rede), sobre o `service` falso."""
    cliente = OAuthCalendarClient.__new__(OAuthCalendarClient)
    cliente.credential = SimpleNamespace(
        google_email="operador@aprendereditora.com.br",
        default_calendar_id="",
        user_id=1,
        user=SimpleNamespace(is_authenticated=True, is_superuser=True),
    )
    cliente.service = service
    return cliente


def _estado_gcal(sol: Solicitacao) -> dict:
    sol.refresh_from_db()
    return {campo: getattr(sol, campo) for campo in CAMPOS_GCAL}


def _audits_gcal(sol: Solicitacao) -> int:
    return AuditLog.objects.filter(
        action__in=[AuditLog.Action.PUBLISH_GCAL, AuditLog.Action.PUBLISH_GCAL_ERROR],
        details__solicitacao_id=sol.id,
    ).count()


# ---------------------------------------------------------------------------
# 1. Republicar depois de remover volta a `confirmed`
# ---------------------------------------------------------------------------


def test_payload_de_publicacao_manda_status_confirmed():
    """O PATCH só "descancela" um evento removido se o corpo trouxer o status."""
    sol = SolicitacaoFactory(status="aprovado")

    assert build_event_payload(sol)["status"] == "confirmed"
    assert build_event_payload(sol, enable_meet=True)["status"] == "confirmed"


@OAUTH
def test_publicar_remover_publicar_de_novo_deixa_o_evento_visivel():
    operador = UsuarioFactory()
    service = _ServiceGoogle()
    sol = SolicitacaoFactory(status="aprovado")
    event_id = f"asv2{sol.id}"

    with patch(FABRICA_OAUTH, return_value=(_cliente_oauth(service), ORG)):
        publicado = task_publish_solicitacao_to_gcal(sol.id, operator_user_id=operador.pk)
        assert publicado["action"] == "CREATE"
        assert service.eventos_api.eventos[event_id]["status"] == "confirmed"

        removido = task_cancel_solicitacao_from_gcal(sol.id, operator_user_id=operador.pk)
        assert removido["action"] == "DELETE"
        assert service.eventos_api.eventos[event_id]["status"] == "cancelled"  # soft-delete, como o Google

        republicado = task_publish_solicitacao_to_gcal(sol.id, operator_user_id=operador.pk)

    assert republicado["action"] == "ADOPT"  # o id determinístico ainda existe (cancelado) no Google
    assert service.eventos_api.eventos[event_id]["status"] == "confirmed"
    sol.refresh_from_db()
    assert sol.gcal_status == Solicitacao.GCalStatus.PUBLISHED
    assert sol.external_event_id == event_id


# ---------------------------------------------------------------------------
# 2. Dry-run no modo OAuth usa o cliente do operador e não mexe na Solicitacao
# ---------------------------------------------------------------------------


@OAUTH
def test_dry_run_oauth_usa_o_cliente_do_operador_sem_escrever_nada():
    from apps.core.services import gcal_client_factory

    operador = UsuarioFactory()
    service = _ServiceGoogle()
    sol = SolicitacaoFactory(status="aprovado")
    antes = _estado_gcal(sol)

    with (
        patch(FABRICA_OAUTH, return_value=(_cliente_oauth(service), ORG)) as fabrica_oauth,
        patch(
            FABRICA_SERVICE_ACCOUNT, wraps=gcal_client_factory.get_gcal_client_and_calendar_id
        ) as fabrica_service_account,
    ):
        resultado = task_publish_solicitacao_to_gcal(sol.id, dry_run=True, operator_user_id=operador.pk)

    assert resultado["error"] is None, resultado
    assert resultado["action"] == "CREATE"  # a prévia: o evento ainda não existe no calendário
    fabrica_oauth.assert_called_once()
    fabrica_service_account.assert_not_called()
    assert service.eventos_api.escritas == []  # dry-run lê o Google, não escreve
    assert _estado_gcal(sol) == antes
    assert _audits_gcal(sol) == 0


@OAUTH
def test_dry_run_oauth_sem_operador_devolve_erro_sem_gravar_error():
    sol = SolicitacaoFactory(status="aprovado", external_event_id="asv2publicado")
    sol.gcal_status = Solicitacao.GCalStatus.PUBLISHED
    sol.save(update_fields=["gcal_status"])
    antes = _estado_gcal(sol)

    resultado = task_publish_solicitacao_to_gcal(sol.id, dry_run=True)

    assert resultado["action"] == "ERROR"
    assert resultado["error"] == "missing_operator_user_id"
    assert _estado_gcal(sol) == antes  # a linha publicada não vira ERROR por causa de uma prévia
    assert _audits_gcal(sol) == 0


@OAUTH
def test_dry_run_oauth_sem_credencial_devolve_erro_sem_gravar_error():
    operador = UsuarioFactory()  # sem GoogleOAuthCredential
    sol = SolicitacaoFactory(status="aprovado", external_event_id="asv2publicado")
    sol.gcal_status = Solicitacao.GCalStatus.PUBLISHED
    sol.save(update_fields=["gcal_status"])
    antes = _estado_gcal(sol)

    resultado = task_publish_solicitacao_to_gcal(sol.id, dry_run=True, operator_user_id=operador.pk)

    assert resultado["action"] == "ERROR"
    assert resultado["error"] == "oauth_credential_missing"
    assert _estado_gcal(sol) == antes
    assert _audits_gcal(sol) == 0


@override_settings(GCAL_CLIENT="google", GCAL_AUTH_MODE="oauth", GCAL_OAUTH_CALENDAR_ID="")
def test_dry_run_com_falha_na_publicacao_devolve_erro_sem_gravar_error():
    """A saída de erro genérica da task também respeita o dry-run (antes marcava ERROR mesmo assim)."""
    operador = UsuarioFactory()
    sol = SolicitacaoFactory(status="aprovado", external_event_id="asv2publicado")
    sol.gcal_status = Solicitacao.GCalStatus.PUBLISHED
    sol.save(update_fields=["gcal_status"])
    antes = _estado_gcal(sol)

    # Sem pino e sem escolha na credencial: o cliente recusa resolver o calendário (falha fechada).
    with patch(FABRICA_OAUTH, return_value=(_cliente_oauth(_ServiceGoogle()), "")):
        resultado = task_publish_solicitacao_to_gcal(sol.id, dry_run=True, operator_user_id=operador.pk)

    assert resultado["action"] == "ERROR"
    assert "não configurado" in resultado["error"]
    assert _estado_gcal(sol) == antes
    assert _audits_gcal(sol) == 0
