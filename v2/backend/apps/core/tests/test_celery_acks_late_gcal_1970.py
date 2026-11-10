"""Publicar e remover do Google sobrevivem à queda do worker sem estragar a linha (#1970).

Sem `acks_late`, o Celery confirma a mensagem ANTES de rodar a task: se o worker cai no meio, a
publicação some e a linha fica PENDING. Com `acks_late` + `reject_on_worker_lost` a mensagem volta
para a fila, e aí a task pode rodar de novo. Rodar de novo sem olhar a linha estraga: o cancel que
já terminou marca ERROR ("não possui evento publicado"), e o publish atrasado traz de volta o evento
que a pessoa removeu depois. A guarda descarta a reentrega quando a linha já não está PENDING.

A reentrega é simulada como o kombu a entrega: `delivery_info["redelivered"] = True` no request.
A chamada direta da task (o resto da suíte) não tem `delivery_info`, então a guarda não entra.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportCallIssue=false, reportFunctionMemberAccess=false

from __future__ import annotations

from unittest.mock import Mock, patch

from django.test import override_settings

import pytest

from apps.core.models import AuditLog, Solicitacao
from apps.core.tasks import task_cancel_solicitacao_from_gcal, task_publish_solicitacao_to_gcal
from apps.core.tests.factories import SolicitacaoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

OAUTH = override_settings(GCAL_CLIENT="google", GCAL_AUTH_MODE="oauth")
CLIENT_FACTORY = "apps.core.services.gcal_client_factory.get_oauth_client_for_user"


def _cliente(**metodos):
    client = Mock()
    client.get_default_calendar_id.return_value = "cal-org"
    client.calendar_accessible.return_value = True
    client.credential.google_email = "operador@example.invalid"
    client.get.return_value = None
    for nome, valor in metodos.items():
        setattr(client, nome, valor)
    return client


def _linha(gcal_status: str, external_event_id: str | None = None) -> Solicitacao:
    sol = SolicitacaoFactory(status="aprovado")
    sol.gcal_status = gcal_status
    sol.external_event_id = external_event_id
    sol.save(update_fields=["gcal_status", "external_event_id"])
    return sol


def _reentregue(task, *args, **kwargs):
    """Roda a task como o worker roda uma mensagem que voltou para a fila."""
    task.push_request(delivery_info={"redelivered": True})
    try:
        return task.run(*args, **kwargs)
    finally:
        task.pop_request()


def test_publish_e_cancel_gcal_tem_acks_late_e_reject_on_worker_lost():
    for task in (task_publish_solicitacao_to_gcal, task_cancel_solicitacao_from_gcal):
        assert task.acks_late is True, task.name
        assert task.reject_on_worker_lost is True, task.name


@OAUTH
def test_cancel_reentregue_com_linha_ja_desvinculada_nao_marca_erro():
    """O cancel terminou (NONE, sem id) e só faltou o ack: a reentrega não pode virar ERROR."""
    operador = UsuarioFactory()
    sol = _linha(Solicitacao.GCalStatus.NONE)
    client = _cliente()

    with patch(CLIENT_FACTORY, return_value=(client, "cal-org")):
        resultado = _reentregue(task_cancel_solicitacao_from_gcal, sol.id, operator_user_id=operador.pk)

    assert resultado["action"] == "SKIP"
    sol.refresh_from_db()
    assert sol.gcal_status == Solicitacao.GCalStatus.NONE
    assert not AuditLog.objects.filter(
        action=AuditLog.Action.PUBLISH_GCAL_ERROR, details__solicitacao_id=sol.id
    ).exists()
    client.delete.assert_not_called()


@OAUTH
def test_publish_reentregue_nao_ressuscita_evento_cancelado():
    """A pessoa removeu depois do publish: o publish que volta da fila não pode adotar o evento cancelado."""
    operador = UsuarioFactory()
    sol = _linha(Solicitacao.GCalStatus.NONE)
    client = _cliente()
    client.get.return_value = {"id": f"asv2{sol.id}", "status": "cancelled"}

    with patch(CLIENT_FACTORY, return_value=(client, "cal-org")):
        resultado = _reentregue(task_publish_solicitacao_to_gcal, sol.id, operator_user_id=operador.pk)

    assert resultado["action"] == "SKIP"
    client.update.assert_not_called()
    client.insert.assert_not_called()
    sol.refresh_from_db()
    assert sol.gcal_status == Solicitacao.GCalStatus.NONE


@OAUTH
def test_publish_reentregue_com_credencial_revogada_nao_rebaixa_linha_publicada():
    """A guarda vem antes do cliente OAuth: montar o cliente com token revogado marcaria ERROR."""
    operador = UsuarioFactory()
    sol = _linha(Solicitacao.GCalStatus.PUBLISHED, external_event_id="asv2-ja-publicado")

    with patch(CLIENT_FACTORY, side_effect=ValueError("invalid_grant")) as fabrica:
        resultado = _reentregue(task_publish_solicitacao_to_gcal, sol.id, operator_user_id=operador.pk)

    assert resultado["action"] == "SKIP"
    fabrica.assert_not_called()
    sol.refresh_from_db()
    assert sol.gcal_status == Solicitacao.GCalStatus.PUBLISHED


@OAUTH
def test_publish_reentregue_com_linha_pending_publica():
    """Controle: a linha ainda espera o publish (o worker caiu antes de terminar). A reentrega publica."""
    operador = UsuarioFactory()
    sol = _linha(Solicitacao.GCalStatus.PENDING)
    client = _cliente()
    client.insert.return_value = {"id": f"asv2{sol.id}"}

    with patch(CLIENT_FACTORY, return_value=(client, "cal-org")):
        resultado = _reentregue(task_publish_solicitacao_to_gcal, sol.id, operator_user_id=operador.pk)

    assert resultado["action"] == "CREATE"
    client.insert.assert_called_once()
    sol.refresh_from_db()
    assert sol.gcal_status == Solicitacao.GCalStatus.PUBLISHED


@OAUTH
def test_reapply_reentregue_com_linha_publicada_atualiza_o_google():
    """O reapply em lote não marca PENDING, e `redelivered` só diz que a mensagem voltou para a fila.

    O kombu marca `redelivered` também na mensagem que o worker só tinha reservado (prefetch) e
    devolveu no restart sem rodar. Com a guarda, o reapply de todo deploy virava SKIP calado e o
    Google ficava com o conteúdo velho. O reapply passa `exige_pending=False` e roda de novo.
    """
    operador = UsuarioFactory()
    sol = _linha(Solicitacao.GCalStatus.PUBLISHED)
    sol.external_event_id = f"asv2{sol.id}"
    sol.gcal_payload_hash = "hash-do-conteudo-anterior"
    sol.save(update_fields=["external_event_id", "gcal_payload_hash"])
    client = _cliente()
    client.get.return_value = {"id": sol.external_event_id, "status": "confirmed"}
    client.update.return_value = {"id": sol.external_event_id}

    with patch(CLIENT_FACTORY, return_value=(client, "cal-org")):
        resultado = _reentregue(
            task_publish_solicitacao_to_gcal, sol.id, operator_user_id=operador.pk, exige_pending=False
        )

    assert resultado["action"] == "UPDATE"
    client.update.assert_called_once()
    sol.refresh_from_db()
    assert sol.gcal_status == Solicitacao.GCalStatus.PUBLISHED
    assert sol.gcal_payload_hash != "hash-do-conteudo-anterior"


@OAUTH
def test_cancel_reentregue_com_linha_pending_cancela():
    """Controle: a linha ainda espera o cancel. A reentrega remove do Google e desvincula."""
    operador = UsuarioFactory()
    sol = _linha(Solicitacao.GCalStatus.PENDING, external_event_id="asv2-a-remover")
    client = _cliente()

    with patch(CLIENT_FACTORY, return_value=(client, "cal-org")):
        resultado = _reentregue(task_cancel_solicitacao_from_gcal, sol.id, operator_user_id=operador.pk)

    assert resultado["action"] == "DELETE"
    client.delete.assert_called_once()
    sol.refresh_from_db()
    assert sol.gcal_status == Solicitacao.GCalStatus.NONE
    assert sol.external_event_id is None


def test_acks_late_nao_e_global():
    """Só publish e cancel aguentam rodar de novo. A cópia do Google e o backup ficam como estão."""
    from apps.core.tasks import copiar_mudancas_do_google
    from apps.core.tasks_backup import perform_database_backup
    from config.celery import app

    assert app.conf.task_acks_late is False
    assert not app.conf.task_reject_on_worker_lost
    assert not copiar_mudancas_do_google.reject_on_worker_lost
    assert not perform_database_backup.reject_on_worker_lost


def test_visibility_timeout_maior_que_time_limit():
    """Com o limite acima do visibility_timeout, o Redis reentregaria a task ainda rodando."""
    from config.celery import app

    opcoes = app.conf.broker_transport_options or {}
    assert opcoes.get("visibility_timeout", 3600) > app.conf.task_time_limit
