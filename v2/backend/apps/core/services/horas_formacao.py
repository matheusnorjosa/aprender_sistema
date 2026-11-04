"""
Horas de formação (CH) por pessoa e por dia — decisão do dono, 02/10 e 05/10/2026.

SSOT da contagem usada pela Grade Mensal e pelo painel de Equipe:

- CH de um evento para uma pessoa = min(fim − início, TETO). TETO = o parâmetro de
  Configurações `AVAILABILITY_DAILY_LIMIT_HOURS` ("Teto de horas por evento", padrão 8 h).
- As CH do dia se somam: não há teto por dia (5 h + 5 h = 10 h).
- O evento conta inteiro no dia local (America/Fortaleza) do INÍCIO, mesmo cruzando a
  meia-noite. Sem desconto de almoço. Online conta igual.
- Só evento aprovado, de qualquer projeto ou gerência.
- Conta sempre quem ocupa a agenda pelo papel (`ENFORCED_ROLES`: FORMADOR e, desde 03/11/2026,
  COORD_ACOMPANHA, o coordenador além do responsável); o coordenador responsável (`coordenador`;
  sem ele, quem criou) só quando `coordenador_acompanha=True`. Convidado não conta.
  A mesma pessoa conta uma vez por evento.
"""

# pyright: reportAttributeAccessIssue=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db.models import Q

from apps.core.models import Participation, Solicitacao
from apps.core.services.availability_service import ENFORCED_ROLES, to_local
from apps.core.services.config_service import parametros_disponibilidade


@dataclass(frozen=True)
class HorasFormacao:
    """CH de uma pessoa no período: por dia local do início do evento e o total."""

    por_dia: dict[date, float]
    total: float


@dataclass(frozen=True)
class Ocupacao:
    """Um evento aprovado que conta para uma pessoa (CH, ranking): início, fim e município."""

    inicio: datetime
    fim: datetime
    municipio_id: int | None


def ocupacoes_aprovadas(
    *, de: date, ate: date, usuario_ids: Iterable[int] | None = None
) -> dict[tuple[int, int], Ocupacao]:
    """
    (pessoa, evento) → `Ocupacao`: os eventos aprovados com início nos dias locais `de`..`ate`
    (inclusive) que contam para a pessoa. SSOT da população da CH e do ranking de formadores.

    Conta `ENFORCED_ROLES` sempre e o coordenador responsável (`coordenador`; sem ele, quem criou)
    só com `coordenador_acompanha=True`. A chave (pessoa, evento) deduplica quem está em dois papéis.
    `usuario_ids=None` = todas as pessoas. Duas consultas (sem N+1).
    """
    tz = ZoneInfo(str(getattr(settings, "TZ_PROJECT", "America/Fortaleza")))
    janela_inicio = datetime.combine(de, time.min, tzinfo=tz)
    janela_fim = datetime.combine(ate + timedelta(days=1), time.min, tzinfo=tz)

    formadores = Participation.objects.filter(
        role__in=ENFORCED_ROLES,
        usuario__isnull=False,
        solicitacao__status=Solicitacao.Status.APROVADO,
        solicitacao__inicio__gte=janela_inicio,
        solicitacao__inicio__lt=janela_fim,
    )
    acompanhados = Solicitacao.objects.filter(
        status=Solicitacao.Status.APROVADO,
        coordenador_acompanha=True,
        inicio__gte=janela_inicio,
        inicio__lt=janela_fim,
    )
    if usuario_ids is not None:
        ids = set(usuario_ids)
        if not ids:
            return {}
        formadores = formadores.filter(usuario_id__in=ids)
        acompanhados = acompanhados.filter(Q(coordenador_id__in=ids) | Q(coordenador__isnull=True, usuario_id__in=ids))

    ocupacoes: dict[tuple[int, int], Ocupacao] = {}
    for uid, sol_id, inicio, fim, municipio_id in formadores.values_list(
        "usuario_id", "solicitacao_id", "solicitacao__inicio", "solicitacao__fim", "solicitacao__municipio_id"
    ):
        ocupacoes[(uid, sol_id)] = Ocupacao(inicio, fim, municipio_id)
    for sol_id, inicio, fim, municipio_id, coordenador_id, criador_id in acompanhados.values_list(
        "id", "inicio", "fim", "municipio_id", "coordenador_id", "usuario_id"
    ):
        responsavel = coordenador_id if coordenador_id is not None else criador_id
        ocupacoes[(responsavel, sol_id)] = Ocupacao(inicio, fim, municipio_id)
    return ocupacoes


def horas_formacao(usuario_ids: Iterable[int], *, de: date, ate: date) -> dict[int, HorasFormacao]:
    """
    CH por pessoa entre os dias locais `de` e `ate` (inclusive), pelo início do evento.

    Duas consultas para qualquer número de pessoas (sem N+1). Toda pessoa pedida volta no
    resultado, com zero quando não tem evento.
    """
    ids = set(usuario_ids)
    teto_segundos = int(parametros_disponibilidade()["AVAILABILITY_DAILY_LIMIT_HOURS"]) * 3600
    eventos = ocupacoes_aprovadas(de=de, ate=ate, usuario_ids=ids)

    segundos: dict[int, dict[date, int]] = defaultdict(lambda: defaultdict(int))
    for (uid, _sol_id), ocupacao in eventos.items():
        duracao = int((ocupacao.fim - ocupacao.inicio).total_seconds())
        segundos[uid][to_local(ocupacao.inicio).date()] += min(max(duracao, 0), teto_segundos)

    resultado: dict[int, HorasFormacao] = {}
    for uid in ids:
        por_dia = {dia: s / 3600 for dia, s in sorted(segundos[uid].items())}
        resultado[uid] = HorasFormacao(por_dia=por_dia, total=sum(segundos[uid].values()) / 3600)
    return resultado
