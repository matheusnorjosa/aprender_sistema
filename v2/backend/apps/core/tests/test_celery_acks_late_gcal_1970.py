"""Publicar e remover do Google sobrevivem à queda do worker sem estragar a linha (#1970).

Sem `acks_late`, o Celery confirma a mensagem ANTES de rodar a task: se o worker cai no meio, a
publicação some e a linha fica PENDING. Com `acks_late` + `reject_on_worker_lost` a mensagem volta
para a fila, e aí a task pode rodar de novo. Rodar de novo sem olhar a linha estraga: o cancel que
já terminou marca ERROR ("não possui evento publicado"), e o publish atrasado traz de volta o evento
que a pessoa removeu depois. A guarda olha a linha: publish exige PENDING, o reapply (`reenvio`) recusa
NONE, e o cancel só desiste quando não há mais o que remover.

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
    Google ficava com o conteúdo velho. O reapply passa `reenvio=True` e roda de novo.
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
        resultado = _reentregue(task_publish_solicitacao_to_gcal, sol.id, operator_user_id=operador.pk, reenvio=True)

    assert resultado["action"] == "UPDATE"
    client.update.assert_called_once()
    sol.refresh_from_db()
    assert sol.gcal_status == Solicitacao.GCalStatus.PUBLISHED
    assert sol.gcal_payload_hash != "hash-do-conteudo-anterior"


@OAUTH
@pytest.mark.parametrize("reentregue", [True, False], ids=["reentrega", "primeira-entrega"])
def test_reapply_com_linha_desvinculada_nao_ressuscita_evento_cancelado(reentregue):
    """A pessoa removeu do Google depois do reapply ir para a fila: a linha está NONE e sem id.

    O cancel zera o hash e o id, então o upsert não tem o que pular: sem a conferência, o reapply
    adota o `asv2{id}` cancelado e o traz de volta. Vale em toda entrega, não só na reentrega.
    """
    operador = UsuarioFactory()
    sol = _linha(Solicitacao.GCalStatus.NONE)
    client = _cliente()
    client.get.return_value = {"id": f"asv2{sol.id}", "status": "cancelled"}

    with patch(CLIENT_FACTORY, return_value=(client, "cal-org")) as fabrica:
        if reentregue:
            resultado = _reentregue(
                task_publish_solicitacao_to_gcal, sol.id, operator_user_id=operador.pk, reenvio=True
            )
        else:
            resultado = task_publish_solicitacao_to_gcal.run(sol.id, operator_user_id=operador.pk, reenvio=True)

    assert resultado["action"] == "SKIP"
    fabrica.assert_not_called()
    client.update.assert_not_called()
    client.insert.assert_not_called()
    sol.refresh_from_db()
    assert sol.gcal_status == Solicitacao.GCalStatus.NONE
    assert sol.external_event_id is None


@OAUTH
def test_cancel_reentregue_com_linha_publicada_remove_do_google():
    """Uma resync terminou (PUBLISHED) enquanto o cancel pedido depois esperava na fila.

    A última ação da pessoa foi remover: com o evento ainda vinculado, o cancel reentregue remove.
    """
    operador = UsuarioFactory()
    sol = _linha(Solicitacao.GCalStatus.PUBLISHED)
    sol.external_event_id = f"asv2{sol.id}"
    sol.save(update_fields=["external_event_id"])
    client = _cliente()

    with patch(CLIENT_FACTORY, return_value=(client, "cal-org")):
        resultado = _reentregue(task_cancel_solicitacao_from_gcal, sol.id, operator_user_id=operador.pk)

    assert resultado["action"] == "DELETE"
    client.delete.assert_called_once()
    sol.refresh_from_db()
    assert sol.gcal_status == Solicitacao.GCalStatus.NONE
    assert sol.external_event_id is None


@OAUTH
def test_cancel_reentregue_sem_evento_vinculado_nao_marca_erro_na_publicacao_pendente():
    """O cancel terminou e a pessoa publicou de novo (PENDING, ainda sem id): o cancel que volta não tem o
    que remover e não pode marcar ERROR por cima da publicação que espera na fila."""
    operador = UsuarioFactory()
    sol = _linha(Solicitacao.GCalStatus.PENDING)
    client = _cliente()

    with patch(CLIENT_FACTORY, return_value=(client, "cal-org")):
        resultado = _reentregue(task_cancel_solicitacao_from_gcal, sol.id, operator_user_id=operador.pk)

    assert resultado["action"] == "SKIP"
    client.delete.assert_not_called()
    sol.refresh_from_db()
    assert sol.gcal_status == Solicitacao.GCalStatus.PENDING


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


def _cancel_termina_durante(sol: Solicitacao):
    """Fábrica OAuth que, ao montar o cliente, deixa outro worker concluir o cancel da linha.

    Reproduz o intervalo entre a guarda (leitura sem lock) e o `select_for_update`: a guarda viu a
    linha esperando a operação, e o cancel commitou NONE, sem id e sem hash, antes do lock.
    """
    client = _cliente()
    client.get.return_value = {"id": f"asv2{sol.id}", "status": "cancelled"}
    client.update.return_value = {"id": f"asv2{sol.id}"}

    def _fabrica(_operador):
        Solicitacao.objects.filter(pk=sol.pk).update(
            gcal_status=Solicitacao.GCalStatus.NONE, external_event_id=None, gcal_payload_hash=None
        )
        return client, "cal-org"

    return client, _fabrica


@OAUTH
@pytest.mark.parametrize(
    ("reenvio", "reentregue"),
    [(True, False), (False, True)],
    ids=["reapply", "publish-reentregue"],
)
def test_publish_nao_ressuscita_evento_cancelado_entre_a_guarda_e_o_lock(reenvio, reentregue):
    """A guarda leu PENDING sem lock; o cancel commitou NONE antes do `select_for_update`.

    Sob o lock a task relê a linha e tem de desistir: sem isso o upsert adota o `asv2{id}` cancelado
    (o delete do Google é soft-delete) e o traz de volta, com a linha PUBLISHED.
    """
    operador = UsuarioFactory()
    sol = _linha(Solicitacao.GCalStatus.PENDING, external_event_id="asv2-em-remocao")
    client, fabrica = _cancel_termina_durante(sol)

    with patch(CLIENT_FACTORY, side_effect=fabrica):
        if reentregue:
            resultado = _reentregue(task_publish_solicitacao_to_gcal, sol.id, operator_user_id=operador.pk)
        else:
            resultado = task_publish_solicitacao_to_gcal.run(sol.id, operator_user_id=operador.pk, reenvio=reenvio)

    assert resultado["action"] == "SKIP"
    client.update.assert_not_called()
    client.insert.assert_not_called()
    sol.refresh_from_db()
    assert sol.gcal_status == Solicitacao.GCalStatus.NONE
    assert sol.external_event_id is None


@OAUTH
def test_cancel_reentregue_nao_marca_erro_quando_a_copia_original_termina_entre_a_guarda_e_o_lock():
    """Duas cópias da mesma mensagem: a original terminou enquanto a reentrega montava o cliente.

    Sob o lock a linha está NONE e sem id: não há o que remover, e a reentrega não pode virar ERROR.
    """
    operador = UsuarioFactory()
    sol = _linha(Solicitacao.GCalStatus.PENDING, external_event_id="asv2-em-remocao")
    client, fabrica = _cancel_termina_durante(sol)

    with patch(CLIENT_FACTORY, side_effect=fabrica):
        resultado = _reentregue(task_cancel_solicitacao_from_gcal, sol.id, operator_user_id=operador.pk)

    assert resultado["action"] == "SKIP"
    client.delete.assert_not_called()
    sol.refresh_from_db()
    assert sol.gcal_status == Solicitacao.GCalStatus.NONE
    assert not AuditLog.objects.filter(
        action=AuditLog.Action.PUBLISH_GCAL_ERROR, details__solicitacao_id=sol.id
    ).exists()
