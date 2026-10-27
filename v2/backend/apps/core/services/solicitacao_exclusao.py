"""Travas de excluir uma Solicitacao que se sabem sem falar com o Google.

SSOT das recusas do `SolicitacaoViewSet.perform_destroy` (que as levanta como 400) e do campo
`pode_excluir` da lista (que avisa a tela). Quem pode excluir (o objeto) é outra regra:
`EscritaEmSolicitacao.exclui`, em `solicitacao_scope.py`.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from django.db.models import Q

from apps.core.models import AuditLog


def esta_no_google(sol: Any) -> bool:
    """O sistema pôs (ou pode ter posto) o evento no Google: `PUBLISHED`, `ERROR` ou com o id de lá.

    `ERROR` sem id conta: a publicação que falhou pode ter criado o evento com o id determinístico.
    """
    return getattr(sol, "gcal_status", None) in ("PUBLISHED", "ERROR") or bool(getattr(sol, "external_event_id", None))


def ids_ja_aprovadas(ids: Iterable[int]) -> set[int]:
    """Das solicitações `ids`, as que já foram aprovadas, numa consulta só.

    A prova é o AuditLog APPROVE (individual ou em lote) ou o UPDATE de uma edição que partiu de SUPER
    `aprovado` (`aprovada_como_super`, que cobre a aprovada sem APPROVE: carga antiga, admin Django,
    data-fix). A auto-aprovação da NAO_SUPER não grava nenhum dos dois.
    """
    ids = list(ids)
    if not ids:
        return set()
    achados = (
        AuditLog.objects.filter(model_name="Solicitacao", details__solicitacao_id__in=ids)
        .filter(Q(action=AuditLog.Action.APPROVE) | Q(action=AuditLog.Action.UPDATE, details__aprovada_como_super=True))
        .values_list("details__solicitacao_id", flat=True)
    )
    return {int(sol_id) for sol_id in achados}


def motivo_que_impede_excluir(sol: Any, *, ja_aprovada: bool, pode_tirar_do_google: bool) -> str | None:
    """Por que `sol` não se exclui (texto do 400), ou None. Na ordem em que o `perform_destroy` recusa.

    `ja_aprovada`: `sol.pk in ids_ja_aprovadas(...)`. `pode_tirar_do_google`: `can_publish_solicitacao` de
    quem exclui (só conta se o evento está no Google, e a exclusão o tira de lá).
    """
    if sol.publicado_fora_do_sistema:
        return (
            "Este evento está no Google Agenda pela planilha e o sistema não o adotou: "
            "excluir aqui deixaria o evento no Google. Ajuste no Google, ou peça a adoção."
        )
    # M10-03 (#1625): PENDING = task Celery de sincronização já enfileirada;
    # excluir nessa janela deixa a task operar sobre um registro removido.
    if sol.gcal_status == "PENDING":
        return (
            "Não é possível excluir enquanto a sincronização com o Google Calendar está "
            "em andamento. Aguarde a conclusão."
        )
    projeto_fluxo = sol.projeto.fluxo if sol.projeto else None
    if projeto_fluxo == "SUPER" and sol.status != "pendente":
        return (
            "Solicitações do fluxo SUPER só podem ser excluídas enquanto estiverem pendentes. "
            "Esta solicitação já foi aprovada ou reprovada."
        )
    if ja_aprovada:
        # Pendente sai pela reprovação; aprovada (ou reprovada) não pendente: só a administração.
        if sol.status == "pendente":
            saida = "Para tirar o evento, peça a reprovação a quem aprova: assim a saída fica registrada."
        else:
            saida = (
                "Como ela não está pendente, não há reprovação a pedir: para tirar o evento, "
                "fale com a administração do sistema."
            )
        return f"Esta solicitação já foi aprovada e não pode ser excluída. {saida}"
    if esta_no_google(sol) and not pode_tirar_do_google:
        return (
            "Não é possível excluir uma solicitação já publicada no Google Calendar. "
            "Cancele o evento primeiro se precisar excluir."
        )
    return None
