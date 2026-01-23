"""
AS v2 — GCal Dashboard Insights Views

Views for analytics: success rate, top insights.
Type-checked with Pyright (strict mode).
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false, reportFunctionMemberAccess=false

from __future__ import annotations

from typing import Any

from django.db.models import Count, Q
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import Solicitacao
from apps.core.permissions import IsControleOrSuper
from apps.core.views_gcal.helpers import _filter_events_queryset


class SuccessRateView(APIView):
    """
    GET /api/gcal/dashboard/insights/success-rate/?start=&end=

    Retorna taxa de sucesso de publicação GCal (published / (published + error)).

    Query params:
        - start (YYYY-MM-DD, opcional): Filtrar eventos >= start
        - end (YYYY-MM-DD, opcional): Filtrar eventos <= end

    Response 200:
    {
        "published": int,
        "error": int,
        "pending": int,
        "none": int,
        "rate": float,  // 0.0 a 1.0 (round 4 casas)
        "window": { "start": "YYYY-MM-DD" | null, "end": "YYYY-MM-DD" | null }
    }

    Permissions: IsControleOrSuper
    """

    permission_classes = [IsAuthenticated, IsControleOrSuper]

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        # Reutilizar helper TZ-aware
        qs = _filter_events_queryset(request, Solicitacao.objects.all())

        # Contar por gcal_status em uma única query (Issue #308: fix N+1)
        counts = qs.aggregate(
            published=Count("id", filter=Q(gcal_status=Solicitacao.GCalStatus.PUBLISHED)),
            error=Count("id", filter=Q(gcal_status=Solicitacao.GCalStatus.ERROR)),
            pending=Count("id", filter=Q(gcal_status=Solicitacao.GCalStatus.PENDING)),
            none=Count("id", filter=Q(gcal_status=Solicitacao.GCalStatus.NONE)),
        )
        published = counts["published"]
        error = counts["error"]
        pending = counts["pending"]
        none = counts["none"]

        # Calcular rate (apenas published e error contam como "tentativas")
        denom = published + error
        rate = 0.0 if denom == 0 else round(published / denom, 4)

        # Extrair janela
        start_param = request.query_params.get("start")
        end_param = request.query_params.get("end")

        return Response(
            {
                "published": published,
                "error": error,
                "pending": pending,
                "none": none,
                "rate": rate,
                "window": {"start": start_param if start_param else None, "end": end_param if end_param else None},
            },
            status=status.HTTP_200_OK,
        )


class TopInsightsView(APIView):
    """
    GET /api/gcal/dashboard/insights/top/?metric=municipios|projetos&start=&end=&limit=5

    Retorna top N municípios ou projetos por contagem de erros/eventos.

    Query params:
        - metric: "municipios" ou "projetos" (aceita aliases "municipio", "projeto")
        - start, end: janela de datas (opcional)
        - limit: número de resultados (default 5, min 1, max 20)

    Response 200:
    {
        "items": [
            {
                "name": "Fortaleza - CE",
                "count": 14,
                "published": 12,
                "error": 2,
                "rate": 0.8571
            },
            ...
        ],
        "window": { "start": "YYYY-MM-DD" | null, "end": "YYYY-MM-DD" | null },
        "metric": "municipios" | "projetos",
        "limit": 5
    }

    Response 400: metric inválido

    Permissions: IsControleOrSuper
    Ordenação: -error, -count
    """

    permission_classes = [IsAuthenticated, IsControleOrSuper]

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        # Validar metric
        metric_param = request.query_params.get("metric", "").lower()
        if metric_param in ("municipios", "municipio"):
            group_field = "municipio__nome"
            metric = "municipios"
        elif metric_param in ("projetos", "projeto"):
            group_field = "projeto__nome"
            metric = "projetos"
        else:
            return Response(
                {"detail": f'Parâmetro "metric" inválido: {metric_param}. Use "municipios" ou "projetos".'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validar limit
        try:
            limit = int(request.query_params.get("limit", 5))
            limit = max(1, min(20, limit))  # clamp entre 1 e 20
        except ValueError:
            limit = 5

        # Reutilizar helper TZ-aware
        qs = _filter_events_queryset(request, Solicitacao.objects.all())

        # Aggregations
        items_qs = (
            qs.values(group_field)
            .annotate(
                count=Count("id"),
                published=Count("id", filter=Q(gcal_status=Solicitacao.GCalStatus.PUBLISHED)),
                error=Count("id", filter=Q(gcal_status=Solicitacao.GCalStatus.ERROR)),
            )
            .order_by("-error", "-count")[:limit]
        )

        # Formatar items com rate
        items = []
        for item in items_qs:
            pub = item["published"]
            err = item["error"]
            denom = pub + err
            rate = 0.0 if denom == 0 else round(pub / denom, 4)

            items.append(
                {"name": item[group_field] or "—", "count": item["count"], "published": pub, "error": err, "rate": rate}
            )

        # Extrair janela
        start_param = request.query_params.get("start")
        end_param = request.query_params.get("end")

        return Response(
            {
                "items": items,
                "window": {"start": start_param if start_param else None, "end": end_param if end_param else None},
                "metric": metric,
                "limit": limit,
            },
            status=status.HTTP_200_OK,
        )
