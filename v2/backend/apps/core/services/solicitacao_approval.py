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

from apps.core.exceptions import APIError, ValidationAPIError
from apps.core.models import AuditLog, Participation, Solicitacao, Usuario
from apps.core.rbac.policies import (
    ESCOPO_SUPERINTENDENCIA_Q,
    solicitation_approval_basis,
    solicitation_approval_basis_for,
)
from apps.core.services.db_retry import retry_on_deadlock
from apps.core.services.solicitacao_availability import enforce_solicitacao_availability
from apps.core.utils.cache_utils import invalidate_availability_cache
from apps.core.utils.net import get_client_ip

logger = logging.getLogger(__name__)


def _invalidate_participants_availability_cache(solicitacao: Solicitacao) -> None:
    """
    Decisão do dono (2026-09-14): ao APROVAR, o evento passa a OCUPAR a agenda dos
    participantes (`check_conflicts` conta evento aprovado via Participation com role
    ocupante — RD-07). O signal de Solicitacao só bumpa o cache do CRIADOR
    (`instance.usuario_id`); os demais participantes ficariam com `avail_ver`/
    `monthly_ver` obsoletos — um preview cacheado diria "livre" para quem acabou de
    ser alocado. Bump explícito aqui (o #1556 só cobre a MUDANÇA de Participation,
    não a mudança de status). Convidados externos (`usuario_id=None`) não têm
    disponibilidade — são naturalmente excluídos pelo filtro.
    """
    participantes_ids = (
        Participation.objects.filter(solicitacao=solicitacao, usuario_id__isnull=False)
        .values_list("usuario_id", flat=True)
        .distinct()
    )
    for usuario_id in participantes_ids:
        invalidate_availability_cache(usuario_id=usuario_id)


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


SELF_APPROVAL_CODE = "self_approval_forbidden"


def _mensagem_decisao_propria(acao: str) -> str:
    return f"Você não pode {acao} a própria solicitação. Outra pessoa aprovadora precisa decidir."


def _decisao_propria_bloqueada(solicitacao: Solicitacao, user: Usuario) -> bool:
    """PA-02 (segregação, PR B1): quem criou (`Solicitacao.usuario`) não decide a própria.

    Superuser pode (break-glass) — a decisão fica marcada com `details.autoaprovacao`.
    Loga o bloqueio sem username (username é o CPF em produção).
    """
    if solicitacao.usuario_id != user.pk or user.is_superuser:
        return False
    logger.warning(
        "solicitacao_self_decision_blocked",
        extra={
            "event": "solicitacao_self_decision_blocked",
            "user_id": user.pk,
            "solicitacao_id": solicitacao.pk,
        },
    )
    return True


def _bloquear_decisao_propria(solicitacao: Solicitacao, user: Usuario, acao: str) -> None:
    """Decisão individual: levanta 403 `self_approval_forbidden` se a solicitação é do ator."""
    if _decisao_propria_bloqueada(solicitacao, user):
        raise APIError(
            code=SELF_APPROVAL_CODE,
            message=_mensagem_decisao_propria(acao),
            status_code=403,
        )


OUT_OF_SCOPE_CODE = "out_of_approval_scope"


def _mensagem_fora_do_escopo(acao: str) -> str:
    return f"Você só pode {acao} solicitações do fluxo SUPER da Superintendência."


def _log_fora_do_escopo(solicitacao: Solicitacao, user: Usuario) -> None:
    """Loga o bloqueio de escopo sem username (username é o CPF em produção)."""
    logger.warning(
        "solicitacao_out_of_scope_blocked",
        extra={
            "event": "solicitacao_out_of_scope_blocked",
            "user_id": user.pk,
            "solicitacao_id": solicitacao.pk,
        },
    )


def _autoridade_no_escopo(solicitacao: Solicitacao, user: Usuario, acao: str) -> str | None:
    """Regra do dono (30/09): base da autoridade para ESTA solicitação; fora do escopo → 403.

    A aprovadora por vínculo (GERENTE em g1) só decide projeto do fluxo SUPER da Superintendência.
    Quem chama sem base nenhuma (serviço interno, sem ator aprovador) continua confiando na view.
    """
    autoridade = solicitation_approval_basis_for(user, solicitacao)
    if autoridade is None and solicitation_approval_basis(user) is not None:
        _log_fora_do_escopo(solicitacao, user)
        raise APIError(code=OUT_OF_SCOPE_CODE, message=_mensagem_fora_do_escopo(acao), status_code=403)
    return autoridade


def _autoridades_do_lote(user: Usuario, ids: set[int]) -> tuple[str | None, str | None, set[int]]:
    """Lote: (autoridade no escopo, autoridade fora do escopo, ids no escopo) sem query por item.

    Só a aprovadora por vínculo tem as duas autoridades diferentes; para ela, 1 query separa os ids
    do escopo (sem `select_related` no `select_for_update`: FK nula dá NotSupportedError no Postgres).
    """
    autoridade = solicitation_approval_basis(user)
    if autoridade != "gerente_superintendencia":
        return autoridade, autoridade, set()
    fora = solicitation_approval_basis_for(user, None)
    no_escopo = set(
        Solicitacao.objects.filter(id__in=ids).filter(ESCOPO_SUPERINTENDENCIA_Q).values_list("id", flat=True)
    )
    return autoridade, fora, no_escopo


