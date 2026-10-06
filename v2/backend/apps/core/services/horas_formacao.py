"""
Horas de formação (CH) por pessoa e por dia — decisão do dono, 02/10 e 05/10/2026.

SSOT da contagem usada pela Grade Mensal e pelo painel de Equipe:

- CH de um evento para uma pessoa = min(fim − início, TETO). TETO = o parâmetro de
  Configurações `AVAILABILITY_DAILY_LIMIT_HOURS` ("Teto de horas por evento", padrão 8 h).
- As CH do dia se somam: não há teto por dia (5 h + 5 h = 10 h).
- O evento conta inteiro no dia local (America/Fortaleza) do INÍCIO, mesmo cruzando a
  meia-noite. Sem desconto de almoço. Online conta igual.
- Só evento aprovado, de qualquer projeto ou gerência.
- Conta o participante FORMADOR sempre; o coordenador responsável (`coordenador`; sem ele,
  quem criou) só quando `coordenador_acompanha=True`. COORD_ACOMPANHA e convidado não contam.
  A mesma pessoa conta uma vez por evento.
"""

# pyright: reportAttributeAccessIssue=false, reportUnknownMemberType=false, reportUnknownVariableType=false

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db.models import Q

from apps.core.models import Participation, Solicitacao
from apps.core.services.availability_service import to_local
from apps.core.services.config_service import parametros_disponibilidade


@dataclass(frozen=True)
class HorasFormacao:
    """CH de uma pessoa no período: por dia local do início do evento e o total."""

    por_dia: dict[date, float]
    total: float


def horas_formacao(usuario_ids: Iterable[int], *, de: date, ate: date) -> dict[int, HorasFormacao]:
    """
    CH por pessoa entre os dias locais `de` e `ate` (inclusive), pelo início do evento.

    Duas consultas para qualquer número de pessoas (sem N+1). Toda pessoa pedida volta no
    resultado, com zero quando não tem evento.
    """
    ids = set(usuario_ids)
    teto_segundos = int(parametros_disponibilidade()["AVAILABILITY_DAILY_LIMIT_HOURS"]) * 3600
    tz = ZoneInfo(str(getattr(settings, "TZ_PROJECT", "America/Fortaleza")))
    janela_inicio = datetime.combine(de, time.min, tzinfo=tz)
    janela_fim = datetime.combine(ate + timedelta(days=1), time.min, tzinfo=tz)

    # (pessoa, evento) → (início, fim): o set de chaves deduplica quem é formador e também
    # responsável que acompanha no mesmo evento.
    eventos: dict[tuple[int, int], tuple[datetime, datetime]] = {}
    if ids:
        formadores = Participation.objects.filter(
            role=Participation.Role.FORMADOR,
            usuario_id__in=ids,
            solicitacao__status=Solicitacao.Status.APROVADO,
            solicitacao__inicio__gte=janela_inicio,
            solicitacao__inicio__lt=janela_fim,
        ).values_list("usuario_id", "solicitacao_id", "solicitacao__inicio", "solicitacao__fim")
        for uid, sol_id, inicio, fim in formadores:
            eventos[(uid, sol_id)] = (inicio, fim)

        acompanhados = (
            Solicitacao.objects.filter(
                status=Solicitacao.Status.APROVADO,
                coordenador_acompanha=True,
                inicio__gte=janela_inicio,
                inicio__lt=janela_fim,
            )
            .filter(Q(coordenador_id__in=ids) | Q(coordenador__isnull=True, usuario_id__in=ids))
            .values_list("id", "inicio", "fim", "coordenador_id", "usuario_id")
        )
        for sol_id, inicio, fim, coordenador_id, criador_id in acompanhados:
            responsavel = coordenador_id if coordenador_id is not None else criador_id
            eventos[(responsavel, sol_id)] = (inicio, fim)

    segundos: dict[int, dict[date, int]] = defaultdict(lambda: defaultdict(int))
    for (uid, _sol_id), (inicio, fim) in eventos.items():
        duracao = int((fim - inicio).total_seconds())
        segundos[uid][to_local(inicio).date()] += min(max(duracao, 0), teto_segundos)

    resultado: dict[int, HorasFormacao] = {}
    for uid in ids:
        por_dia = {dia: s / 3600 for dia, s in sorted(segundos[uid].items())}
        resultado[uid] = HorasFormacao(por_dia=por_dia, total=sum(segundos[uid].values()) / 3600)
    return resultado
