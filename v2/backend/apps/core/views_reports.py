"""
Reports API Views

Provides analytical reports for decision-making.
"""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false

from __future__ import annotations
from typing import Any
from django.db.models import QuerySet
from rest_framework.request import Request
from rest_framework.response import Response

from datetime import datetime, timedelta

from django.core.cache import cache
from django.db.models import Count
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import Solicitacao
from .permissions import IsControleOrDAT


@api_view(["GET"])
@permission_classes([IsControleOrDAT])
def reports_status_counts(request: Request) -> Response:
    """
    GET /api/reports/status-counts/

    Retorna contagem de solicitações por status em um intervalo de datas.

    Query parameters:
    - start: data inicial (YYYY-MM-DD), default: 30 dias atrás
    - end: data final (YYYY-MM-DD), default: hoje

    Response:
    {
        "pendente": 10,
        "aprovado": 50,
        "reprovado": 5,
        "total": 65,
        "period": {"start": "2025-01-01", "end": "2025-01-31"}
    }

    Permissions: IsControleOrSuper
    """
    # Parse dates
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)

    start_param = request.query_params.get("start")
    end_param = request.query_params.get("end")

    if start_param:
        try:
            start_date = datetime.strptime(start_param, "%Y-%m-%d").date()
        except ValueError:
            return Response(
                {"detail": "start deve estar no formato YYYY-MM-DD"},
                status=400
            )

    if end_param:
        try:
            end_date = datetime.strptime(end_param, "%Y-%m-%d").date()
        except ValueError:
            return Response(
                {"detail": "end deve estar no formato YYYY-MM-DD"},
                status=400
            )

    if end_date < start_date:
        return Response(
            {"detail": "end deve ser posterior ou igual a start"},
            status=400
        )

    # Generate cache key
    cache_key = f"reports:status_counts:{start_date}:{end_date}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return Response(cached_result)

    # Query - filtrar por data do evento (inicio), não por created_at
    queryset = Solicitacao.objects.filter(
        inicio__date__gte=start_date,
        inicio__date__lte=end_date
    )

    counts = queryset.values("status").annotate(count=Count("id"))
    counts_dict = {item["status"]: item["count"] for item in counts}

    result = {
        "range": {
            "start": str(start_date),
            "end": str(end_date)
        },
        "counts": {
            "pendente": counts_dict.get("pendente", 0),
            "aprovado": counts_dict.get("aprovado", 0),
            "reprovado": counts_dict.get("reprovado", 0),
            "publicado": counts_dict.get("publicado", 0),
        },
        "total": queryset.count(),
    }

    # Cache for 5 minutes
    cache.set(cache_key, result, 300)

    return Response(result)


@api_view(["GET"])
@permission_classes([IsControleOrDAT])
def reports_top_projects(request: Request) -> Response:
    """
    GET /api/reports/top-projects/

    Retorna ranking de projetos por quantidade de solicitações (últimos 30 dias).

    Query parameters:
    - limit: quantidade de projetos no ranking (default: 10, max: 50)

    Response:
    {
        "projects": [
            {"projeto": "Projeto A", "count": 50, "rank": 1},
            {"projeto": "Projeto B", "count": 30, "rank": 2},
            ...
        ],
        "limit": 10
    }

    Permissions: IsControleOrSuper
    """
    limit = 5  # Default is 5
    limit_param = request.query_params.get("limit")

    if limit_param:
        try:
            limit = int(limit_param)
            if limit < 1 or limit > 20:
                return Response(
                    {"detail": "limit deve estar entre 1 e 20"},
                    status=400
                )
        except (ValueError, TypeError):
            return Response(
                {"detail": "limit deve ser um número inteiro"},
                status=400
            )

    # Filter by last 30 days (consistent with other reports)
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)

    # Query - filtrar por data do evento (inicio)
    top_projects = (
        Solicitacao.objects
        .filter(inicio__date__gte=start_date, inicio__date__lte=end_date)
        .exclude(projeto__isnull=True)
        .values("projeto__nome")
        .annotate(count=Count("id"))
        .order_by("-count")[:limit]
    )

    # Format with ranking
    items_list = [
        {
            "projeto": item["projeto__nome"],
            "count": item["count"],
            "rank": idx + 1
        }
        for idx, item in enumerate(top_projects)
    ]

    return Response({
        "range": {"limit": limit},
        "items": items_list
    })


@api_view(["GET"])
@permission_classes([IsControleOrDAT])
def reports_weekly_approved(request: Request) -> Response:
    """
    GET /api/reports/weekly-approved/

    Retorna quantidade de solicitações aprovadas por semana.

    Query parameters:
    - weeks: número de semanas no histórico (default: 4, max: 52)

    Response:
    {
        "weeks": [
            {"week": "2025-W01", "count": 15, "start_date": "2025-01-01"},
            {"week": "2025-W02", "count": 20, "start_date": "2025-01-08"},
            ...
        ],
        "total": 35,
        "weeks_count": 4
    }

    Permissions: IsControleOrSuper
    """
    weeks = 12  # Default is 12
    weeks_param = request.query_params.get("weeks")

    if weeks_param:
        try:
            weeks = int(weeks_param)
            if weeks < 1 or weeks > 52:
                return Response(
                    {"detail": "weeks deve estar entre 1 e 52"},
                    status=400
                )
        except (ValueError, TypeError):
            return Response(
                {"detail": "weeks deve ser um número inteiro"},
                status=400
            )

    # Calculate date range
    end_date = timezone.now().date()
    start_date = end_date - timedelta(weeks=weeks)

    # Query only approved - filtrar por data do evento (inicio)
    queryset = Solicitacao.objects.filter(
        status="aprovado",
        inicio__date__gte=start_date,
        inicio__date__lte=end_date
    )

    # Se não há nenhuma solicitação aprovada, retornar array vazio
    if queryset.count() == 0:
        return Response({
            "weeks": weeks,
            "series": [],
        })

    # Group by week (simplified - use created_at week)
    weeks_data = []
    current_date = start_date

    while current_date <= end_date:
        week_end = current_date + timedelta(days=6)
        if week_end > end_date:
            week_end = end_date

        week_count = queryset.filter(
            inicio__date__gte=current_date,
            inicio__date__lte=week_end
        ).count()

        weeks_data.append({
            "week": f"{current_date.year}-W{current_date.isocalendar()[1]:02d}",
            "count": week_count,
            "start_date": str(current_date)
        })

        current_date = week_end + timedelta(days=1)

    return Response({
        "weeks": weeks,
        "series": weeks_data[-weeks:],  # Last N weeks
    })


@api_view(["GET"])
@permission_classes([IsControleOrDAT])
def reports_by_uf(request: Request) -> Response:
    """
    GET /api/reports/by-uf/

    Retorna distribuição de solicitações por UF (últimos 30 dias por padrão).

    Response:
    {
        "range": {},
        "items": [
            {"uf": "CE", "count": 100},
            {"uf": "SP", "count": 80},
            ...
        ]
    }

    Permissions: IsControleOrDAT
    """
    # Default: últimos 30 dias
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)

    # Query aggregated by UF (últimos 30 dias)
    by_uf = (
        Solicitacao.objects
        .filter(inicio__date__gte=start_date, inicio__date__lte=end_date)
        .exclude(municipio__isnull=True)
        .values("municipio__uf")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    items_list = [
        {"uf": item["municipio__uf"], "count": item["count"]}
        for item in by_uf
    ]

    return Response({
        "range": {},
        "items": items_list,
    })
