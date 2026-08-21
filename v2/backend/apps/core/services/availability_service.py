"""
Availability Service - Verificação de conflitos (RD-01 a RD-08)

Serviço puro, sem efeitos colaterais. NÃO altera estado, NÃO aprova nada.
Apenas calcula conflitos e retorna lista estruturada.

RD-01: Não-sobreposição (overlap ≥ 1 min → X; adjacente OK)
RD-02: Bloqueio Total (T) impede qualquer evento
RD-03: Bloqueio Parcial (P) impede dentro do subintervalo
RD-04: Deslocamento (D) buffer configurável entre municípios
RD-05: Capacidade diária (M) limite configurável de horas/dia
RD-06: Timezone-aware (UTC storage, America/Fortaleza comparison)
RD-07: Prioridade de checagem (reporta todos)
RD-08: Mensagens com formador, intervalo, tipo, detalhe
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false, reportReturnType=false, reportGeneralTypeIssues=false

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from apps.core.models import AvailabilityBlock, Municipio, Participation, Solicitacao, Usuario
from apps.core.services.config_service import get_cfg
from apps.core.types import ConflictCode
from apps.core.utils.cache_utils import cache_availability_check

# SSOT dos papéis OCUPANTES (RD): quem, participando de um evento aprovado, ocupa a
# agenda para efeito de conflito/capacidade. CONVIDADO não ocupa. Usado tanto no
# enforcement (solicitacao_availability) quanto na query de eventos existentes aqui —
# um único predicado, sem lista de papéis duplicada fora deste módulo. (M08-07 / #1664)
ENFORCED_ROLES: tuple[str, ...] = (
    Participation.Role.COORDENADOR.value,
    Participation.Role.FORMADOR.value,
    Participation.Role.COORD_ACOMPANHA.value,
)


@dataclass
class Conflict:
    """
    Representa um conflito de disponibilidade.

    code: Código do tipo de conflito (X/T/P/D/M)
    title: Título breve do conflito
    detail: Mensagem descritiva detalhada
    ref_id: ID do evento/bloqueio relacionado (opcional)
    """

    code: ConflictCode
    title: str
    detail: str
    ref_id: int | None = None


@dataclass
class CheckResult:
    """
    Resultado da verificação de disponibilidade.

    ok: True se não há conflitos
    conflicts: Lista de conflitos encontrados
    """

    ok: bool
    conflicts: list[Conflict]


def to_local(dt: datetime) -> datetime:
    """
    Converte datetime UTC para timezone local do projeto (RD-06).

    Args:
        dt: datetime em UTC

    Returns:
        datetime convertido para America/Fortaleza
    """
    tz_name: str = getattr(settings, "TZ_PROJECT", "America/Fortaleza")
    tz = ZoneInfo(tz_name)

    # Se naive, assume UTC
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.utc)

    return dt.astimezone(tz)


def same_day_local(a: datetime, b: datetime) -> bool:
    """
    Verifica se dois datetimes são no mesmo dia (timezone local).

    Args:
        a, b: datetimes a comparar

    Returns:
        bool: True se mesma data local
    """
    la: datetime = to_local(a)
    lb: datetime = to_local(b)
    return la.date() == lb.date()


def _fmt_interval_local(start: datetime, end: datetime) -> str:
    """
    Formata intervalo para exibição (RD-08).

    Args:
        start, end: datetimes do intervalo

    Returns:
        str: Formato "HH:MM dd/mm–HH:MM dd/mm"
    """
    s: datetime = to_local(start)
    e: datetime = to_local(end)
    return f"{s:%H:%M %d/%m}–{e:%H:%M %d/%m}"


def _clip_minutes(start: datetime, end: datetime, window_start: datetime, window_end: datetime) -> int:
    """Minutos de [start, end] que caem dentro de [window_start, window_end] (>= 0).

    Usado pela RD-05 para recortar tanto os eventos existentes quanto o novo pela
    janela de UM dia local — assim um evento que cruza a meia-noite contribui só a
    fração correta em cada dia (M08-09 / #1664).
    """
    lo = max(start, window_start)
    hi = min(end, window_end)
    return max(int((hi - lo).total_seconds() // 60), 0)


def _check_conflicts_impl(
    *,
    usuario: Usuario,
    inicio: datetime,
    fim: datetime,
    municipio: Municipio | None = None,
    exclude_solicitacao_id: int | None = None,
) -> CheckResult:
    """
    Implementação pura da checagem RD-01..RD-08. Não usar diretamente.

    Público: `check_conflicts` (cacheado, consultivo) e `check_conflicts_uncached`
    (sem cache, para enforcement transacional).

    NÃO grava nada. NÃO aprova nada.

    Considera:
    - Solicitações aprovadas (eventos confirmados) → RD-01 (X)
    - AvailabilityBlock com status=aprovado → RD-02 (T), RD-03 (P)
    - Buffer de deslocamento entre municípios → RD-04 (D)
    - Capacidade diária → RD-05 (M)

    Args:
        usuario: Usuário para verificar disponibilidade
        inicio: datetime início do intervalo (timezone-aware UTC)
        fim: datetime fim do intervalo (timezone-aware UTC)
        municipio: Município opcional (necessário para checagem RD-04)
        exclude_solicitacao_id: Ignora esta solicitação em TODOS os checks. Usado ao
            revalidar um evento já gravado (update/aprovação), para que ele não
            conflite consigo mesmo. Precisa ser aplicado na origem (`events_qs`) e não
            filtrado depois por `ref_id`: o conflito M (RD-05) não tem `ref_id` e
            somaria as horas do próprio evento em dobro.

    Returns:
        CheckResult com ok=True/False e lista de conflitos
    """
    # Validação básica
    if not inicio or not fim or fim <= inicio:
        return CheckResult(
            ok=False,
            conflicts=[Conflict("X", "Intervalo inválido", "fim deve ser > início")],
        )

    # Carregar configurações (RD-04, RD-05) com fallback para settings
    cfg: dict[str, str] = get_cfg("availability", {})
    buffer_min: int = int(cfg.get("TRAVEL_BUFFER_MINUTES") or getattr(settings, "TRAVEL_BUFFER_MINUTES", 120))
    daily_limit_h: float = float(
        cfg.get("AVAILABILITY_DAILY_LIMIT_HOURS") or getattr(settings, "AVAILABILITY_DAILY_LIMIT_HOURS", 8)
    )

    conflicts: list[Conflict] = []
    # M08-07 (#1664): só papéis OCUPANTES (ENFORCED_ROLES) bloqueiam. Antes qualquer
    # participação casava, então um CONVIDADO bloqueava indevidamente o FORMADOR. O
    # filtro por role vai na ORIGEM da query (events_qs), não em Python depois.
    events_qs = Solicitacao.objects.filter(status=Solicitacao.Status.APROVADO).filter(
        Q(usuario=usuario) | Q(participations__usuario=usuario, participations__role__in=ENFORCED_ROLES)
    )
    if exclude_solicitacao_id is not None:
        events_qs = events_qs.exclude(pk=exclude_solicitacao_id)

    # ================================================================
    # RD-02, RD-03: BLOQUEIOS aprovados
    # ================================================================
    blocks = AvailabilityBlock.objects.filter(usuario=usuario, status=AvailabilityBlock.Status.APROVADO).filter(
        Q(inicio__lt=fim) & Q(fim__gt=inicio)  # Interseção
    )

    for b in blocks:
        interval: str = _fmt_interval_local(b.inicio, b.fim)
        if b.tipo == "T":
            # RD-02: Bloqueio Total
            conflicts.append(
                Conflict(
                    "T",
                    "Bloqueio total",
                    f"Conflita com bloqueio total {interval}",
                    ref_id=b.id,
                )
            )
        else:
            # RD-03: Bloqueio Parcial
            conflicts.append(
                Conflict(
                    "P",
                    "Bloqueio parcial",
                    f"Conflita com bloqueio parcial {interval}",
                    ref_id=b.id,
                )
            )

    # ================================================================
    # RD-01: SOBREPOSIÇÃO com eventos aprovados
    # ================================================================
    events = events_qs.filter(Q(inicio__lt=fim) & Q(fim__gt=inicio)).distinct()

    for ev in events:
        interval: str = _fmt_interval_local(ev.inicio, ev.fim)
        conflicts.append(
            Conflict(
                "X",
                "Sobreposição",
                f"Conflita com evento aprovado #{ev.id} ({interval})",
                ref_id=ev.id,
            )
        )

    # ================================================================
    # RD-04: BUFFER de deslocamento entre municípios
    # ================================================================
    # RD-04 sempre verifica buffer. Se municipio=None, trata como cidade diferente.
    # Evento imediatamente anterior
    prev_ev: Solicitacao | None = events_qs.filter(fim__lte=inicio).order_by("-fim").distinct().first()

    # Evento imediatamente posterior
    next_ev: Solicitacao | None = events_qs.filter(inicio__gte=fim).order_by("inicio").distinct().first()

    # Verificar buffer anterior
    if prev_ev:
        # RD-04: municipio=None é tratado como cidade diferente (fix #588)
        # Se qualquer lado é None, não podemos afirmar que são na mesma cidade → requer buffer.
        municipio_id: int | None = municipio.id if municipio else None
        prev_municipio_id: int | None = prev_ev.municipio_id

        same_city: bool = municipio_id is not None and municipio_id == prev_municipio_id
        prev_diff_city: bool = not same_city

        if prev_diff_city:
            delta: timedelta = inicio - prev_ev.fim
            mins: int = int(delta.total_seconds() // 60)
            # Buffer exato (==) deve passar, apenas < buffer conflita
            if mins < buffer_min:
                conflicts.append(
                    Conflict(
                        "D",
                        "Buffer deslocamento insuficiente",
                        f"Apenas {mins} min após evento #{prev_ev.id}. "
                        f"Exige ≥ {buffer_min} min entre cidades distintas.",
                        ref_id=prev_ev.id,
                    )
                )

    # Verificar buffer posterior
    if next_ev:
        municipio_id = municipio.id if municipio else None
        next_municipio_id: int | None = next_ev.municipio_id

        same_city = municipio_id is not None and municipio_id == next_municipio_id
        next_diff_city: bool = not same_city

        if next_diff_city:
            delta: timedelta = next_ev.inicio - fim
            mins: int = int(delta.total_seconds() // 60)
            # Buffer exato (==) deve passar, apenas < buffer conflita
            if mins < buffer_min:
                conflicts.append(
                    Conflict(
                        "D",
                        "Buffer deslocamento insuficiente",
                        f"Apenas {mins} min antes de evento #{next_ev.id}. "
                        f"Exige ≥ {buffer_min} min entre cidades distintas.",
                        ref_id=next_ev.id,
                    )
                )

    # ================================================================
    # RD-05: CAPACIDADE DIÁRIA
    # ================================================================
    # M08-09 (#1664): checa CADA dia LOCAL que o novo evento toca. Eventos
    # existentes E o novo são recortados pela janela do dia (`_clip_minutes`),
    # então um evento que cruza a meia-noite (ex.: 22h→02h) contribui só a fração
    # certa em D e em D+1 — antes, o novo evento entrava com a duração CHEIA no dia
    # do início e o dia seguinte nunca era checado.
    # Issue #249: ranges de datetime (não `.date()`) por causa de UTC vs local (RD-06).
    tz_name: str = getattr(settings, "TZ_PROJECT", "America/Fortaleza")
    local_tz = ZoneInfo(tz_name)
    daily_limit_minutes: int = int(daily_limit_h * 60)

    first_day = to_local(inicio).date()
    last_day = to_local(fim).date()
    day = first_day
    while day <= last_day:
        day_start: datetime = datetime.combine(day, time.min, tzinfo=local_tz)
        day_end: datetime = datetime.combine(day, time.max, tzinfo=local_tz)

        # Só checa dias onde o novo evento realmente ocupa tempo (evita falso M num
        # dia adjacente onde o evento apenas toca a fronteira).
        new_minutes = _clip_minutes(inicio, fim, day_start, day_end)
        if new_minutes > 0:
            total_minutes = new_minutes
            for ev in events_qs.filter(inicio__lt=day_end, fim__gt=day_start).distinct():
                total_minutes += _clip_minutes(ev.inicio, ev.fim, day_start, day_end)

            if total_minutes > daily_limit_minutes:
                conflicts.append(
                    Conflict(
                        "M",
                        "Capacidade diária excedida",
                        f"Total do dia {day:%d/%m}: {total_minutes} min > "
                        f"limite {daily_limit_minutes} min ({daily_limit_h}h)",
                    )
                )

        day += timedelta(days=1)

    # ================================================================
    # RD-07: Retornar todos os conflitos encontrados
    # ================================================================
    return CheckResult(ok=(len(conflicts) == 0), conflicts=conflicts)


@cache_availability_check(timeout=300)  # CP3: Cache 5 min (TTL curto, dados mudam frequentemente)
def check_conflicts(
    *, usuario: Usuario, inicio: datetime, fim: datetime, municipio: Municipio | None = None
) -> CheckResult:
    """
    Checagem consultiva de disponibilidade (RD-01..RD-08), com cache de 5 min.

    Para leitura/preview: telas de disponibilidade, feedback antecipado no wizard.
    NÃO usar para enforcement — o resultado pode ter até 5 min de atraso.
    Enforcement usa `check_conflicts_uncached` dentro da transação.

    A assinatura não expõe `exclude_solicitacao_id` de propósito: a chave de cache
    (`cache_utils.py`) é montada a partir de uma whitelist fixa de campos, então um
    argumento extra alteraria o resultado sem alterar a chave — envenenando o cache.

    Args:
        usuario: Usuário para verificar disponibilidade
        inicio: datetime início do intervalo (timezone-aware UTC)
        fim: datetime fim do intervalo (timezone-aware UTC)
        municipio: Município opcional (necessário para checagem RD-04)

    Returns:
        CheckResult com ok=True/False e lista de conflitos
    """
    return _check_conflicts_impl(usuario=usuario, inicio=inicio, fim=fim, municipio=municipio)


def check_conflicts_uncached(
    *,
    usuario: Usuario,
    inicio: datetime,
    fim: datetime,
    municipio: Municipio | None = None,
    exclude_solicitacao_id: int | None = None,
) -> CheckResult:
    """
    Mesma checagem de `check_conflicts`, sempre lendo do banco.

    Usar em enforcement (criação, edição, aprovação, publicação): dentro da transação,
    depois de travar os participantes, um resultado cacheado deixaria passar o
    double-booking que o lock existe para impedir.

    Args:
        usuario: Usuário para verificar disponibilidade
        inicio: datetime início do intervalo (timezone-aware UTC)
        fim: datetime fim do intervalo (timezone-aware UTC)
        municipio: Município opcional (necessário para checagem RD-04)
        exclude_solicitacao_id: Ignora esta solicitação (revalidar evento já gravado)

    Returns:
        CheckResult com ok=True/False e lista de conflitos
    """
    return _check_conflicts_impl(
        usuario=usuario,
        inicio=inicio,
        fim=fim,
        municipio=municipio,
        exclude_solicitacao_id=exclude_solicitacao_id,
    )
