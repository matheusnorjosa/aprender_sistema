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

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

import pytz
from apps.core.models import AvailabilityBlock, Municipio, Solicitacao, Usuario
from apps.core.services.config_service import get_cfg
from apps.core.types import ConflictCode


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
    tz: pytz.BaseTzInfo = pytz.timezone(tz_name)

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


def check_conflicts(
    *, usuario: Usuario, inicio: datetime, fim: datetime, municipio: Municipio | None = None
) -> CheckResult:
    """
    Verifica conflitos para um novo intervalo (inicio, fim) de um usuário.

    NÃO grava nada. NÃO aprova nada. Checagem consultiva apenas.

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
    buffer_min: int = int(
        cfg.get("TRAVEL_BUFFER_MINUTES")
        or getattr(settings, "TRAVEL_BUFFER_MINUTES", 120)
    )
    daily_limit_h: float = float(
        cfg.get("AVAILABILITY_DAILY_LIMIT_HOURS")
        or getattr(settings, "AVAILABILITY_DAILY_LIMIT_HOURS", 8)
    )

    conflicts: list[Conflict] = []

    # ================================================================
    # RD-02, RD-03: BLOQUEIOS aprovados
    # ================================================================
    blocks = AvailabilityBlock.objects.filter(
        usuario=usuario, status="aprovado"
    ).filter(
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
    events = Solicitacao.objects.filter(usuario=usuario, status="aprovado").filter(
        Q(inicio__lt=fim) & Q(fim__gt=inicio)  # Interseção
    )

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
    prev_ev: Solicitacao | None = (
        Solicitacao.objects.filter(usuario=usuario, status="aprovado", fim__lte=inicio)
        .order_by("-fim")
        .first()
    )

    # Evento imediatamente posterior
    next_ev: Solicitacao | None = (
        Solicitacao.objects.filter(usuario=usuario, status="aprovado", inicio__gte=fim)
        .order_by("inicio")
        .first()
    )

    # Verificar buffer anterior
    if prev_ev:
        # RD-04: municipio=None é tratado como cidade diferente
        # Compara IDs de município. Se um é None e outro não, ou IDs diferentes → requer buffer.
        municipio_id: int | None = municipio.id if municipio else None
        prev_municipio_id: int | None = prev_ev.municipio_id

        prev_diff_city: bool = municipio_id != prev_municipio_id

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
        municipio_id: int | None = municipio.id if municipio else None
        next_municipio_id: int | None = next_ev.municipio_id

        next_diff_city: bool = municipio_id != next_municipio_id

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
    # Buscar eventos aprovados no mesmo dia local do início
    inicio_local: datetime = to_local(inicio)
    inicio_date = inicio_local.date()

    # Seleção ampla: eventos que tocam o dia do início
    same_day_events = Solicitacao.objects.filter(
        usuario=usuario, status="aprovado"
    ).filter(Q(inicio__date=inicio_date) | Q(fim__date=inicio_date))

    # Somar duração dos eventos existentes no dia
    total_minutes: int = 0
    for ev in same_day_events:
        if same_day_local(ev.inicio, inicio) or same_day_local(ev.fim, inicio):
            dur: int = int((ev.fim - ev.inicio).total_seconds() // 60)
            total_minutes += max(dur, 0)

    # Somar duração do novo intervalo
    new_duration: int = int((fim - inicio).total_seconds() // 60)
    total_minutes += new_duration

    # Verificar limite diário
    daily_limit_minutes: int = int(daily_limit_h * 60)
    if total_minutes > daily_limit_minutes:
        conflicts.append(
            Conflict(
                "M",
                "Capacidade diária excedida",
                f"Total do dia {inicio_local:%d/%m}: {total_minutes} min > "
                f"limite {daily_limit_minutes} min ({daily_limit_h}h)",
            )
        )

    # ================================================================
    # RD-07: Retornar todos os conflitos encontrados
    # ================================================================
    return CheckResult(ok=(len(conflicts) == 0), conflicts=conflicts)
