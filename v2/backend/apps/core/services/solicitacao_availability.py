"""
Solicitacao Availability Guard — enforcement de RD-01..RD-08 por participante (#1452).

SSOT dos call-sites que gravam/aprovam/publicam evento. O cálculo dos conflitos continua
em `availability_service.check_conflicts_uncached` (RD-01..RD-08); aqui decidimos QUEM é
checado, garantimos exclusão mútua entre transações e traduzimos o resultado em bloqueio.

Motivo: `check_conflicts` era chamado apenas para o criador da solicitação. Como o
coordenador que cria tipicamente não é o formador que atende, as regras rodavam na pessoa
errada e o formador podia ser alocado em dois eventos simultâneos.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportArgumentType=false

from __future__ import annotations

import logging
from dataclasses import dataclass

from django.db import connection

from apps.core.exceptions import ValidationAPIError
from apps.core.models import Participation, Solicitacao, Usuario
from apps.core.services.availability_service import Conflict, check_conflicts_uncached

logger = logging.getLogger(__name__)

# Papéis que ocupam a agenda da pessoa e por isso entram na checagem.
#
# CONVIDADO fica de fora de propósito: é audiência, não recurso alocado. Checá-lo
# estouraria a capacidade diária (RD-05) de quem é convidado a vários eventos no mesmo
# dia — um diretor convidado a 5 eventos bloquearia os 5.
ENFORCED_ROLES: tuple[str, ...] = (
    Participation.Role.COORDENADOR,
    Participation.Role.FORMADOR,
    Participation.Role.COORD_ACOMPANHA,
)

# Namespace do advisory lock (classid), para não colidir com outros locks da aplicação.
_LOCK_NAMESPACE = 1452


@dataclass
class ParticipantConflicts:
    """Conflitos encontrados para um participante específico."""

    usuario_id: int
    usuario_nome: str
    conflicts: list[Conflict]


@dataclass
class GuardResult:
    """
    Resultado da checagem de todos os participantes de uma solicitação.

    ok: True se nenhum participante tem conflito
    blocked: participantes com conflito (vazio se ok)
    skipped_guests: e-mails de convidados externos que não puderam ser checados
    checked_usuario_ids: ids efetivamente checados (já deduplicados)
    """

    ok: bool
    blocked: list[ParticipantConflicts]
    skipped_guests: list[str]
    checked_usuario_ids: list[int]


def _display_name(usuario: Usuario) -> str:
    """Nome legível do participante para as mensagens de conflito (RD-08)."""
    return str(usuario.get_full_name() or usuario.username)


def collect_participants(solicitacao: Solicitacao) -> tuple[list[Usuario], list[str]]:
    """
    Lê do banco quem deve ser checado nesta solicitação.

    A fonte é a tabela `Participation` já gravada — não o payload da requisição. Resolver
    o payload de novo aqui abriria espaço para checar pessoas diferentes das que foram
    salvas, que é exatamente a falha que este guard existe para fechar.

    O criador (`solicitacao.usuario`) entra sempre, mesmo sem `Participation`: preserva a
    checagem que já existia antes do #1452 e cobre eventos sem participantes extras.

    Convidado externo sem cadastro (`usuario=NULL` + `guest_email`) é fisicamente
    não-checável: não tem `AvailabilityBlock` nem casa com `Q(participations__usuario=)`.
    Volta em `skipped_guests` para ser reportado — nunca ignorado em silêncio.

    Returns:
        (usuarios a checar, deduplicados por id; e-mails de convidados pulados)
    """
    participations = Participation.objects.filter(solicitacao=solicitacao, role__in=ENFORCED_ROLES).select_related(
        "usuario"
    )

    # Dedup por id é obrigatório: o coordenador é sempre gravado como COORDENADOR e pode
    # também estar em formador_ids. Sem dedup as horas dele contariam 2x no RD-05.
    usuarios_by_id: dict[int, Usuario] = {}
    skipped_guests: list[str] = []

    if solicitacao.usuario_id:
        usuarios_by_id[solicitacao.usuario_id] = solicitacao.usuario

    for p in participations:
        if p.usuario_id:
            usuarios_by_id.setdefault(p.usuario_id, p.usuario)
        elif p.guest_email and p.guest_email not in skipped_guests:
            skipped_guests.append(p.guest_email)

    usuarios = [usuarios_by_id[uid] for uid in sorted(usuarios_by_id)]
    return usuarios, skipped_guests


def lock_participants(usuario_ids: list[int]) -> None:
    """
    Trava os participantes até o fim da transação (`pg_advisory_xact_lock`).

    Sem isto o fix é apenas metade: `select_for_update` nas rotinas de aprovação tranca a
    própria linha da solicitação. Duas solicitações distintas do mesmo formador trancam
    linhas disjuntas, e como `pendente` é invisível para a checagem (que só olha eventos
    aprovados), cada transação lê a outra como inexistente e ambas commitam — o formador
    acaba com dois eventos no mesmo horário.

    Travando por `usuario_id`, a segunda transação espera a primeira e enxerga o evento
    recém-aprovado. A ordem ASC fixa evita deadlock quando duas solicitações compartilham
    mais de um participante.

    Requer transação aberta: `pg_advisory_xact_lock` libera no commit/rollback.
    """
    if not usuario_ids:
        return

    with connection.cursor() as cursor:
        for usuario_id in sorted(usuario_ids):
            cursor.execute("SELECT pg_advisory_xact_lock(%s, %s)", [_LOCK_NAMESPACE, usuario_id])


def check_solicitacao_availability(solicitacao: Solicitacao, *, lock: bool = True) -> GuardResult:
    """
    Checa RD-01..RD-08 para cada participante da solicitação.

    Deve rodar dentro de `transaction.atomic()`: o lock é por transação e o resultado só
    vale enquanto ele estiver mantido.

    A própria solicitação é excluída da checagem (`exclude_solicitacao_id`) — senão um
    evento já gravado conflitaria consigo mesmo. A exclusão acontece na origem da query e
    não como filtro por `ref_id` depois: o conflito de capacidade diária (M, RD-05) não
    tem `ref_id` e somaria as horas do próprio evento em dobro.

    Args:
        solicitacao: evento já gravado (precisa de pk, inicio, fim)
        lock: trava os participantes antes de ler. False só para leitura consultiva.

    Returns:
        GuardResult com ok/blocked/skipped_guests
    """
    usuarios, skipped_guests = collect_participants(solicitacao)

    if lock:
        lock_participants([u.id for u in usuarios])

    blocked: list[ParticipantConflicts] = []
    for usuario in usuarios:
        result = check_conflicts_uncached(
            usuario=usuario,
            inicio=solicitacao.inicio,
            fim=solicitacao.fim,
            municipio=solicitacao.municipio,
            exclude_solicitacao_id=solicitacao.pk,
        )
        if not result.ok:
            blocked.append(
                ParticipantConflicts(
                    usuario_id=usuario.id,
                    usuario_nome=_display_name(usuario),
                    conflicts=result.conflicts,
                )
            )

    return GuardResult(
        ok=not blocked,
        blocked=blocked,
        skipped_guests=skipped_guests,
        checked_usuario_ids=[u.id for u in usuarios],
    )


def _build_message(guard: GuardResult) -> str:
    """Mensagem de bloqueio nomeando quem está alocado (RD-08)."""
    nomes = ", ".join(p.usuario_nome for p in guard.blocked)
    if len(guard.blocked) == 1:
        return f"{nomes} já está alocado neste horário. Não é possível criar o evento."
    return f"{nomes} já estão alocados neste horário. Não é possível criar o evento."


def raise_if_blocked(guard: GuardResult) -> None:
    """
    Converte um GuardResult bloqueado em 400 `availability_conflict`.

    Conflito é bloqueio duro, sem override: vale para todos os fluxos, inclusive
    NAO_SUPER (decisão de negócio, 2026-07-16).

    O payload mantém `conflicts` achatado como antes do #1452 (clientes existentes leem
    essa chave) e acrescenta `blocked_participants` com a atribuição por pessoa.
    """
    if guard.ok:
        return

    todos: list[Conflict] = [c for p in guard.blocked for c in p.conflicts]
    raise ValidationAPIError(
        message=_build_message(guard),
        code="availability_conflict",
        extra={
            "conflicts": [c.__dict__ for c in todos],
            "blocked_participants": [
                {
                    "usuario_id": p.usuario_id,
                    "usuario_nome": p.usuario_nome,
                    "conflicts": [c.__dict__ for c in p.conflicts],
                }
                for p in guard.blocked
            ],
            "skipped_guests": guard.skipped_guests,
        },
    )


def enforce_solicitacao_availability(solicitacao: Solicitacao, *, action: str) -> GuardResult:
    """
    Checa e bloqueia. Ponto de entrada dos call-sites (create, update, approve, publish).

    Requer transação aberta.

    Args:
        solicitacao: evento já gravado
        action: rótulo do call-site, só para log/auditoria

    Returns:
        GuardResult (ok=True) quando passa

    Raises:
        ValidationAPIError: `availability_conflict` quando algum participante tem conflito
    """
    guard = check_solicitacao_availability(solicitacao)

    if guard.skipped_guests:
        # PA-05: convidado externo não é checável. Registrar sempre — a ausência de
        # checagem precisa ser visível, não presumida.
        logger.warning(
            "availability_guest_check_skipped",
            extra={
                "event": "availability_guest_check_skipped",
                "action": action,
                "solicitacao_id": solicitacao.pk,
                "skipped_guests": guard.skipped_guests,
            },
        )

    if not guard.ok:
        logger.info(
            "availability_blocked",
            extra={
                "event": "availability_blocked",
                "action": action,
                "solicitacao_id": solicitacao.pk,
                "blocked_usuario_ids": [p.usuario_id for p in guard.blocked],
            },
        )
        raise_if_blocked(guard)

    return guard
