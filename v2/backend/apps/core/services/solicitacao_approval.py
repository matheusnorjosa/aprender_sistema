"""
Solicitacao Approval Service - §1 Epic #459

Service layer for approval/rejection operations.
Extracted from views_solicitacao.py to follow Single Responsibility Principle.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.core.exceptions import ValidationAPIError
from apps.core.models import AuditLog, Solicitacao, Usuario
from apps.core.services.db_retry import retry_on_deadlock

logger = logging.getLogger(__name__)


@dataclass
class ApprovalResult:
    """Result of an approval/rejection operation."""

    success: bool
    solicitacao: Solicitacao
    prev_status: str
    new_status: str
    message: str


@dataclass
class BatchApprovalResult:
    """Result of a batch approval/rejection operation."""

    approved_count: int
    rejected_count: int
    errors: list[dict[str, Any]]


def _get_client_ip(request: Any) -> str:
    """Extract real client IP considering reverse proxies."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    x_real_ip = request.META.get("HTTP_X_REAL_IP")
    if x_real_ip:
        return x_real_ip.strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def _raise_invalid_status_error(solicitacao: Solicitacao) -> None:
    """Raise ValidationAPIError for non-pending solicitacao status."""
    if solicitacao.status == "aprovado":
        raise ValidationAPIError(
            message="Solicitação já está aprovada.",
            code="already_approved",
        )
    if solicitacao.status == "reprovado":
        raise ValidationAPIError(
            message="Solicitação já está reprovada.",
            code="already_rejected",
        )
    raise ValidationAPIError(
        message="Solicitação não está pendente.",
        code="invalid_status",
        extra={"status": solicitacao.status},
    )


def _build_batch_status_errors(ids: list[int], found_ids: set[int]) -> list[dict[str, Any]]:
    """
    Build per-ID errors for batch actions without N+1 queries.

    Strategy:
    - Pending/locked IDs are in `found_ids` and will be processed.
    - For the remaining IDs, fetch status in a single query and emit:
      - \"Status já é 'X'\" when record exists but is not pending
      - \"Solicitação não encontrada\" when record does not exist
    """
    status_by_id: dict[int, str] = dict(Solicitacao.objects.filter(id__in=ids).values_list("id", "status"))
    errors: list[dict[str, Any]] = []

    for sol_id in ids:
        if sol_id in found_ids:
            continue

        existing_status = status_by_id.get(sol_id)
        if existing_status is None:
            errors.append({"id": sol_id, "detail": "Solicitação não encontrada"})
        else:
            errors.append({"id": sol_id, "detail": f"Status já é '{existing_status}'"})

    return errors


@retry_on_deadlock(operation="solicitacao.approve")
def approve_solicitacao(
    solicitacao: Solicitacao,
    user: Usuario,
    request: Any,
    justificativa: str = "",
) -> ApprovalResult:
    """
    Approve a single solicitacao.

    Args:
        solicitacao: The solicitacao to approve
        user: The user performing the approval
        request: The HTTP request (for IP/user-agent logging)
        justificativa: Optional justification text

    Returns:
        ApprovalResult with operation details

    Raises:
        ValidationAPIError: If solicitacao is not pending
    """
    client_ip = _get_client_ip(request)
    with transaction.atomic():
        solicitacao = Solicitacao.objects.select_for_update().get(pk=solicitacao.pk)
        if solicitacao.status != "pendente":
            _raise_invalid_status_error(solicitacao)

        prev_status = solicitacao.status
        solicitacao.status = "aprovado"
        solicitacao.save()

        # Persist AuditLog
        AuditLog.objects.create(
            usuario=user,
            action=AuditLog.Action.APPROVE,
            model_name="Solicitacao",
            details={
                "solicitacao_id": solicitacao.id,
                "prev_status": prev_status,
                "new_status": solicitacao.status,
                "justificativa": justificativa,
                "ip_address": client_ip,
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:200],
            },
        )

        logger.info(
            "solicitacao_approved",
            extra={
                "event": "solicitacao_approved",
                "user_id": user.id,
                "username": user.username,
                "solicitation_id": solicitacao.id,
                "action": "approve",
                "ip_address": client_ip,
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:200],
                "justificativa": justificativa,
                "timestamp": timezone.now().isoformat(),
            },
        )

    return ApprovalResult(
        success=True,
        solicitacao=solicitacao,
        prev_status=prev_status,
        new_status="aprovado",
        message="Solicitação aprovada com sucesso.",
    )


@retry_on_deadlock(operation="solicitacao.reject")
def reject_solicitacao(
    solicitacao: Solicitacao,
    user: Usuario,
    request: Any,
    justificativa: str = "",
) -> ApprovalResult:
    """
    Reject a single solicitacao.

    Args:
        solicitacao: The solicitacao to reject
        user: The user performing the rejection
        request: The HTTP request (for IP/user-agent logging)
        justificativa: Optional justification text

    Returns:
        ApprovalResult with operation details

    Raises:
        ValidationAPIError: If solicitacao is not pending
    """
    client_ip = _get_client_ip(request)
    with transaction.atomic():
        solicitacao = Solicitacao.objects.select_for_update().get(pk=solicitacao.pk)
        if solicitacao.status != "pendente":
            _raise_invalid_status_error(solicitacao)

        prev_status = solicitacao.status
        solicitacao.status = "reprovado"
        solicitacao.save()

        # Persist AuditLog
        AuditLog.objects.create(
            usuario=user,
            action=AuditLog.Action.REJECT,
            model_name="Solicitacao",
            details={
                "solicitacao_id": solicitacao.id,
                "prev_status": prev_status,
                "new_status": solicitacao.status,
                "justificativa": justificativa,
                "ip_address": client_ip,
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:200],
            },
        )

        logger.info(
            "solicitacao_rejected",
            extra={
                "event": "solicitacao_rejected",
                "user_id": user.id,
                "username": user.username,
                "solicitation_id": solicitacao.id,
                "action": "reject",
                "ip_address": client_ip,
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:200],
                "justificativa": justificativa,
                "timestamp": timezone.now().isoformat(),
            },
        )

    return ApprovalResult(
        success=True,
        solicitacao=solicitacao,
        prev_status=prev_status,
        new_status="reprovado",
        message="Solicitação reprovada.",
    )


