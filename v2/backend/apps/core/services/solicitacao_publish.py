"""
Solicitacao Publish Service - §1 Epic #459

Service layer for Google Calendar publish/resync/cancel operations.
Extracted from views_solicitacao.py to follow Single Responsibility Principle.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportFunctionMemberAccess=false, reportCallIssue=false

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Literal
from uuid import uuid4

from django.conf import settings
from django.db import OperationalError, connection, transaction
from django.utils import timezone

from kombu.exceptions import OperationalError as FilaForaDoAr

from apps.core.exceptions import APIError, ConflictError, ValidationAPIError
from apps.core.models import AuditLog, GoogleOAuthCredential, Solicitacao, Usuario
from apps.core.services.availability_service import cancelado_confirmado
from apps.core.services.db_retry import _extract_pgcode  # pyright: ignore[reportPrivateUsage]
from apps.core.services.evento_de_formacao import eh_evento_de_formacao, falta_numero_da_formacao
from apps.core.utils.net import get_client_ip

logger = logging.getLogger(__name__)

# Quem desiste de esperar a trava da linha diz isto: a edição (DEF-30) e o pedido de operação no Google (DEF-32).
MSG_LINHA_OCUPADA = (
    "Este evento está sendo alterado por outra operação agora (como a publicação no Google Agenda ou "
    "uma aprovação). Tente de novo em instantes."
)

# Teto da espera do pedido pela trava da linha, o mesmo da edição: abaixo do statement_timeout de produção
# (30 s), para desistir com "tente de novo" e não com o 500 do statement cancelado.
_PEDIDO_LOCK_TIMEOUT = "10s"

_MSG_FILA_INDISPONIVEL = (
    "Não foi possível enviar o pedido para a fila de publicação. Nada foi alterado. Tente de novo em instantes."
)

_MSG_OPERACAO_EM_ANDAMENTO = (
    "Este evento já tem uma operação no Google em andamento. Espere alguns minutos; se não terminar, siga "
    "«Evento parado em Publicando…» no GUIDE_GCAL (não reenvie se foi um Tirar do Google)."
)

# Erros do broker no `.delay`: o Celery embrulha os erros de conexão do Redis no OperationalError do kombu; os
# outros três são de socket. Qualquer outra exceção é defeito de código e sobe (500), sem virar "fila fora".
_ERROS_DA_FILA = (FilaForaDoAr, ConnectionError, TimeoutError, OSError)

# Por que o evento não pode ir ao Google agora (virada, 16/10/2026). Mensagem para a tela e o lote.
MENSAGENS_NAO_PUBLICAVEL: dict[str, str] = {
    "cancelado_na_agenda": (
        "Este evento foi cancelado na agenda: ele fica no Google com (CANCELADO) no título e não se publica "
        "nem se reenvia de novo."
    ),
    "publicado_fora_do_sistema": (
        "Este evento já está no Google Agenda pela planilha e o sistema não o adotou: publicar criaria um "
        "segundo evento. Ajuste no Google, ou peça a adoção."
    ),
    "evento_passado": "Este evento já terminou: o sistema não publica nem reenvia evento passado.",
    "ja_publicado": "Este evento já foi publicado (ou está sendo). Use Atualizar no Google.",
    "nao_publicado": "Este evento ainda não foi publicado: use Publicar, não Reaplicar nem Reenviar.",
    "sem_numero_da_formacao": (
        "Este evento de formação está sem o Nº da formação (só o número, de 1 a 999), e o título no Google "
        "precisa dele. Informe o número antes de publicar ou reenviar."
    ),
}


def motivo_nao_publicavel(s: Solicitacao, *, reenvio: bool = False) -> str | None:
    """Código do motivo para recusar Publicar (`reenvio=False`) ou Reapply/Resync (`reenvio=True`),
    ou None se pode. Vem antes de enfileirar; a guarda final do CREATE fica no `upsert_one`.

    Publicar: recusa o já publicado (PUBLISHED ou PENDING; ERROR pode tentar de novo). Reenvio: recusa o
    que nunca foi ao Google (`NONE`), porque nele o sync cria. Os dois recusam o evento que já terminou e
    o que está no Google pela planilha sem adoção (`publicado_fora_do_sistema`). Depois desses, os dois recusam
    o evento de formação sem o Nº da formação (`sem_numero_da_formacao`, CON-09): sem ele o título no Google sai
    fora da forma que o DFF lê. Antes de tudo, os dois recusam a linha cancelada na agenda (`cancelado_na_agenda`,
    CON-08): o envio tiraria o "(CANCELADO) " do título e traria de volta o evento."""
    if s.cancelado_na_agenda:
        return "cancelado_na_agenda"
    if s.publicado_fora_do_sistema:
        return "publicado_fora_do_sistema"
    if s.fim < timezone.now():
        return "evento_passado"
    if reenvio:
        if s.gcal_status == Solicitacao.GCalStatus.NONE:
            return "nao_publicado"
    elif s.gcal_status in (Solicitacao.GCalStatus.PUBLISHED, Solicitacao.GCalStatus.PENDING):
        return "ja_publicado"
    if falta_numero_da_formacao(s):
        return "sem_numero_da_formacao"
    return None


_MSG_CANCELADO_NA_AGENDA_NAO_TIRA = (
    "Este evento foi cancelado na agenda: ele fica no Google com (CANCELADO) no título e não se tira de lá por aqui."
)
_MSG_NAO_E_EVENTO_DE_FORMACAO = (
    "Só evento de formação (Presencial, Online ou Workshop) se cancela na agenda. Para os outros, use Tirar só "
    "do Google ou Excluir."
)


_MSG_JA_CANCELADO_NA_AGENDA = (
    "Este evento já foi cancelado na agenda: o título no Google já tem (CANCELADO) e não há o que refazer."
)


_MSG_CANCELAR_NA_AGENDA_DESLIGADO = (
    "O Cancelar evento não está disponível no sistema agora. Para tirar o evento do Google Agenda, use Tirar só do "
    "Google ou Excluir."
)


def cancelar_na_agenda_ligado() -> bool:
    """A chave do CON-08 B (`CON08_CANCELAR_NA_AGENDA`, desligada por padrão)."""
    return bool(getattr(settings, "CON08_CANCELAR_NA_AGENDA", False))


def _recusar_se_desligado() -> None:
    """Com a chave desligada, ninguém cancela na agenda (409 `cancelar_na_agenda_desligado`)."""
    if not cancelar_na_agenda_ligado():
        raise ConflictError(message=_MSG_CANCELAR_NA_AGENDA_DESLIGADO, details={"code": "cancelar_na_agenda_desligado"})


def excluir_marca_cancelado(s: Solicitacao) -> bool:
    """O Excluir desta linha, que está no Google, marca o título com "(CANCELADO) " em vez de tirar o evento
    de lá? Sim para evento de formação e para a linha já cancelada na agenda (decisão do dono, 23/11/2026).

    Com a chave do CON-08 B desligada, só a linha cujo Cancelar terminou no Google (`cancelamento_confirmado`,
    marcada quando a chave esteve ligada): o título dela lá já tem o "(CANCELADO)", e apagar o evento desfaria o
    cancelamento que o DFF já leu. O evento de formação não marcado volta a sair do Google, como antes do #2255. A
    linha marcada sem Cancelar confirmado (ERROR: o Cancelar falhou antes do Google) também: marcar o título agora
    seria um cancelamento novo com a chave desligada (revisão da rodada 1 da chave). É o mesmo critério da tarefa
    que fica na fila (`_cancelar_na_agenda_desligado`), e o Tirar só do Google também a aceita (`pedir_operacao_gcal`).
    """
    if s.cancelado_na_agenda:
        return cancelar_na_agenda_ligado() or cancelamento_confirmado(s)
    return cancelar_na_agenda_ligado() and eh_evento_de_formacao(s)


# Desfechos de um Cancelar que terminou (`task_cancelar_na_agenda`, ou o remover do Excluir que não apagou a linha).
_CANCELAR_TERMINOU = ("marcado", "ja_marcado", "ja_saiu")


def cancelamento_confirmado(s: Solicitacao) -> bool:
    """O Cancelar desta linha já terminou no Google (o "(CANCELADO) " foi para lá, ou o evento já tinha saído)?

    A marca `cancelado_na_agenda` é gravada no pedido, antes do Google, então sozinha não diz isso: a linha ERROR
    marcada pode ser um Cancelar que falhou antes do Google (sem acesso, 5xx). Confirmado = linha PUBLISHED com a
    marca (só a tarefa que terminou a deixa assim) ou um `CANCELAR_NA_AGENDA` com desfecho de quem terminou. Decide
    o que fazer com o id adotado que o Google não acha (P5, revisão da rodada 5): confirmado, o evento sumiu depois
    de cancelado e a linha conclui; sem confirmação, o id pode estar errado (o evento lá com outro id, sem a
    marca), e o Excluir recusa e a tarefa desfaz a marca."""
    if not s.cancelado_na_agenda:
        return False
    if cancelado_confirmado(s):
        return True
    return AuditLog.objects.filter(
        action=AuditLog.Action.CANCELAR_NA_AGENDA,
        model_name="Solicitacao",
        details__solicitacao_id=s.pk,
        details__resultado__in=_CANCELAR_TERMINOU,
    ).exists()


OperacaoGcal = Literal["publicar", "reenviar", "reaplicar", "cancelar", "cancelar_na_agenda"]


def pedir_operacao_gcal(solicitacao_id: int, operacao: OperacaoGcal) -> str:
    """Registra o pedido de uma operação no Google e devolve o identificador dele (DEF-32).

    Trava a linha, confere sobre ela o que a entrada conferiu sem trava, grava um identificador novo em
    `gcal_pedido` e marca PENDING. A tarefa recebe o identificador e só age se ele ainda for o da linha.

    Exige transação aberta por quem chama e não abre outra: o `.delay` da tarefa entra na mesma transação,
    e a fila fora do ar desfaz o PENDING. Fora de transação o `select_for_update` levanta.

    Hash do payload: publicar e reenviar zeram (o envio é forçado); cancelar e cancelar na agenda mantêm;
    reaplicar mantém só o de linha PUBLISHED, para o envio sem mudança virar SKIP.

    Cancelar na agenda (CON-08) só com a chave `CON08_CANCELAR_NA_AGENDA` ligada (desligada, recusa antes de travar
    a linha). Aceita o que o cancelar aceita, só em evento de formação ou na linha já marcada
    (o refazer do Cancelar que falhou, mesmo com o tipo renomeado: `excluir_marca_cancelado`), e grava a marca
    `cancelado_na_agenda` aqui, no pedido: já no PENDING a linha não se publica, não se reenvia e não se tira
    do Google (o cancelar recusa a linha marcada; com a chave desligada, só a de Cancelar confirmado, e a marca da
    outra sai com o evento em `cancel_solicitacao`). Pela tela não há desfazer; só a tarefa do Cancelar tira a marca,
    quando o Event ID adotado não é achado e nenhum Cancelar anterior terminou (gcal.spec, "A tarefa"). A marca
    sozinha não libera a agenda: só com a linha de volta a PUBLISHED pela tarefa (`cancelado_confirmado_q`). A
    linha marcada só se pede de novo em PENDING ou ERROR (o refazer); fora deles o Cancelar já terminou (409
    `ja_cancelado_na_agenda`).

    Reaplicar sobre linha em PENDING é recusado: outra operação está em andamento, e o pedido novo zeraria o
    hash (UPDATE sem mudança no Google, com e-mail aos convidados) ou desfaria um "Tirar do Google".

    Raises:
        ConflictError `linha_ocupada`: outra operação segurou a linha além de `_PEDIDO_LOCK_TIMEOUT`.
        ConflictError `operacao_em_andamento`: reaplicar sobre linha em PENDING.
        ValidationAPIError, ConflictError: as recusas das entradas, agora sobre a linha travada.
        Solicitacao.DoesNotExist: a linha foi apagada depois da leitura de quem chama.
        ConflictError `cancelar_na_agenda_desligado`: cancelar na agenda com a chave do CON-08 B desligada.
    """
    if operacao == "cancelar_na_agenda":
        _recusar_se_desligado()
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('lock_timeout', %s, true)", [_PEDIDO_LOCK_TIMEOUT])
    try:
        s = Solicitacao.objects.select_for_update().get(pk=solicitacao_id)
    except OperationalError as exc:
        if _extract_pgcode(exc) != "55P03":  # lock_not_available
            raise
        raise ConflictError(message=MSG_LINHA_OCUPADA, details={"code": "linha_ocupada"}) from exc

    if operacao == "reaplicar" and s.gcal_status == Solicitacao.GCalStatus.PENDING:
        raise ConflictError(message=_MSG_OPERACAO_EM_ANDAMENTO, details={"code": "operacao_em_andamento"})

    # A linha já marcada refaz o Cancelar mesmo com o tipo renomeado (a mesma regra do Excluir).
    if operacao == "cancelar_na_agenda" and not excluir_marca_cancelado(s):
        raise ConflictError(message=_MSG_NAO_E_EVENTO_DE_FORMACAO, details={"code": "nao_e_evento_de_formacao"})
    # Linha marcada fora de PENDING e de ERROR: o Cancelar já terminou (revisão da rodada 5). Refeito, ele só
    # poderia tirar a marca confirmada (id adotado que sumiu do Google depois).
    if (
        operacao == "cancelar_na_agenda"
        and s.cancelado_na_agenda
        and s.gcal_status not in (Solicitacao.GCalStatus.PENDING, Solicitacao.GCalStatus.ERROR)
    ):
        raise ConflictError(message=_MSG_JA_CANCELADO_NA_AGENDA, details={"code": "ja_cancelado_na_agenda"})
    # A linha marcada não se tira do Google, salvo com a chave desligada e sem Cancelar confirmado (o título lá não
    # tem a marca): aí o Tirar é a saída dela, e a marca sai com o evento (`cancel_solicitacao`).
    if operacao == "cancelar" and s.cancelado_na_agenda and excluir_marca_cancelado(s):
        raise ConflictError(message=_MSG_CANCELADO_NA_AGENDA_NAO_TIRA, details={"code": "cancelado_na_agenda"})

    if operacao in ("cancelar", "cancelar_na_agenda"):
        if not s.external_event_id and s.gcal_status != Solicitacao.GCalStatus.PUBLISHED:
            raise ConflictError(
                message="Solicitação não possui evento publicado no Google Calendar.",
                details={
                    "code": "not_published",
                    "hint": "Apenas eventos publicados podem ser cancelados.",
                },
            )
    else:
        reenvio = operacao != "publicar"
        if s.status != "aprovado":
            raise ValidationAPIError(
                message=(
                    "Apenas solicitações aprovadas podem ser resincronizadas."
                    if reenvio
                    else "Apenas solicitações aprovadas podem ser publicadas no Google Calendar."
                ),
                code="not_approved",
            )
        motivo = motivo_nao_publicavel(s, reenvio=reenvio)
        if motivo is not None:
            raise ValidationAPIError(message=MENSAGENS_NAO_PUBLICAVEL[motivo], code=motivo)

    mantem_hash = operacao in ("cancelar", "cancelar_na_agenda") or (
        operacao == "reaplicar" and s.gcal_status == Solicitacao.GCalStatus.PUBLISHED
    )
    s.gcal_pedido = uuid4().hex
    campos = ["gcal_pedido"]
    if operacao == "cancelar_na_agenda":
        s.cancelado_na_agenda = True
        campos.append("cancelado_na_agenda")
    s.save(update_fields=campos)
    s.mark_gcal(
        status=Solicitacao.GCalStatus.PENDING,
        payload_hash=s.gcal_payload_hash if mantem_hash else None,
        error="",
    )
    return s.gcal_pedido


def enfileirar_tarefa_gcal(tarefa: Any, solicitacao_id: int, **kwargs: Any) -> Any:
    """`.delay` da tarefa, de dentro da transação do pedido.

    Fila fora do ar (`_ERROS_DA_FILA`) vira 503 `fila_indisponivel`; ao sair do `atomic` de quem chama, o erro
    desfaz o PENDING e o identificador. Não fica pedido gravado sem tarefa na fila. Outro erro sobe como veio
    (500) e desfaz do mesmo jeito.
    """
    try:
        return tarefa.delay(solicitacao_id, **kwargs)
    except _ERROS_DA_FILA as exc:
        logger.exception(
            "gcal_fila_indisponivel",
            extra={"event": "gcal_fila_indisponivel", "solicitacao_id": solicitacao_id},
        )
        raise APIError(code="fila_indisponivel", message=_MSG_FILA_INDISPONIVEL, status_code=503) from exc


@dataclass
class PublishResult:
    """Result of a publish/resync operation."""

    success: bool
    task_id: str
    solicitacao_id: int
    message: str
    dry_run: bool = False


@dataclass
class CancelResult:
    """Result of a cancel operation."""

    success: bool
    task_id: str
    solicitacao_id: int
    message: str


@dataclass
class PreviewResult:
    """Result of a preview operation."""

    success: bool
    preview: dict[str, Any]
    message: str


def oauth_publish_block_reason(user: Usuario) -> str | None:
    """Por que `user` não pode escrever no GCal agora (modo OAuth), ou None se pode.

    - `google_not_connected`: sem credencial Google;
    - `google_calendar_not_configured`: sem calendário de publicação (sem o pino da organização
      `GCAL_OAUTH_CALENDAR_ID` e sem escolha na credencial) — nunca cair no calendário pessoal.
    Fora do modo OAuth → None (o service account resolve o calendário por conta própria).
    """
    if getattr(settings, "GCAL_AUTH_MODE", "service_account") != "oauth":
        return None
    try:
        credential = GoogleOAuthCredential.objects.get(user=user)
    except GoogleOAuthCredential.DoesNotExist:
        return "google_not_connected"
    from apps.core.services.gcal_oauth_client import resolve_publish_calendar_id

    if not resolve_publish_calendar_id(credential):
        return "google_calendar_not_configured"
    return None


def _check_google_oauth(user: Usuario) -> int | None:
    """
    Check if user can write to Google Calendar in OAuth mode (roda ANTES de marcar PENDING).

    Returns:
        operator_user_id if OAuth mode and the user can write, None outside OAuth mode

    Raises:
        APIError 403 `google_not_connected`: OAuth mode and no credentials found
        APIError 409 `google_calendar_not_configured`: no organization calendar to write to
    """
    if getattr(settings, "GCAL_AUTH_MODE", "service_account") != "oauth":
        return None

    reason = oauth_publish_block_reason(user)
    if reason == "google_not_connected":
        raise APIError(
            code="google_not_connected",
            message="Conecte sua conta Google",
            status_code=403,
        )
    if reason == "google_calendar_not_configured":
        raise APIError(
            code="google_calendar_not_configured",
            message="A agenda da organização ainda não foi configurada no sistema. Avise o Controle.",
            status_code=409,
        )
    return user.pk


def preview_gcal(
    solicitacao: Solicitacao,
    user: Usuario,
    request: Any,
) -> PreviewResult:
    """
    Generate preview of GCal payload without publishing.

    Args:
        solicitacao: The solicitacao to preview
        user: The user requesting the preview
        request: The HTTP request (for IP/user-agent logging)

    Returns:
        PreviewResult with preview data
    """
    from apps.core.services.gcal_sync_service import build_preview_for_solicitacao

    preview = build_preview_for_solicitacao(solicitacao)

    client_ip = get_client_ip(request)
    AuditLog.objects.create(
        usuario=user,
        action=AuditLog.Action.PREVIEW_GCAL,
        model_name="Solicitacao",
        details={
            "solicitacao_id": solicitacao.id,
            "event_id": preview["event_id"],
            "summary": preview["payload"].get("summary", ""),
            "payload_hash": preview.get("payload_hash", ""),
            "ip_address": client_ip,
        },
    )

    logger.info(
        "preview_gcal",
        extra={
            "event": "preview_gcal",
            "user_id": user.id,
            "solicitacao_id": solicitacao.id,
            "event_id": preview["event_id"],
            "ip_address": client_ip,
            "timestamp": timezone.now().isoformat(),
        },
    )

    return PreviewResult(
        success=True,
        preview=preview,
        message="Preview gerado com sucesso.",
    )


def _warn_if_participants_unavailable(solicitacao: Solicitacao) -> None:
    """
    Registra (sem bloquear) participantes com conflito num evento já aprovado (#1452).

    Sinaliza double-booking legado, anterior ao enforcement na criação/aprovação.
    """
    from apps.core.services.solicitacao_availability import check_solicitacao_availability

    guard = check_solicitacao_availability(solicitacao, lock=False)
    if guard.ok:
        return

    logger.warning(
        "publish_availability_conflict_detected",
        extra={
            "event": "publish_availability_conflict_detected",
            "solicitacao_id": solicitacao.id,
            "blocked_usuario_ids": [p.usuario_id for p in guard.blocked],
        },
    )


def publish_to_gcal(
    solicitacao: Solicitacao,
    user: Usuario,
    request: Any,
    dry_run: bool = False,
    apply_blocked: bool = False,
) -> PublishResult:
    """
    Publish solicitacao to Google Calendar via Celery.

    Args:
        solicitacao: The solicitacao to publish
        user: The user performing the publish
        request: The HTTP request (for IP/user-agent logging)
        dry_run: If True, simulate without actual publish
        apply_blocked: If True, force publish even if GCAL_CLIENT != "google"

    Returns:
        PublishResult with task details

    Raises:
        ValidationAPIError: If not approved, OAuth missing, or apply blocked
    """
    from apps.core.tasks import task_publish_solicitacao_to_gcal

    # Check OAuth credentials
    operator_user_id = _check_google_oauth(user)

    # Validate status
    if solicitacao.status != "aprovado":
        raise ValidationAPIError(
            message="Apenas solicitações aprovadas podem ser publicadas no Google Calendar.",
            code="not_approved",
        )
    motivo = motivo_nao_publicavel(solicitacao)
    if motivo is not None:
        raise ValidationAPIError(message=MENSAGENS_NAO_PUBLICAVEL[motivo], code=motivo)

    # #1452: revalidação NÃO bloqueante, de propósito.
    #
    # Publicar não aloca nada — o evento já está aprovado e ocupa a agenda desde então.
    # Com o enforcement na criação e na aprovação, dois eventos aprovados conflitantes só
    # existem em dados anteriores a esta correção; bloquear a publicação deles puniria o
    # operador por um evento que a instituição já assumiu. Então aqui só registramos, para
    # que o double-booking legado apareça em vez de passar despercebido.
    _warn_if_participants_unavailable(solicitacao)

    # Check if apply is blocked
    gcal_client = getattr(settings, "GCAL_CLIENT", None)
    features_apply_blocked = gcal_client != "google"

    if features_apply_blocked and not apply_blocked and not dry_run:
        raise ConflictError(
            message="Publicação bloqueada: GCAL_CLIENT não está configurado como 'google'.",
            details={
                "code": "gcal_client_not_configured",
                "hint": "Para forçar publicação em modo de teste, envie apply_blocked=true no corpo da requisição.",
                "features_apply_blocked": True,
                "dry_run_allowed": True,
            },
        )

    kwargs: dict[str, Any] = {"dry_run": dry_run, "apply_blocked": apply_blocked}
    if getattr(settings, "GCAL_AUTH_MODE", "service_account") == "oauth":
        kwargs["operator_user_id"] = operator_user_id
    client_ip = get_client_ip(request)
    detalhes = {
        "solicitacao_id": solicitacao.id,
        "dry_run": dry_run,
        "apply_blocked": apply_blocked,
        "ip_address": client_ip,
    }
    if dry_run:
        # A prévia não grava nada na linha: sem pedido e fora de transação.
        task = task_publish_solicitacao_to_gcal.delay(solicitacao.id, **kwargs)
        AuditLog.objects.create(
            usuario=user,
            action=AuditLog.Action.PUBLISH_GCAL_REQUESTED,
            model_name="Solicitacao",
            details={**detalhes, "task_id": task.id},
        )
    else:
        # DEF-32: o pedido (PENDING sob trava), a tarefa e o registro numa transação só.
        with transaction.atomic():
            pedido = pedir_operacao_gcal(solicitacao.id, "publicar")
            task = enfileirar_tarefa_gcal(task_publish_solicitacao_to_gcal, solicitacao.id, **kwargs, pedido=pedido)
            AuditLog.objects.create(
                usuario=user,
                action=AuditLog.Action.PUBLISH_GCAL_REQUESTED,
                model_name="Solicitacao",
                details={**detalhes, "task_id": task.id, "pedido": pedido},
            )

    logger.info(
        "publish_gcal_requested",
        extra={
            "event": "publish_gcal_requested",
            "user_id": user.id,
            "solicitacao_id": solicitacao.id,
            "task_id": task.id,
            "dry_run": dry_run,
            "apply_blocked": apply_blocked,
            "ip_address": client_ip,
            "timestamp": timezone.now().isoformat(),
        },
    )

    return PublishResult(
        success=True,
        task_id=task.id,
        solicitacao_id=solicitacao.id,
        message="Publicação solicitada com sucesso (processando em background).",
        dry_run=dry_run,
    )


def resync_to_gcal(
    solicitacao: Solicitacao,
    user: Usuario,
    request: Any,
) -> PublishResult:
    """
    Republish solicitacao to Google Calendar (force UPDATE).

    Resets gcal_payload_hash to force UPDATE even if already published.

    Args:
        solicitacao: The solicitacao to resync
        user: The user performing the resync
        request: The HTTP request (for IP/user-agent logging)

    Returns:
        PublishResult with task details

    Raises:
        ValidationAPIError: If not approved, OAuth missing, or `motivo_nao_publicavel(reenvio=True)`
    """
    from apps.core.tasks import task_publish_solicitacao_to_gcal

    # Check OAuth credentials
    operator_user_id = _check_google_oauth(user)

    # Validate status
    if solicitacao.status != "aprovado":
        raise ValidationAPIError(
            message="Apenas solicitações aprovadas podem ser resincronizadas.",
            code="not_approved",
        )
    # D64: o Reenviar de uma linha recusa o mesmo que o lote (evento passado, nunca publicado, fora do sistema).
    motivo = motivo_nao_publicavel(solicitacao, reenvio=True)
    if motivo is not None:
        raise ValidationAPIError(message=MENSAGENS_NAO_PUBLICAVEL[motivo], code=motivo)

    kwargs: dict[str, Any] = {"dry_run": False, "apply_blocked": False}
    if getattr(settings, "GCAL_AUTH_MODE", "service_account") == "oauth":
        kwargs["operator_user_id"] = operator_user_id
    client_ip = get_client_ip(request)
    # DEF-32: o pedido (PENDING sob trava, hash zerado para forçar o UPDATE), a tarefa e o registro numa
    # transação só.
    with transaction.atomic():
        pedido = pedir_operacao_gcal(solicitacao.id, "reenviar")
        task = enfileirar_tarefa_gcal(task_publish_solicitacao_to_gcal, solicitacao.id, **kwargs, pedido=pedido)
        AuditLog.objects.create(
            usuario=user,
            action=AuditLog.Action.RESYNC_GCAL_REQUESTED,
            model_name="Solicitacao",
            details={
                "solicitacao_id": solicitacao.id,
                "task_id": task.id,
                "pedido": pedido,
                "ip_address": client_ip,
            },
        )

    logger.info(
        "resync_gcal_requested",
        extra={
            "event": "resync_gcal_requested",
            "user_id": user.id,
            "solicitacao_id": solicitacao.id,
            "task_id": task.id,
            "ip_address": client_ip,
            "timestamp": timezone.now().isoformat(),
        },
    )

    return PublishResult(
        success=True,
        task_id=task.id,
        solicitacao_id=solicitacao.id,
        message="Resincronização solicitada com sucesso (processando em background).",
        dry_run=False,
    )


def cancel_from_gcal(
    solicitacao: Solicitacao,
    user: Usuario,
    request: Any,
) -> CancelResult:
    """
    Cancel event in Google Calendar and clear fields.

    Deletes event from Calendar (treats 404 as success - idempotency).

    Args:
        solicitacao: The solicitacao to cancel
        user: The user performing the cancel
        request: The HTTP request (for IP/user-agent logging)

    Returns:
        CancelResult with task details

    Raises:
        ConflictError: If event was not published
    """
    from apps.core.tasks import task_cancel_solicitacao_from_gcal

    # Check OAuth credentials (fix #572)
    operator_user_id = _check_google_oauth(user)

    # Validate that event was published
    if not solicitacao.external_event_id and solicitacao.gcal_status != Solicitacao.GCalStatus.PUBLISHED:
        raise ConflictError(
            message="Solicitação não possui evento publicado no Google Calendar.",
            details={
                "code": "not_published",
                "hint": "Apenas eventos publicados podem ser cancelados.",
            },
        )

    kwargs: dict[str, Any] = {}
    if getattr(settings, "GCAL_AUTH_MODE", "service_account") == "oauth":
        kwargs["operator_user_id"] = operator_user_id
    client_ip = get_client_ip(request)
    # DEF-32: o pedido (PENDING sob trava, hash mantido; a tarefa grava NONE depois do delete), a tarefa e o
    # registro numa transação só.
    with transaction.atomic():
        pedido = pedir_operacao_gcal(solicitacao.id, "cancelar")
        task = enfileirar_tarefa_gcal(task_cancel_solicitacao_from_gcal, solicitacao.id, **kwargs, pedido=pedido)
        AuditLog.objects.create(
            usuario=user,
            action=AuditLog.Action.CANCEL_GCAL_REQUESTED,
            model_name="Solicitacao",
            details={
                "solicitacao_id": solicitacao.id,
                "task_id": task.id,
                "pedido": pedido,
                "external_event_id": solicitacao.external_event_id,
                "ip_address": client_ip,
            },
        )

    logger.info(
        "cancel_gcal_requested",
        extra={
            "event": "cancel_gcal_requested",
            "user_id": user.id,
            "solicitacao_id": solicitacao.id,
            "task_id": task.id,
            "external_event_id": solicitacao.external_event_id,
            "ip_address": client_ip,
            "timestamp": timezone.now().isoformat(),
        },
    )

    return CancelResult(
        success=True,
        task_id=task.id,
        solicitacao_id=solicitacao.id,
        message="Cancelamento solicitado com sucesso (processando em background).",
    )


def cancelar_na_agenda(
    solicitacao: Solicitacao,
    user: Usuario,
    request: Any,
) -> CancelResult:
    """Cancela na agenda um evento de formação: o título no Google ganha "(CANCELADO) " (CON-08), pela tarefa.

    Mesmo molde do `cancel_from_gcal`: a conta Google de quem pede primeiro; depois o pedido (marca, PENDING
    sob trava), a tarefa e o registro numa transação só. As recusas (não é de formação, nunca foi ao Google)
    vêm do pedido, sobre a linha travada.

    Raises:
        APIError 403 `google_not_connected`, 409 `google_calendar_not_configured`: modo OAuth sem como escrever.
        ConflictError 409 `nao_e_evento_de_formacao`, `ja_cancelado_na_agenda`, `not_published`, `linha_ocupada`.
        ConflictError 409 `cancelar_na_agenda_desligado`: a chave do CON-08 B está desligada (vem antes de tudo).
    """
    from apps.core.tasks import task_cancelar_na_agenda

    _recusar_se_desligado()
    operator_user_id = _check_google_oauth(user)

    kwargs: dict[str, Any] = {}
    if getattr(settings, "GCAL_AUTH_MODE", "service_account") == "oauth":
        kwargs["operator_user_id"] = operator_user_id
    client_ip = get_client_ip(request)
    with transaction.atomic():
        pedido = pedir_operacao_gcal(solicitacao.id, "cancelar_na_agenda")
        task = enfileirar_tarefa_gcal(task_cancelar_na_agenda, solicitacao.id, **kwargs, pedido=pedido)
        AuditLog.objects.create(
            usuario=user,
            action=AuditLog.Action.CANCELAR_NA_AGENDA_REQUESTED,
            model_name="Solicitacao",
            details={
                "solicitacao_id": solicitacao.id,
                "task_id": task.id,
                "pedido": pedido,
                "external_event_id": solicitacao.external_event_id,
                "ip_address": client_ip,
            },
        )

    logger.info(
        "cancelar_na_agenda_requested",
        extra={
            "event": "cancelar_na_agenda_requested",
            "user_id": user.id,
            "solicitacao_id": solicitacao.id,
            "task_id": task.id,
            "ip_address": client_ip,
        },
    )

    return CancelResult(
        success=True,
        task_id=task.id,
        solicitacao_id=solicitacao.id,
        message="Cancelamento na agenda solicitado: o título no Google ganha (CANCELADO) em instantes.",
    )


_MSG_SINCRONIZACAO_EM_ANDAMENTO = (
    "Não é possível excluir enquanto a sincronização com o Google Calendar está em andamento. Aguarde a conclusão."
)
_MSG_GOOGLE_NAO_CONFIRMOU = (
    "O Google Agenda não confirmou a remoção do evento, e nada foi excluído: ele continua no sistema e no "
    "Google. Tente excluir de novo em alguns minutos."
)
_MSG_GOOGLE_NAO_CONFIRMOU_A_MARCA = (
    "O Google Agenda não confirmou o (CANCELADO) no título, e nada foi excluído: o evento continua no sistema e "
    "no Google. Tente excluir de novo em alguns minutos."
)
_MSG_BANCO_DEPOIS_DO_GOOGLE = (
    "O evento pode já ter saído do Google Agenda, mas o sistema não conseguiu gravar. Nada foi excluído aqui: "
    "tente excluir de novo."
)
_MSG_BANCO_DEPOIS_DA_MARCA = (
    "O título no Google Agenda pode já ter ganhado (CANCELADO), mas o sistema não conseguiu gravar. Nada foi "
    "excluído aqui: tente excluir de novo."
)


def remover_do_google_agora(solicitacao: Solicitacao, user: Usuario) -> tuple[str | None, str | None]:
    """Tira o evento do Google AGORA (síncrono), para a exclusão apagar dos dois lados.

    Mesmo caminho da task de cancelamento (`task_cancel_solicitacao_from_gcal`): no modo OAuth o
    cliente é o da conta de quem exclui; fora dele, o service account. `cancel_solicitacao` só limpa
    os campos depois que o Google confirma (404 ou 410 = já removido) e grava `gcal_status=NONE`; o
    `status` não muda. Quem chama já conferiu `can_publish_solicitacao`.

    A linha é relida com lock: PENDING (publicação ou reenvio enfileirado) recusa sem chamar o
    Google. ERROR sem id (publicação que falhou) usa o id determinístico do insert, porque o evento
    pode ter sido criado lá. O AuditLog vem antes do Google: depois dele só sobra o save da linha.

    Evento de formação com a chave do CON-08 B ligada, ou linha já cancelada na agenda (`excluir_marca_cancelado`,
    que decide a chave num lugar só; desligada, o de formação não marcado sai do Google): em vez de tirar do Google,
    marca o título com "(CANCELADO) " (`marcar_cancelado_no_google`) e grava `cancelado_na_agenda`; o evento fica
    lá, cancelado, e quem chama apaga a linha (decisão do dono, 23/11/2026). O AuditLog é `CANCELAR_NA_AGENDA`,
    gravado antes do Google e completado, no mesmo atomic, com o desfecho (`action` e `resultado`). Se o Google
    falha, o rollback desfaz a marca. Id adotado que o Google não acha (P5, decisão do dono de 24/11): na linha
    cujo Cancelar já terminou (`cancelamento_confirmado`), conclui e avisa (`nao_achado`); nas outras, inclusive a
    marcada em ERROR cujo Cancelar falhou antes do Google, recusa (o id pode estar errado).

    Returns:
        O `external_event_id` que estava (ou podia estar) no Google, e o desfecho da marca: `marcado`,
        `ja_marcado`, `ja_saiu` ou `nao_achado` (id adotado da linha já cancelada, 404 ou 410); None quando o
        evento foi tirado do Google (tipo que não é de formação).

    Raises:
        ValidationAPIError 400 `gcal_cancel_failed` com o motivo legível. Se o Google falhou, nada
        mudou. Se a gravação falhou depois do Google (raro: só o commit vem depois), o evento pode já ter
        saído de lá, ou o título já ter ganhado "(CANCELADO) ", e a linha continua como antes, publicável;
        tentar de novo resolve (404 e 410 contam como sucesso; o marcador já posto dá SKIP). Risco aceito:
        gravar a marca numa transação antes do Google deixaria a linha "Cancelado na agenda" com o título sem
        a marca sempre que o Google falha, que é o caso comum.
    """
    from django.db import DatabaseError, transaction

    from apps.core.services.gcal.sync import EventoAdotadoNaoAchado
    from apps.core.services.gcal_sync_service import (  # pyright: ignore[reportPrivateUsage]
        _event_id_for,
        cancel_solicitacao,
        marcar_cancelado_no_google,
    )
    from apps.core.tasks import (  # pyright: ignore[reportPrivateUsage]
        _MSG_CREDENCIAL_GOOGLE,
        _MSG_SEM_ACESSO_CALENDARIO,
        _friendly_gcal_error,
    )

    marca = excluir_marca_cancelado(solicitacao)
    try:
        client = None
        if _check_google_oauth(user) is not None:
            from apps.core.services.gcal_client_factory import get_oauth_client_for_user

            try:
                client, _ = get_oauth_client_for_user(user)
            except ValueError as e:
                raise ValidationAPIError(message=_MSG_CREDENCIAL_GOOGLE, code="gcal_cancel_failed") from e

        with transaction.atomic():
            s = Solicitacao.objects.select_for_update().get(pk=solicitacao.pk)
            if s.gcal_status == Solicitacao.GCalStatus.PENDING:
                raise ValidationAPIError(message=_MSG_SINCRONIZACAO_EM_ANDAMENTO, code="gcal_cancel_failed")
            if s.gcal_status == Solicitacao.GCalStatus.ERROR and not s.external_event_id:
                s.external_event_id = _event_id_for(s)
            external_event_id = s.external_event_id
            resultado: str | None = None
            marca = excluir_marca_cancelado(s)  # sobre a linha travada; o de fora do try serve aos textos de erro
            if marca:
                ja_cancelada = cancelamento_confirmado(s)  # lido antes de gravar a marca e do registro abaixo
                s.cancelado_na_agenda = True
                s.save(update_fields=["cancelado_na_agenda"])
                registro = AuditLog.objects.create(
                    usuario=user,
                    action=AuditLog.Action.CANCELAR_NA_AGENDA,
                    model_name="Solicitacao",
                    details={
                        "solicitacao_id": s.id,
                        "action": "UPDATE",
                        "external_event_id": external_event_id,
                        "origem": "exclusao",
                    },
                )
                try:
                    outcome = marcar_cancelado_no_google(s, client=client)
                    acao, resultado = outcome.action, outcome.summary
                except EventoAdotadoNaoAchado:
                    # P5 (decisão do dono, 24/11/2026): na linha cujo Cancelar já terminou o (CANCELADO) já foi
                    # para o Google; o evento sumiu de lá depois. Sem saída por outro botão, a exclusão conclui com
                    # aviso. Sem o Cancelar confirmado (linha não marcada, ou marcada em ERROR com o Cancelar que
                    # falhou antes do Google) o id pode estar errado, o evento lá com outro id: recusa, abaixo.
                    if not ja_cancelada:
                        raise
                    acao, resultado = "SKIP", "nao_achado"
                # O registro diz o que de fato aconteceu: "UPDATE" só quando o título ganhou a marca agora.
                registro.details.update(action=acao, resultado=resultado)
                registro.save(update_fields=["details"])
            else:
                AuditLog.objects.create(
                    usuario=user,
                    action=AuditLog.Action.CANCEL_GCAL,
                    model_name="Solicitacao",
                    details={
                        "solicitacao_id": s.id,
                        "action": "DELETE",
                        "external_event_id": external_event_id,
                        "origem": "exclusao",
                    },
                )
                cancel_solicitacao(s, client=client)
    except ValidationAPIError:
        raise
    except Exception as e:
        logger.warning(
            "excluir_cancel_gcal_failed",
            extra={"event": "excluir_cancel_gcal_failed", "solicitacao_id": solicitacao.pk, "error": str(e)[:500]},
        )
        if isinstance(e, DatabaseError):
            mensagem = _MSG_BANCO_DEPOIS_DA_MARCA if marca else _MSG_BANCO_DEPOIS_DO_GOOGLE
        elif isinstance(e, APIError):
            mensagem = e.message
        elif isinstance(e, ValueError) or _friendly_gcal_error(e) == _MSG_SEM_ACESSO_CALENDARIO:
            # Sem acesso ao calendário (403/404, ou a checagem do `cancel_solicitacao`): o texto diz o que fazer.
            mensagem = f"Nada foi excluído. {_friendly_gcal_error(e)}"
        else:
            # Fora de 403/404 (5xx, rede) o texto do Google é técnico: o cru fica só no log acima.
            mensagem = _MSG_GOOGLE_NAO_CONFIRMOU_A_MARCA if marca else _MSG_GOOGLE_NAO_CONFIRMOU
        raise ValidationAPIError(message=mensagem, code="gcal_cancel_failed") from e

    return external_event_id, resultado