def _decision_details(solicitacao: Solicitacao, user: Usuario, autoridade: str | None) -> dict[str, Any]:
    """Autoria comum a todo AuditLog de decisão (PR B1): base da autoridade + autoaprovação."""
    details: dict[str, Any] = {"autoridade": autoridade}
    if solicitacao.usuario_id == user.pk:
        details["autoaprovacao"] = True
    return details


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
        ValidationAPIError: If solicitacao is not pending, or if any participant has a
            conflict (#1452)
    """
    client_ip = get_client_ip(request)
    with transaction.atomic():
        solicitacao = Solicitacao.objects.select_for_update().get(pk=solicitacao.pk)
        _bloquear_decisao_propria(solicitacao, user, "aprovar")
        autoridade = _autoridade_no_escopo(solicitacao, user, "aprovar")
        if solicitacao.status != "pendente":
            _raise_invalid_status_error(solicitacao)

        # #1452: aprovar é o momento em que o evento passa a ocupar a agenda, e pode ter
        # ficado pendente por dias. Revalidar aqui — o `select_for_update` acima tranca só
        # esta linha, então quem garante exclusão entre solicitações distintas do mesmo
        # formador é o advisory lock por participante dentro do guard.
        enforce_solicitacao_availability(solicitacao, action="approve")

        prev_status = solicitacao.status
        solicitacao.status = "aprovado"
        solicitacao.save()

        # #GAP-5: aprovar torna o evento ocupante — invalida o cache consultivo dos
        # participantes (o signal de Solicitacao só bumpa o criador).
        _invalidate_participants_availability_cache(solicitacao)

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
                **_decision_details(solicitacao, user, autoridade),
            },
        )

        logger.info(
            "solicitacao_approved",
            extra={
                "event": "solicitacao_approved",
                "user_id": user.id,
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
    client_ip = get_client_ip(request)
    with transaction.atomic():
        solicitacao = Solicitacao.objects.select_for_update().get(pk=solicitacao.pk)
        _bloquear_decisao_propria(solicitacao, user, "reprovar")
        autoridade = _autoridade_no_escopo(solicitacao, user, "reprovar")
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
                **_decision_details(solicitacao, user, autoridade),
            },
        )

        logger.info(
            "solicitacao_rejected",
            extra={
                "event": "solicitacao_rejected",
                "user_id": user.id,
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
    client_ip = get_client_ip(request)

    with transaction.atomic():
        # Fetch and lock pending solicitacoes to avoid double-approval races
        solicitacoes = list(
            Solicitacao.objects.filter(id__in=ids, status="pendente").select_for_update(skip_locked=True).order_by("id")
        )
        found_ids = {sol.id for sol in solicitacoes}
        autoridade_global, autoridade_fora, no_escopo = _autoridades_do_lote(user, found_ids)

        errors.extend(_build_batch_status_errors(ids, found_ids))

        # Approve in batch
        for sol in solicitacoes:
            # PA-02 (segregação, PR B1): item próprio vai para errors[]; o resto do lote segue.
            if _decisao_propria_bloqueada(sol, user):
                errors.append(
                    {"id": sol.id, "code": SELF_APPROVAL_CODE, "detail": _mensagem_decisao_propria("aprovar")}
                )
                continue

            # Regra do dono (30/09): fora do escopo da aprovadora por vínculo vai para errors[].
            autoridade = autoridade_global if sol.id in no_escopo else autoridade_fora
            if autoridade is None and autoridade_global is not None:
                _log_fora_do_escopo(sol, user)
                errors.append({"id": sol.id, "code": OUT_OF_SCOPE_CODE, "detail": _mensagem_fora_do_escopo("aprovar")})
                continue

            # #1452: cada solicitação é revalidada imediatamente antes de ser aprovada.
            # Como aprovamos em sequência dentro da mesma transação, a checagem da
            # próxima já enxerga as anteriores como aprovadas — é isso que impede um
            # lote de aprovar dois eventos conflitantes do mesmo formador de uma vez.
            # Conflito reprova só aquele item; o resto do lote segue.
            try:
                enforce_solicitacao_availability(sol, action="batch_approve")
            except ValidationAPIError as exc:
                errors.append({"id": sol.id, "detail": exc.message})
                continue

            prev_status = sol.status
            sol.status = "aprovado"
            sol.save()

            # #GAP-5: idem approve single — invalida cache consultivo dos participantes.
            _invalidate_participants_availability_cache(sol)

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
                    **_decision_details(sol, user, autoridade),
                },
            )

            logger.info(
                "solicitacao_batch_approved",
                extra={
                    "event": "solicitacao_batch_approved",
                    "user_id": user.id,
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
    client_ip = get_client_ip(request)

    with transaction.atomic():
        # Fetch and lock pending solicitacoes to avoid double-reject races
        solicitacoes = list(
            Solicitacao.objects.filter(id__in=ids, status="pendente").select_for_update(skip_locked=True).order_by("id")
        )
        found_ids = {sol.id for sol in solicitacoes}
        autoridade_global, autoridade_fora, no_escopo = _autoridades_do_lote(user, found_ids)

        errors.extend(_build_batch_status_errors(ids, found_ids))

        # Reject in batch
        for sol in solicitacoes:
            # PA-02 (segregação, PR B1): item próprio vai para errors[]; o resto do lote segue.
            if _decisao_propria_bloqueada(sol, user):
                errors.append(
                    {"id": sol.id, "code": SELF_APPROVAL_CODE, "detail": _mensagem_decisao_propria("reprovar")}
                )
                continue

            # Regra do dono (30/09): fora do escopo da aprovadora por vínculo vai para errors[].
            autoridade = autoridade_global if sol.id in no_escopo else autoridade_fora
            if autoridade is None and autoridade_global is not None:
                _log_fora_do_escopo(sol, user)
                errors.append({"id": sol.id, "code": OUT_OF_SCOPE_CODE, "detail": _mensagem_fora_do_escopo("reprovar")})
                continue

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
                    **_decision_details(sol, user, autoridade),
                },
            )

            logger.info(
                "solicitacao_batch_rejected",
                extra={
                    "event": "solicitacao_batch_rejected",
                    "user_id": user.id,
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