@retry_on_deadlock(operation="solicitacao.batch_approve")
def batch_approve_solicitacoes(
    ids: list[int],
    user: Usuario,
    request: Any,
) -> BatchApprovalResult:
    """
    Approve multiple solicitacoes in batch.

    Args:
        ids: List of solicitacao IDs to approve
        user: The user performing the approval
        request: The HTTP request (for IP/user-agent logging)

    Returns:
        BatchApprovalResult with counts and errors

    Raises:
        ValidationAPIError: If ids is empty or exceeds limit
    """
    if not ids:
        raise ValidationAPIError(
            message="O campo 'ids' é obrigatório.",
            code="ids_required",
        )

    if len(ids) > 100:
        raise ValidationAPIError(
            message="Máximo 100 solicitações por vez.",
            code="batch_limit_exceeded",
        )

    approved = 0
    errors: list[dict[str, Any]] = []
    client_ip = _get_client_ip(request)

    with transaction.atomic():
        # Fetch and lock pending solicitacoes to avoid double-approval races
        solicitacoes = list(
            Solicitacao.objects.filter(id__in=ids, status="pendente").select_for_update(skip_locked=True).order_by("id")
        )
        found_ids = {sol.id for sol in solicitacoes}

        errors.extend(_build_batch_status_errors(ids, found_ids))

        # Approve in batch
        for sol in solicitacoes:
            prev_status = sol.status
            sol.status = "aprovado"
            sol.save()

            # PA-05: Individual AuditLog with batch=true
            AuditLog.objects.create(
                usuario=user,
                action=AuditLog.Action.APPROVE,
                model_name="Solicitacao",
                details={
                    "solicitacao_id": sol.id,
                    "prev_status": prev_status,
                    "new_status": "aprovado",
                    "batch": True,
                    "ip_address": client_ip,
                    "user_agent": request.META.get("HTTP_USER_AGENT", "")[:200],
                },
            )

            logger.info(
                "solicitacao_batch_approved",
                extra={
                    "event": "solicitacao_batch_approved",
                    "user_id": user.id,
                    "username": user.username,
                    "solicitacao_id": sol.id,
                    "batch": True,
                    "ip_address": client_ip,
                    "timestamp": timezone.now().isoformat(),
                },
            )

            approved += 1

    return BatchApprovalResult(
        approved_count=approved,
        rejected_count=0,
        errors=errors,
    )


@retry_on_deadlock(operation="solicitacao.batch_reject")
def batch_reject_solicitacoes(
    ids: list[int],
    user: Usuario,
    request: Any,
) -> BatchApprovalResult:
    """
    Reject multiple solicitacoes in batch.

    Args:
        ids: List of solicitacao IDs to reject
        user: The user performing the rejection
        request: The HTTP request (for IP/user-agent logging)

    Returns:
        BatchApprovalResult with counts and errors

    Raises:
        ValidationAPIError: If ids is empty or exceeds limit
    """
    if not ids:
        raise ValidationAPIError(
            message="O campo 'ids' é obrigatório.",
            code="ids_required",
        )

    if len(ids) > 100:
        raise ValidationAPIError(
            message="Máximo 100 solicitações por vez.",
            code="batch_limit_exceeded",
        )

    rejected = 0
    errors: list[dict[str, Any]] = []
    client_ip = _get_client_ip(request)

    with transaction.atomic():
        # Fetch and lock pending solicitacoes to avoid double-reject races
        solicitacoes = list(
            Solicitacao.objects.filter(id__in=ids, status="pendente").select_for_update(skip_locked=True).order_by("id")
        )
        found_ids = {sol.id for sol in solicitacoes}

        errors.extend(_build_batch_status_errors(ids, found_ids))

        # Reject in batch
        for sol in solicitacoes:
            prev_status = sol.status
            sol.status = "reprovado"
            sol.save()

            # PA-05: Individual AuditLog with batch=true
            AuditLog.objects.create(
                usuario=user,
                action=AuditLog.Action.REJECT,
                model_name="Solicitacao",
                details={
                    "solicitacao_id": sol.id,
                    "prev_status": prev_status,
                    "new_status": "reprovado",
                    "batch": True,
                    "ip_address": client_ip,
                    "user_agent": request.META.get("HTTP_USER_AGENT", "")[:200],
                },
            )

            logger.info(
                "solicitacao_batch_rejected",
                extra={
                    "event": "solicitacao_batch_rejected",
                    "user_id": user.id,
                    "username": user.username,
                    "solicitacao_id": sol.id,
                    "batch": True,
                    "ip_address": client_ip,
                    "timestamp": timezone.now().isoformat(),
                },
            )

            rejected += 1

    return BatchApprovalResult(
        approved_count=0,
        rejected_count=rejected,
        errors=errors,
    )
