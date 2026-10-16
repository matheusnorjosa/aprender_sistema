"""
Solicitacao Approval Service - §1 Epic #459

Service layer for approval/rejection operations.
Extracted from views_solicitacao.py to follow Single Responsibility Principle.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from django.db import transaction
from django.db.models import CharField, Exists, Max, OuterRef, Q, QuerySet
from django.db.models.fields.json import KeyTextTransform
from django.db.models.functions import Cast
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
ALTERED_ACCOUNT_CODE = "altered_account_approval_forbidden"
ALTERED_BY_AUTHOR_CODE = "approver_account_altered_by_author_forbidden"
EDITED_BY_APPROVER_CODE = "edited_by_approver_forbidden"

# PA-02, segregação por histórico (D2, PR 10; decisão do dono de 16/10: qualquer alteração pela tela
# de Usuários conta, inclusive corrigir o nome e criar a conta). Filtro: `model_name="Usuario"`, ator =
# `AuditLog.usuario`, alvo = `details.target_user_id`. `DELEGATE_BLOCK_*` também tem alvo, mas não é conta.
ACOES_QUE_ALTERAM_CONTA: frozenset[str] = frozenset(
    {
        AuditLog.Action.CREATE,
        AuditLog.Action.UPDATE,
        AuditLog.Action.RESET_PASSWORD,
        AuditLog.Action.USER_PRIVILEGE_CHANGED,
        AuditLog.Action.ASSIGN_GROUPS,
        AuditLog.Action.USER_ANONYMIZE,
    }
)
JANELA_SEGREGACAO = timedelta(days=30)

# PA-02, quem editou não decide (PR 10): chave de `changed_fields` no AuditLog `UPDATE` da solicitação
# → campo material do adendo da PA-04 (`views_solicitacao._campos_materiais`). Paridade por teste.
CAMPOS_MATERIAIS_NO_AUDITLOG: dict[str, str] = {
    "projeto_id": "projeto",
    "municipio_id": "municipio",
    "inicio": "inicio",
    "fim": "fim",
    "formador_ids": "formadores",
}

# Código do impedimento → valor de `decisao_impedida` na lista (tela de Aprovações).
DECISAO_IMPEDIDA: dict[str, str] = {
    SELF_APPROVAL_CODE: "propria",
    ALTERED_ACCOUNT_CODE: "conta_alterada",
    ALTERED_BY_AUTHOR_CODE: "conta_alterada_pelo_autor",
    EDITED_BY_APPROVER_CODE: "editada_pelo_ator",
}


def mensagem_impedida(code: str, acao: str) -> str:
    """Mensagem do 403 (e do item em `errors[]` no lote) para cada impedimento."""
    if code == SELF_APPROVAL_CODE:
        return f"Você não pode {acao} a própria solicitação. Outra pessoa aprovadora precisa decidir."
    if code == ALTERED_ACCOUNT_CODE:
        return (
            "Você alterou a conta de quem pediu esta solicitação nos últimos 30 dias. "
            "Outra pessoa aprovadora precisa decidir."
        )
    if code == ALTERED_BY_AUTHOR_CODE:
        return (
            "Quem pediu esta solicitação alterou a sua conta nos últimos 30 dias. "
            "Outra pessoa aprovadora precisa decidir."
        )
    return (
        "Você mudou data, horário, município, projeto ou formadores desta solicitação. "
        "Outra pessoa aprovadora precisa decidir."
    )


def contas_alteradas_por(user: Usuario) -> dict[int, datetime]:
    """D2: {id da conta: última vez que `user` a alterou} (uma consulta; índice `usuario, created_at`)."""
    if not getattr(user, "pk", None):
        return {}
    linhas = (
        AuditLog.objects.filter(usuario_id=user.pk, model_name="Usuario", action__in=ACOES_QUE_ALTERAM_CONTA)
        .order_by()
        .values("details__target_user_id")
        .annotate(ultima=Max("created_at"))
    )
    return {
        int(linha["details__target_user_id"]): linha["ultima"]
        for linha in linhas
        if isinstance(linha["details__target_user_id"], int)
    }


def quem_alterou_a_conta_de(user: Usuario, desde: datetime) -> dict[int, datetime]:
    """{id de quem alterou a conta de `user` desde `desde`: última vez} (uma consulta).

    Serve à D2 ao contrário (o autor redefine a senha de uma aprovadora e decide pela conta dela) e ao
    fantoche ao contrário de "quem editou não decide" (quem editou faz o mesmo).
    """
    if not getattr(user, "pk", None):
        return {}
    return dict(
        AuditLog.objects.filter(
            model_name="Usuario",
            action__in=ACOES_QUE_ALTERAM_CONTA,
            details__target_user_id=user.pk,
            created_at__gte=desde,
        )
        .exclude(usuario_id=None)
        .order_by()
        .values("usuario_id")
        .annotate(ultima=Max("created_at"))
        .values_list("usuario_id", "ultima")
    )


def _corte(criada_em: datetime | None, agora: datetime) -> datetime:
    """Decisão 6(b) do dono: a janela conta da decisão ou da criação do evento, o que vier antes."""
    return min(agora, criada_em or agora) - JANELA_SEGREGACAO


def _ultima_aprovacao(ids: list[int]) -> dict[int, datetime]:
    """{id: último AuditLog APPROVE} (uma consulta)."""
    ultima: dict[int, datetime] = {}
    for sol_id, quando in (
        AuditLog.objects.filter(
            model_name="Solicitacao",
            action=AuditLog.Action.APPROVE,
            details__solicitacao_id__in=ids,
        )
        .order_by()
        .values_list("details__solicitacao_id", "created_at")
    ):
        if sol_id not in ultima or quando > ultima[sol_id]:
            ultima[sol_id] = quando
    return ultima


def _editadas_pelo_ator(
    user: Usuario,
    cortes: dict[int, datetime],
    alteradas: dict[int, datetime],
    alteraram_a_minha: dict[int, datetime],
) -> set[int]:
    """Quem editou não decide: ids de `cortes` em que um editor ligado a `user` mudou campo material
    depois do último APPROVE, ou desde a criação. Até 2 consultas.

    O editor é `user`, uma conta que ele alterou nos 30 dias anteriores à edição (o fantoche: só conta
    a alteração em [edição − 30 dias, edição]; a feita depois não faz a edição virar do ator), ou quem
    alterou a conta de `user` desde o corte da solicitação (o fantoche ao contrário: o editor redefine
    a senha da aprovadora e decide pela conta dela).
    """
    fantoche = AuditLog.objects.alias(alvo=KeyTextTransform("target_user_id", "details")).filter(
        usuario_id=user.pk,
        model_name="Usuario",
        action__in=ACOES_QUE_ALTERAM_CONTA,
        alvo=Cast(OuterRef("usuario_id"), CharField()),
        created_at__gte=OuterRef("created_at") - JANELA_SEGREGACAO,
        created_at__lte=OuterRef("created_at"),
    )
    edicoes = (
        AuditLog.objects.filter(
            model_name="Solicitacao",
            action=AuditLog.Action.UPDATE,
            usuario_id__in={user.pk, *alteradas, *alteraram_a_minha},
            details__changed_fields__has_any_keys=list(CAMPOS_MATERIAIS_NO_AUDITLOG),
        )
        .annotate(eh_fantoche=Exists(fantoche))
        .filter(Q(usuario_id=user.pk) | Q(eh_fantoche=True) | Q(usuario_id__in=list(alteraram_a_minha)))
        .order_by()
        .values_list("details__solicitacao_id", "created_at", "usuario_id", "eh_fantoche")
    )
    candidatas: dict[int, datetime] = {}
    for sol_id, quando, editor_id, eh_fantoche in edicoes:
        if sol_id not in cortes:
            continue
        if editor_id != user.pk and not eh_fantoche:
            alterou_a_minha = alteraram_a_minha.get(editor_id)
            if alterou_a_minha is None or alterou_a_minha < cortes[sol_id]:
                continue
        if sol_id not in candidatas or quando > candidatas[sol_id]:
            candidatas[sol_id] = quando
    if not candidatas:
        return set()
    ultima = _ultima_aprovacao(list(candidatas))
    return {sol_id for sol_id, quando in candidatas.items() if sol_id not in ultima or quando > ultima[sol_id]}


def impedimentos(user: Usuario, solicitacoes: QuerySet[Solicitacao]) -> dict[int, str]:
    """PA-02 (segregação): {id: código} das solicitações de `solicitacoes` que `user` não decide.

    Ordem: própria, conta do autor alterada pelo ator (D2), conta do ator alterada pelo autor (D2 ao
    contrário), editada pelo ator (ou por quem alterou a conta dele). Calcula também para o
    superusuário (o AuditLog dele marca o break-glass); quem bloqueia é `decisoes_impedidas`. Número de
    consultas constante (sem consulta por item).
    """
    if not getattr(user, "pk", None):
        return {}
    agora = timezone.now()
    linhas = list(solicitacoes.order_by().values_list("id", "usuario_id", "created_at"))
    if not linhas:
        return {}
    cortes = {sol_id: _corte(criada_em, agora) for sol_id, _, criada_em in linhas}
    alteradas = contas_alteradas_por(user)
    alteraram_a_minha = quem_alterou_a_conta_de(user, min(cortes.values()))
    resultado: dict[int, str] = {}
    for sol_id, autor_id, _ in linhas:
        corte = cortes[sol_id]
        if autor_id == user.pk:
            resultado[sol_id] = SELF_APPROVAL_CODE
        elif autor_id in alteradas and alteradas[autor_id] >= corte:
            resultado[sol_id] = ALTERED_ACCOUNT_CODE
        elif autor_id in alteraram_a_minha and alteraram_a_minha[autor_id] >= corte:
            resultado[sol_id] = ALTERED_BY_AUTHOR_CODE
    restantes = {sol_id: corte for sol_id, corte in cortes.items() if sol_id not in resultado}
    if restantes:
        for sol_id in _editadas_pelo_ator(user, restantes, alteradas, alteraram_a_minha):
            resultado[sol_id] = EDITED_BY_APPROVER_CODE
    return resultado


def decisoes_impedidas(user: Usuario, solicitacoes: QuerySet[Solicitacao]) -> dict[int, str]:
    """Impedimentos que barram a decisão: o superusuário decide tudo (break-glass registrado)."""
    if getattr(user, "is_superuser", False):
        return {}
    return impedimentos(user, solicitacoes)


def _log_decisao_impedida(solicitacao: Solicitacao, user: Usuario, code: str) -> None:
    """Loga o bloqueio sem username (username é o CPF em produção)."""
    # O bloqueio da própria mantém o nome do evento do PR B1 (alertas e testes o leem).
    evento = "solicitacao_self_decision_blocked" if code == SELF_APPROVAL_CODE else "solicitacao_decision_blocked"
    logger.warning(
        evento,
        extra={
            "event": evento,
            "code": code,
            "user_id": user.pk,
            "solicitacao_id": solicitacao.pk,
        },
    )


def _marcas(code: str | None) -> dict[str, bool]:
    """Marcas do AuditLog da decisão; só podem ser True no break-glass do superusuário."""
    return {
        "conta_alterada_pelo_ator": code == ALTERED_ACCOUNT_CODE,
        "conta_do_ator_alterada_pelo_autor": code == ALTERED_BY_AUTHOR_CODE,
        "editada_pelo_ator": code == EDITED_BY_APPROVER_CODE,
    }


def _bloquear_decisao_impedida(solicitacao: Solicitacao, user: Usuario, acao: str) -> dict[str, bool]:
    """Decisão individual: 403 com o código do impedimento (própria, conta alterada, editada).

    Devolve as marcas do AuditLog da decisão.
    """
    code = impedimentos(user, Solicitacao.objects.filter(pk=solicitacao.pk)).get(solicitacao.pk)
    if code is not None and not user.is_superuser:
        _log_decisao_impedida(solicitacao, user, code)
        raise APIError(code=code, message=mensagem_impedida(code, acao), status_code=403)
    return _marcas(code)


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


def _decision_details(
    solicitacao: Solicitacao, user: Usuario, autoridade: str | None, marcas: dict[str, bool]
) -> dict[str, Any]:
    """Autoria comum a todo AuditLog de decisão (PR B1): base da autoridade + autoaprovação.

    PR 10: `conta_alterada_pelo_ator` e `editada_pelo_ator` vão em toda decisão (True só no break-glass
    do superusuário); a presença da chave separa a decisão tomada com a trava da anterior a ela.
    """
    details: dict[str, Any] = {"autoridade": autoridade, **marcas}
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
        marcas = _bloquear_decisao_impedida(solicitacao, user, "aprovar")
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
                **_decision_details(solicitacao, user, autoridade, marcas),
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
        marcas = _bloquear_decisao_impedida(solicitacao, user, "reprovar")
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
                **_decision_details(solicitacao, user, autoridade, marcas),
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
        impedidos = impedimentos(user, Solicitacao.objects.filter(id__in=found_ids))

        errors.extend(_build_batch_status_errors(ids, found_ids))

        # Approve in batch
        for sol in solicitacoes:
            # PA-02 (segregação): item próprio, de autor com conta alterada pelo ator ou editado pelo ator
            # vai para errors[]; o resto do lote segue.
            code = impedidos.get(sol.id)
            if code is not None and not user.is_superuser:
                _log_decisao_impedida(sol, user, code)
                errors.append({"id": sol.id, "code": code, "detail": mensagem_impedida(code, "aprovar")})
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
                errors.append(
                    {
                        "id": sol.id,
                        "code": exc.code,
                        "detail": exc.message,
                        "blocked_participants": exc.details.get("blocked_participants", []),
                    }
                )
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
                    **_decision_details(sol, user, autoridade, _marcas(impedidos.get(sol.id))),
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
        impedidos = impedimentos(user, Solicitacao.objects.filter(id__in=found_ids))

        errors.extend(_build_batch_status_errors(ids, found_ids))

        # Reject in batch
        for sol in solicitacoes:
            # PA-02 (segregação): item próprio, de autor com conta alterada pelo ator ou editado pelo ator
            # vai para errors[]; o resto do lote segue.
            code = impedidos.get(sol.id)
            if code is not None and not user.is_superuser:
                _log_decisao_impedida(sol, user, code)
                errors.append({"id": sol.id, "code": code, "detail": mensagem_impedida(code, "reprovar")})
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
                    **_decision_details(sol, user, autoridade, _marcas(impedidos.get(sol.id))),
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
