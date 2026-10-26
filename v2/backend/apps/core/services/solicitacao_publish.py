"""
Solicitacao Publish Service - §1 Epic #459

Service layer for Google Calendar publish/resync/cancel operations.
Extracted from views_solicitacao.py to follow Single Responsibility Principle.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportFunctionMemberAccess=false, reportCallIssue=false

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.utils import timezone

from apps.core.exceptions import APIError, ConflictError, ValidationAPIError
from apps.core.models import AuditLog, GoogleOAuthCredential, Solicitacao, Usuario
from apps.core.utils.net import get_client_ip

logger = logging.getLogger(__name__)

# Por que o evento não pode ir ao Google agora (virada, 16/10/2026). Mensagem para a tela e o lote.
MENSAGENS_NAO_PUBLICAVEL: dict[str, str] = {
    "publicado_fora_do_sistema": (
        "Este evento já está no Google Agenda pela planilha e o sistema não o adotou: publicar criaria um "
        "segundo evento. Ajuste no Google, ou peça a adoção."
    ),
    "evento_passado": "Este evento já terminou: o sistema não publica nem reenvia evento passado.",
    "ja_publicado": "Este evento já foi publicado (ou está sendo). Use Atualizar no Google.",
    "nao_publicado": "Este evento ainda não foi publicado: use Publicar, não Reaplicar nem Reenviar.",
}


def motivo_nao_publicavel(s: Solicitacao, *, reenvio: bool = False) -> str | None:
    """Código do motivo para recusar Publicar (`reenvio=False`) ou Reapply/Resync (`reenvio=True`),
    ou None se pode. Vem antes de enfileirar; a guarda final do CREATE fica no `upsert_one`.

    Publicar: recusa o já publicado (PUBLISHED ou PENDING; ERROR pode tentar de novo). Reenvio: recusa o
    que nunca foi ao Google (`NONE`), porque nele o sync cria. Os dois recusam o evento que já terminou e
    o que está no Google pela planilha sem adoção (`publicado_fora_do_sistema`)."""
    if s.publicado_fora_do_sistema:
        return "publicado_fora_do_sistema"
    if s.fim < timezone.now():
        return "evento_passado"
    if reenvio:
        if s.gcal_status == Solicitacao.GCalStatus.NONE:
            return "nao_publicado"
    elif s.gcal_status in (Solicitacao.GCalStatus.PUBLISHED, Solicitacao.GCalStatus.PENDING):
        return "ja_publicado"
    return None


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

    # Mark as PENDING before enqueueing (if not dry-run)
    if not dry_run:
        solicitacao.mark_gcal(
            status=Solicitacao.GCalStatus.PENDING,
            payload_hash=None,
            error="",
        )

    # Dispatch Celery task
    auth_mode = getattr(settings, "GCAL_AUTH_MODE", "service_account")
    if auth_mode == "oauth":
        task = task_publish_solicitacao_to_gcal.delay(
            solicitacao.id,
            dry_run=dry_run,
            apply_blocked=apply_blocked,
            operator_user_id=operator_user_id,
        )
    else:
        task = task_publish_solicitacao_to_gcal.delay(
            solicitacao.id,
            dry_run=dry_run,
            apply_blocked=apply_blocked,
        )

    # AuditLog
    client_ip = get_client_ip(request)
    AuditLog.objects.create(
        usuario=user,
        action=AuditLog.Action.PUBLISH_GCAL_REQUESTED,
        model_name="Solicitacao",
        details={
            "solicitacao_id": solicitacao.id,
            "task_id": task.id,
            "dry_run": dry_run,
            "apply_blocked": apply_blocked,
            "ip_address": client_ip,
        },
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
        ValidationAPIError: If not approved or OAuth missing
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

    # Mark as PENDING (will be republished)
    solicitacao.mark_gcal(
        status=Solicitacao.GCalStatus.PENDING,
        payload_hash=None,  # Reset hash to force UPDATE
        error="",
    )

    # Dispatch Celery task
    auth_mode = getattr(settings, "GCAL_AUTH_MODE", "service_account")
    if auth_mode == "oauth":
        task = task_publish_solicitacao_to_gcal.delay(
            solicitacao.id,
            dry_run=False,
            apply_blocked=False,
            operator_user_id=operator_user_id,
        )
    else:
        task = task_publish_solicitacao_to_gcal.delay(
            solicitacao.id,
            dry_run=False,
            apply_blocked=False,
        )

    # AuditLog
    client_ip = get_client_ip(request)
    AuditLog.objects.create(
        usuario=user,
        action=AuditLog.Action.RESYNC_GCAL_REQUESTED,
        model_name="Solicitacao",
        details={
            "solicitacao_id": solicitacao.id,
            "task_id": task.id,
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

    # Mark as PENDING temporarily (task will change to NONE after delete)
    solicitacao.mark_gcal(
        status=Solicitacao.GCalStatus.PENDING,
        payload_hash=solicitacao.gcal_payload_hash,  # Keep hash during cancellation
        error="",
    )

    # Dispatch Celery task (pass operator_user_id for OAuth mode)
    auth_mode = getattr(settings, "GCAL_AUTH_MODE", "service_account")
    if auth_mode == "oauth":
        task = task_cancel_solicitacao_from_gcal.delay(
            solicitacao.id,
            operator_user_id=operator_user_id,
        )
    else:
        task = task_cancel_solicitacao_from_gcal.delay(solicitacao.id)

    # AuditLog
    client_ip = get_client_ip(request)
    AuditLog.objects.create(
        usuario=user,
        action=AuditLog.Action.CANCEL_GCAL_REQUESTED,
        model_name="Solicitacao",
        details={
            "solicitacao_id": solicitacao.id,
            "task_id": task.id,
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


_MSG_SINCRONIZACAO_EM_ANDAMENTO = (
    "Não é possível excluir enquanto a sincronização com o Google Calendar está em andamento. Aguarde a conclusão."
)
_MSG_GOOGLE_NAO_CONFIRMOU = (
    "O Google Agenda não confirmou a remoção do evento, e nada foi excluído: ele continua no sistema e no "
    "Google. Tente excluir de novo em alguns minutos."
)


def remover_do_google_agora(solicitacao: Solicitacao, user: Usuario) -> str | None:
    """Tira o evento do Google AGORA (síncrono), para a exclusão apagar dos dois lados.

    Mesmo caminho da task de cancelamento (`task_cancel_solicitacao_from_gcal`): no modo OAuth o
    cliente é o da conta de quem exclui; fora dele, o service account. `cancel_solicitacao` só limpa
    os campos depois que o Google confirma (404 = já removido) e grava `gcal_status=NONE`; o
    `status` não muda. Quem chama já conferiu `can_publish_solicitacao`.

    A linha é relida com lock: PENDING (publicação ou reenvio enfileirado) recusa sem chamar o
    Google. ERROR sem id (publicação que falhou) usa o id determinístico do insert, porque o evento
    pode ter sido criado lá. O AuditLog vem antes do Google: depois dele só sobra o save da linha.

    Returns:
        O `external_event_id` que estava (ou podia estar) no Google.

    Raises:
        ValidationAPIError 400 `gcal_cancel_failed` com o motivo legível. Se o Google falhou, nada
        mudou. Se a gravação falhou depois do Google (raro), o evento pode já ter saído de lá e a
        linha continua como antes; tentar de novo resolve (404 conta como sucesso).
    """
    from django.db import DatabaseError, transaction

    from apps.core.services.gcal_sync_service import (  # pyright: ignore[reportPrivateUsage]
        _event_id_for,
        cancel_solicitacao,
    )
    from apps.core.tasks import (  # pyright: ignore[reportPrivateUsage]
        _MSG_CREDENCIAL_GOOGLE,
        _MSG_SEM_ACESSO_CALENDARIO,
        _friendly_gcal_error,
    )

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
            mensagem = (
                "O evento pode já ter saído do Google Agenda, mas o sistema não conseguiu gravar. "
                "Nada foi excluído aqui: tente excluir de novo."
            )
        elif isinstance(e, APIError):
            mensagem = e.message
        elif isinstance(e, ValueError) or _friendly_gcal_error(e) == _MSG_SEM_ACESSO_CALENDARIO:
            # Sem acesso ao calendário (403/404, ou a checagem do `cancel_solicitacao`): o texto diz o que fazer.
            mensagem = f"Nada foi excluído. {_friendly_gcal_error(e)}"
        else:
            # Fora de 403/404 (5xx, rede) o texto do Google é técnico: o cru fica só no log acima.
            mensagem = _MSG_GOOGLE_NAO_CONFIRMOU
        raise ValidationAPIError(message=mensagem, code="gcal_cancel_failed") from e

    return external_event_id
