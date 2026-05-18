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

logger = logging.getLogger(__name__)


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


def _get_client_ip(request: Any) -> str:
    """Extract real client IP considering reverse proxies."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    x_real_ip = request.META.get("HTTP_X_REAL_IP")
    if x_real_ip:
        return x_real_ip.strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def _check_google_oauth(user: Usuario) -> int | None:
    """
    Check if user has Google OAuth credentials in OAuth mode.

    Returns:
        operator_user_id if OAuth mode and credentials exist, None otherwise

    Raises:
        ValidationAPIError: If OAuth mode and no credentials found
    """
    auth_mode = getattr(settings, "GCAL_AUTH_MODE", "service_account")

    if auth_mode != "oauth":
        return None

    try:
        GoogleOAuthCredential.objects.get(user=user)
        return user.id
    except GoogleOAuthCredential.DoesNotExist:
        raise APIError(
            code="google_not_connected",
            message="Conecte sua conta Google",
            status_code=403,
        )


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

    client_ip = _get_client_ip(request)
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
            "username": user.username,
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
    client_ip = _get_client_ip(request)
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
            "username": user.username,
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
    client_ip = _get_client_ip(request)
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
            "username": user.username,
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
    client_ip = _get_client_ip(request)
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
            "username": user.username,
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
