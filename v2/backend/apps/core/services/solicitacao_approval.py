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

from django.utils import timezone

from apps.core.exceptions import ValidationAPIError
from apps.core.models import AuditLog, Solicitacao, Usuario

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
        ValidationAPIError: If solicitacao is already approved
    """
    if solicitacao.status == "aprovado":
        raise ValidationAPIError(
            message="Solicitação já está aprovada.",
            code="already_approved",
        )

    prev_status = solicitacao.status
    solicitacao.status = "aprovado"
    solicitacao.save()

    client_ip = _get_client_ip(request)

    # Persist AuditLog
    AuditLog.objects.create(
        usuario=user,
        action="APPROVE",
        model_name="Solicitacao",
        details={
            "solicitacao_id": solicitacao.id,
            "prev_status": prev_status,
            "new_status": solicitacao.status,
            "ip_address": client_ip,
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
        ValidationAPIError: If solicitacao is already rejected
    """
    if solicitacao.status == "reprovado":
        raise ValidationAPIError(
            message="Solicitação já está reprovada.",
            code="already_rejected",
        )

    prev_status = solicitacao.status
    solicitacao.status = "reprovado"
    solicitacao.save()

    client_ip = _get_client_ip(request)

    # Persist AuditLog
    AuditLog.objects.create(
        usuario=user,
        action="REJECT",
        model_name="Solicitacao",
        details={
            "solicitacao_id": solicitacao.id,
            "prev_status": prev_status,
            "new_status": solicitacao.status,
            "justificativa": justificativa,
            "ip_address": client_ip,
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

    # Fetch pending solicitacoes
    solicitacoes = Solicitacao.objects.filter(id__in=ids, status="pendente")
    found_ids = set(solicitacoes.values_list("id", flat=True))

    # Record errors for not found or already processed IDs
    for sol_id in ids:
        if sol_id not in found_ids:
            sol = Solicitacao.objects.filter(id=sol_id).first()
            if sol:
                errors.append({"id": sol_id, "detail": f"Status já é '{sol.status}'"})
            else:
                errors.append({"id": sol_id, "detail": "Solicitação não encontrada"})

    # Approve in batch
    for sol in solicitacoes:
        prev_status = sol.status
        sol.status = "aprovado"
        sol.save()

        # PA-05: Individual AuditLog with batch=true
        AuditLog.objects.create(
            usuario=user,
            action="APPROVE",
            model_name="Solicitacao",
            details={
                "solicitacao_id": sol.id,
                "prev_status": prev_status,
                "new_status": "aprovado",
                "batch": True,
                "ip_address": client_ip,
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

    # Fetch pending solicitacoes
    solicitacoes = Solicitacao.objects.filter(id__in=ids, status="pendente")
    found_ids = set(solicitacoes.values_list("id", flat=True))

    # Record errors for not found or already processed IDs
    for sol_id in ids:
        if sol_id not in found_ids:
            sol = Solicitacao.objects.filter(id=sol_id).first()
            if sol:
                errors.append({"id": sol_id, "detail": f"Status já é '{sol.status}'"})
            else:
                errors.append({"id": sol_id, "detail": "Solicitação não encontrada"})

    # Reject in batch
    for sol in solicitacoes:
        prev_status = sol.status
        sol.status = "reprovado"
        sol.save()

        # PA-05: Individual AuditLog with batch=true
        AuditLog.objects.create(
            usuario=user,
            action="REJECT",
            model_name="Solicitacao",
            details={
                "solicitacao_id": sol.id,
                "prev_status": prev_status,
                "new_status": "reprovado",
                "batch": True,
                "ip_address": client_ip,
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
