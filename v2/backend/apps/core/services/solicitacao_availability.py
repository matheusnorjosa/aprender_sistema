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
from dataclasses import dataclass, field

from django.db import connection

from apps.core.exceptions import ValidationAPIError
from apps.core.models import Participation, Solicitacao, Usuario
from apps.core.services.availability_service import (
    ENFORCED_ROLES,
    Conflict,
    check_conflicts_uncached,
    coordenador_ocupante,
)

logger = logging.getLogger(__name__)

# ENFORCED_ROLES (papéis ocupantes; CONVIDADO fica de fora — é audiência, não recurso
# alocado) é SSOT do motor: definido em availability_service e importado acima, para o
# enforcement e a query de eventos existentes usarem o MESMO predicado (M08-07 / #1664).

# Namespace do advisory lock (classid), para não colidir com outros locks da aplicação.
_LOCK_NAMESPACE = 1452


@dataclass
class ParticipantConflicts:
    """Conflitos (barram) e avisos (não barram) de um participante específico."""

    usuario_id: int
    usuario_nome: str
    conflicts: list[Conflict]
    warnings: list[Conflict] = field(default_factory=list)


@dataclass
class GuardResult:
    """
    Resultado da checagem de todos os participantes de uma solicitação.

    ok: True se nenhum participante tem conflito (aviso não conta)
    blocked: participantes com conflito (vazio se ok)
    skipped_guests: e-mails de convidados externos que não puderam ser checados
    checked_usuario_ids: ids efetivamente checados (já deduplicados)
    warnings: participantes com aviso, bloqueados ou não. Nunca muda `ok`. Hoje fica
        vazio: o motor não emite aviso desde 05/10/2026 (o M saiu).
    """

    ok: bool
    blocked: list[ParticipantConflicts]
    skipped_guests: list[str]
    checked_usuario_ids: list[int]
    warnings: list[ParticipantConflicts] = field(default_factory=list)


def _display_name(usuario: Usuario) -> str:
    """Nome legível do participante para as mensagens de conflito (RD-08)."""
    return str(usuario.get_full_name() or usuario.username)


