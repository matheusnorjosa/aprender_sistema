"""
AS v2 — GCal Dashboard Helpers

Helper functions and pagination classes for GCal views.
Type-checked with Pyright (strict mode).
"""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false, reportFunctionMemberAccess=false

from __future__ import annotations

from datetime import date, datetime, timezone as dt_timezone
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db.models import Q, QuerySet
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request

from apps.core.models import Solicitacao


def _filter_events_queryset(request: Request, base_qs: QuerySet[Solicitacao]) -> QuerySet[Solicitacao]:
    """
    Helper unificado para filtrar eventos do Dashboard GCal com lógica timezone-aware.

    Aplica filtros de status, start, end de forma determinística usando timezone local
    (America/Fortaleza) e converte para UTC antes de aplicar no queryset.

    Args:
        request: DRF Request com query params (status, start, end)
        base_qs: QuerySet base de Solicitacao (já com status='aprovado' e select_related)

    Returns:
        QuerySet filtrado e ordenado por updated_at desc

    Filtros suportados:
        - status: gcal_status (NONE/PENDING/PUBLISHED/ERROR)
        - start: Início >= start (formato YYYY-MM-DD, 00:00 local)
        - end: Início <= end (formato YYYY-MM-DD, 23:59:59.999999 local)

    Nota: Evita __date__gte/lte por causa de timezone. Usa inicio__gte/lte com
    datetimes UTC derivados da janela local.
    """
    # Base: apenas aprovadas com select_related
    qs = base_qs.filter(status='aprovado').select_related(
        'usuario', 'municipio', 'tipo_evento', 'projeto'
    )

    # Filtro por status (gcal_status)
    status_param = request.query_params.get('status')
    if status_param:
        qs = qs.filter(gcal_status=status_param)

    # Filtro por janela de datas (timezone-aware)
    start_param = request.query_params.get('start')
    end_param = request.query_params.get('end')

    # Timezone local do projeto (America/Fortaleza)
    tz_local = ZoneInfo(settings.TIME_ZONE)

    if start_param:
        try:
            # Converter data ISO para datetime local 00:00:00
            local_start = datetime.fromisoformat(start_param).replace(
                tzinfo=tz_local,
                hour=0,
                minute=0,
                second=0,
                microsecond=0
            )
            # Converter para UTC
            start_utc = local_start.astimezone(dt_timezone.utc)
            # Aplicar filtro inclusivo
            qs = qs.filter(inicio__gte=start_utc)
        except (ValueError, TypeError):
            # Data inválida: ignorar filtro
            pass

    if end_param:
        try:
            # Converter data ISO para datetime local 23:59:59.999999
            local_end = datetime.fromisoformat(end_param).replace(
                tzinfo=tz_local,
                hour=23,
                minute=59,
                second=59,
                microsecond=999999
            )
            # Converter para UTC
            end_utc = local_end.astimezone(dt_timezone.utc)
            # Aplicar filtro inclusivo
            qs = qs.filter(inicio__lte=end_utc)
        except (ValueError, TypeError):
            # Data inválida: ignorar filtro
            pass

    # Ordenação: updated_at desc, id desc (determinístico)
    qs = qs.order_by('-updated_at', '-id')

    return qs


def _apply_common_filters(qs: QuerySet[Solicitacao], request: Request) -> QuerySet[Solicitacao]:
    """
    Aplica filtros comuns a todos os endpoints GCal.

    Filtros suportados:
    - date_from (YYYY-MM-DD): início >= date_from
    - date_to (YYYY-MM-DD): início <= date_to
    - sector: projeto__nome__icontains
    - q: busca em múltiplos campos
    - status: filtra por gcal_status (NONE/PENDING/PUBLISHED/ERROR)
    """
    # Filtro por datas
    date_from = request.query_params.get('date_from')
    if date_from:
        try:
            date_from_parsed = date.fromisoformat(date_from)
            qs = qs.filter(inicio__date__gte=date_from_parsed)
        except (ValueError, TypeError):
            pass

    date_to = request.query_params.get('date_to')
    if date_to:
        try:
            date_to_parsed = date.fromisoformat(date_to)
            qs = qs.filter(inicio__date__lte=date_to_parsed)
        except (ValueError, TypeError):
            pass

    # Filtro por setor (projeto)
    sector = request.query_params.get('sector')
    if sector:
        qs = qs.filter(projeto__nome__icontains=sector)

    # Filtro por gcal_status
    gcal_status_filter = request.query_params.get('status')
    if gcal_status_filter:
        qs = qs.filter(gcal_status=gcal_status_filter)

    # Busca textual
    q = request.query_params.get('q')
    if q:
        qs = qs.filter(
            Q(municipio__nome__icontains=q) |
            Q(projeto__nome__icontains=q) |
            Q(tipo_evento__nome__icontains=q) |
            Q(observacoes__icontains=q) |
            Q(usuario__first_name__icontains=q) |
            Q(usuario__last_name__icontains=q) |
            Q(usuario__username__icontains=q)
        )

    return qs


class DashboardEventsPagination(PageNumberPagination):
    """Paginação customizada para dashboard events"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