def collect_participants(solicitacao: Solicitacao) -> tuple[list[Usuario], list[str]]:
    """
    Lê do banco quem deve ser checado nesta solicitação.

    A fonte é a tabela `Participation` já gravada — não o payload da requisição. Resolver
    o payload de novo aqui abriria espaço para checar pessoas diferentes das que foram
    salvas, que é exatamente a falha que este guard existe para fechar.

    Entram os FORMADORES (papéis de `ENFORCED_ROLES`) e, só quando o evento tem
    `coordenador_acompanha=True`, o coordenador responsável (`coordenador_ocupante`). Quem
    criou não entra por ter criado (decisão do dono, 05/10/2026; antes entrava sempre).

    Convidado externo sem cadastro (`usuario=NULL` + `guest_email`) é fisicamente
    não-checável: não tem `AvailabilityBlock` nem casa com `Q(participations__usuario=)`.
    Volta em `skipped_guests` para ser reportado — nunca ignorado em silêncio.

    Returns:
        (usuarios a checar, deduplicados por id; e-mails de convidados pulados)
    """
    participations = Participation.objects.filter(solicitacao=solicitacao, role__in=ENFORCED_ROLES).select_related(
        "usuario"
    )

    # Dedup por id é obrigatório: o responsável que acompanha pode também estar em
    # formador_ids. Sem dedup as horas dele contariam 2x no RD-05.
    usuarios_by_id: dict[int, Usuario] = {}
    skipped_guests: list[str] = []

    responsavel = coordenador_ocupante(solicitacao)
    if responsavel is not None:
        usuarios_by_id[responsavel.id] = responsavel

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
    não como filtro por `ref_id` depois.

    Só `conflicts` (X, T, P, D) bloqueia. `warnings` é repassado por pessoa, sem bloquear;
    hoje vem vazio (o limite diário M saiu em 05/10/2026).

    Args:
        solicitacao: evento já gravado (precisa de pk, inicio, fim)
        lock: trava os participantes antes de ler. False só para leitura consultiva.

    Returns:
        GuardResult com ok/blocked/skipped_guests/warnings
    """
    usuarios, skipped_guests = collect_participants(solicitacao)

    if lock:
        lock_participants([u.id for u in usuarios])

    blocked: list[ParticipantConflicts] = []
    warned: list[ParticipantConflicts] = []
    for usuario in usuarios:
        result = check_conflicts_uncached(
            usuario=usuario,
            inicio=solicitacao.inicio,
            fim=solicitacao.fim,
            municipio=solicitacao.municipio,
            exclude_solicitacao_id=solicitacao.pk,
        )
        if result.ok and not result.warnings:
            continue
        participante = ParticipantConflicts(
            usuario_id=usuario.id,
            usuario_nome=_display_name(usuario),
            conflicts=result.conflicts,
            warnings=result.warnings,
        )
        if not result.ok:
            blocked.append(participante)
        if result.warnings:
            warned.append(participante)

    return GuardResult(
        ok=not blocked,
        blocked=blocked,
        skipped_guests=skipped_guests,
        checked_usuario_ids=[u.id for u in usuarios],
        warnings=warned,
    )


# Texto da ação barrada, por call-site (`action` de `enforce_solicitacao_availability`).
_ACAO_TEXTO: dict[str, str] = {
    "create": "criar o evento",
    "update": "salvar a alteração",
    "approve": "aprovar a solicitação",
    "batch_approve": "aprovar a solicitação",
}
_ACAO_GENERICA = "concluir a ação"

# Motivo em linguagem de quem usa, por código de conflito do motor (X/T/P/D). É só
# apresentação: quem decide o conflito continua sendo `check_conflicts_uncached`. Sempre
# consultado com `.get` — código fora do mapa cai no texto genérico, nunca em KeyError.
# O limite diário (M) não está aqui: o motor não o emite desde 05/10/2026.
_MOTIVO_TEXTO: dict[str, str] = {
    "X": "tem outro evento aprovado neste horário",
    "T": "tem bloqueio de agenda no período",
    "P": "tem bloqueio parcial de agenda no período",
    "D": "não tem o intervalo de deslocamento entre cidades",
}
_MOTIVO_GENERICO = "tem conflito de agenda"
# O motor usa o código X também para "Intervalo inválido" (fim <= início): só a
# sobreposição de fato pode dizer "outro evento".
_TITULO_SOBREPOSICAO = "Sobreposição"


def _motivo(conflict: Conflict) -> str:
    """Motivo legível de um conflito; texto genérico (com o título, se houver) fora do mapa."""
    code = str(getattr(conflict, "code", "") or "")
    titulo = str(getattr(conflict, "title", "") or "").strip()
    texto = _MOTIVO_TEXTO.get(code)
    if texto is not None and (code != "X" or titulo == _TITULO_SOBREPOSICAO):
        return texto
    return f"{_MOTIVO_GENERICO} ({titulo.lower()})" if titulo else _MOTIVO_GENERICO


def _build_message(guard: GuardResult, *, action: str = "create") -> str:
    """Mensagem de bloqueio: a ação barrada, quem está bloqueado e por quê (RD-08)."""
    partes: list[str] = []
    for p in guard.blocked:
        motivos = list(dict.fromkeys(_motivo(c) for c in p.conflicts)) or [_MOTIVO_GENERICO]
        partes.append(f"{p.usuario_nome} {' e '.join(motivos)}")
    return f"Não é possível {_ACAO_TEXTO.get(action, _ACAO_GENERICA)}: {'; '.join(partes)}."


def raise_if_blocked(guard: GuardResult, *, action: str = "create") -> None:
    """
    Converte um GuardResult bloqueado em 400 `availability_conflict`.

    Conflito (X, T, P, D) é bloqueio duro, sem override: vale para todos os fluxos,
    inclusive NAO_SUPER (decisão de negócio, 2026-07-16). O limite diário (M) não existe
    mais (decisão do dono, 05/10/2026).

    O payload mantém `conflicts` achatado como antes do #1452 (clientes existentes leem
    essa chave) e acrescenta `blocked_participants` com a atribuição por pessoa. As chaves
    `warnings` (achatada, de todos os participantes com aviso) e
    `blocked_participants[].warnings` são aditivas: trazem o que foi calculado e não barra.
    A mensagem e `conflicts` só falam do que barra.
    """
    if guard.ok:
        return

    todos: list[Conflict] = [c for p in guard.blocked for c in p.conflicts]
    raise ValidationAPIError(
        message=_build_message(guard, action=action),
        code="availability_conflict",
        extra={
            "conflicts": [c.__dict__ for c in todos],
            "warnings": [w.__dict__ for p in guard.warnings for w in p.warnings],
            "blocked_participants": [
                {
                    "usuario_id": p.usuario_id,
                    "usuario_nome": p.usuario_nome,
                    "conflicts": [c.__dict__ for c in p.conflicts],
                    "warnings": [w.__dict__ for w in p.warnings],
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
        action: rótulo do call-site (create/update/approve/batch_approve): vai para o log e
            escolhe o verbo da mensagem de bloqueio. Não muda o que é checado nem a decisão.

    Returns:
        GuardResult (ok=True) quando passa; `warnings` traz quem teve aviso (hoje, ninguém)

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

    if guard.warnings:
        # Aviso não barra, mas fica registrado. Só ids, sem nome.
        logger.info(
            "availability_warning",
            extra={
                "event": "availability_warning",
                "action": action,
                "solicitacao_id": solicitacao.pk,
                "warned_usuario_ids": [p.usuario_id for p in guard.warnings],
                "codes": sorted({w.code for p in guard.warnings for w in p.warnings}),
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
        raise_if_blocked(guard, action=action)

    return guard
