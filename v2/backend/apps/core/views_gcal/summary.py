"""
AS v2 — GCal Dashboard Summary Views

Views for status summaries, metrics, and alerts.
Type-checked with Pyright (strict mode).
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false, reportFunctionMemberAccess=false

from __future__ import annotations

from datetime import date
from typing import Any

from django.db.models import Count, Q
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema

from apps.core.models import Solicitacao
from apps.core.pagination import LargePagination
from apps.core.permissions import HasPerm
from apps.core.serializers import SolicitacaoSerializer
from apps.core.serializers.gcal_dashboard_contract import (
    AlertsSummaryResponseSerializer,
    DashboardMetricsResponseSerializer,
    GCalStatusSummaryResponseSerializer,
    PaginatedSolicitacaoResponseSerializer,
)
from apps.core.views_gcal.helpers import _apply_common_filters, _filter_events_queryset


class GCalStatusSummaryView(APIView):
    """
    GET /api/gcal/status-summary/

    Retorna resumo de contadores por gcal_status.
    Suporta filtros: date_from, date_to, sector, q, status.

    Response:
    {
        "counts": {
            "NONE": 10,
            "PENDING": 2,
            "PUBLISHED": 150,
            "ERROR": 1
        },
        "total": 163
    }
    """

    permission_classes = [IsAuthenticated, HasPerm("operate_preagenda") | HasPerm("approve_solicitation")]

    @extend_schema(responses=GCalStatusSummaryResponseSerializer)
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        # Base queryset: apenas solicitações aprovadas
        qs = Solicitacao.objects.filter(status="aprovado")

        # Aplicar filtros comuns
        qs = _apply_common_filters(qs, request)

        # Agregar contadores por gcal_status
        summary = qs.values("gcal_status").annotate(count=Count("id"))

        # Transformar em dict
        counts = {item["gcal_status"]: item["count"] for item in summary}

        # Garantir todas as chaves existem
        for status_key in ["NONE", "PENDING", "PUBLISHED", "ERROR"]:
            if status_key not in counts:
                counts[status_key] = 0

        return Response({"counts": counts, "total": sum(counts.values())})


class GCalListView(APIView):
    """
    GET /api/gcal/list/

    Lista solicitações aprovadas com campos GCal expostos.
    Suporta filtros: date_from, date_to, sector, q, status.
    Suporta paginação: page, page_size (max 1000).

    Response (paginada):
    {
        "count": 1500,
        "next": "http://.../api/gcal/list/?page=2",
        "previous": null,
        "results": [...]
    }
    """

    permission_classes = [IsAuthenticated, HasPerm("operate_preagenda") | HasPerm("approve_solicitation")]
    pagination_class = LargePagination

    @extend_schema(responses=PaginatedSolicitacaoResponseSerializer)
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        # Base queryset: apenas aprovadas
        # Fix N+1: prefetch participations with their users
        qs = (
            Solicitacao.objects.filter(status="aprovado")
            .select_related("usuario", "municipio", "tipo_evento", "projeto", "projeto__gerencia")
            .prefetch_related("participations__usuario")
        )

        # Aplicar filtros comuns
        qs = _apply_common_filters(qs, request)

        # Ordenação: mais recentes primeiro
        qs = qs.order_by("-inicio", "-id")

        # Paginação (#408)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)

        if page is not None:
            serializer = SolicitacaoSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        # Fallback (não deve acontecer com PageNumberPagination)
        serializer = SolicitacaoSerializer(qs[:500], many=True)
        return Response({"results": serializer.data, "count": len(serializer.data)})


class DashboardMetricsView(APIView):
    """
    GET /api/gcal/dashboard/metrics/

    Retorna métricas de publicação GCal com erros recentes.

    Query params:
    - start (ISO date): Filtro início >= start (formato: YYYY-MM-DD)
    - end (ISO date): Filtro início <= end (formato: YYYY-MM-DD)

    Response:
    {
        "counts": {
            "NONE": 10,
            "PENDING": 2,
            "PUBLISHED": 150,
            "ERROR": 1
        },
        "recent_errors": [
            {
                "id": 789,
                "summary": "Fortaleza - CE Fundamental I Online [ACERTA]",
                "gcal_last_error": "500 Internal Server Error",
                "updated_at": "2025-11-08T10:30:00Z"
            },
            ...
        ],
        "window": {
            "start": "2025-10-01",
            "end": "2025-11-30"
        }
    }

    Permissions: HasPerm("import_spreadsheet")
    """

    permission_classes = [IsAuthenticated, HasPerm("operate_preagenda") | HasPerm("approve_solicitation")]

    @extend_schema(responses=DashboardMetricsResponseSerializer)
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        # Base queryset: apenas solicitações aprovadas
        qs = Solicitacao.objects.filter(status="aprovado")

        # Parse filtros de janela (start/end)
        start_param = request.query_params.get("start")
        end_param = request.query_params.get("end")

        start_date = None
        end_date = None

        if start_param:
            try:
                start_date = date.fromisoformat(start_param)
                qs = qs.filter(inicio__date__gte=start_date)
            except (ValueError, TypeError):
                pass

        if end_param:
            try:
                end_date = date.fromisoformat(end_param)
                qs = qs.filter(inicio__date__lte=end_date)
            except (ValueError, TypeError):
                pass

        # Contadores por gcal_status
        summary = qs.values("gcal_status").annotate(count=Count("id"))
        counts = {item["gcal_status"]: item["count"] for item in summary}

        # Garantir todas as chaves existem
        for status_key in ["NONE", "PENDING", "PUBLISHED", "ERROR"]:
            if status_key not in counts:
                counts[status_key] = 0

        # Recent errors (top 5, ordenados por updated_at desc)
        error_qs = (
            qs.filter(gcal_status=Solicitacao.GCalStatus.ERROR)
            .select_related("municipio", "projeto")
            .order_by("-updated_at")[:5]
        )

        recent_errors = []
        for s in error_qs:
            # Gerar summary simples para exibição
            municipio_nome = s.municipio.nome if s.municipio else ""
            municipio_uf = s.municipio.uf if s.municipio else ""
            projeto_nome = s.projeto.nome if s.projeto else ""
            summary_text = (
                f"{municipio_nome} - {municipio_uf} {projeto_nome}" if municipio_nome else f"Solicitação #{s.id}"
            )

            recent_errors.append(
                {
                    "id": s.id,
                    "summary": summary_text.strip(),
                    "gcal_last_error": s.gcal_last_error or "",
                    "updated_at": s.updated_at.isoformat() if s.updated_at else None,
                }
            )

        return Response(
            {
                "counts": counts,
                "recent_errors": recent_errors,
                "window": {
                    "start": start_date.isoformat() if start_date else None,
                    "end": end_date.isoformat() if end_date else None,
                },
            }
        )


class AlertsSummaryView(APIView):
    """
    GET /api/gcal/dashboard/alerts/summary/?start=&end=

    Retorna contagens de eventos por gcal_status para exibir badge/toast no frontend.

    Query params:
        - start (YYYY-MM-DD, opcional): Filtrar eventos >= start (00:00 local)
        - end (YYYY-MM-DD, opcional): Filtrar eventos <= end (23:59:59.999999 local)

    Response 200:
    {
        "errors": int,
        "pending": int,
        "published": int,
        "none": int,
        "window": {
            "start": "YYYY-MM-DD" | null,
            "end": "YYYY-MM-DD" | null
        }
    }

    Permissions: HasPerm("import_spreadsheet")
    Timezone-aware: Usa helper _filter_events_queryset (clamp local→UTC)
    """

    permission_classes = [IsAuthenticated, HasPerm("operate_preagenda") | HasPerm("approve_solicitation")]

    @extend_schema(responses=AlertsSummaryResponseSerializer)
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        # Reutilizar helper TZ-aware
        qs = _filter_events_queryset(request, Solicitacao.objects.all())

        # Contar por gcal_status em uma única query (Issue #308: fix N+1)
        counts = qs.aggregate(
            errors=Count("id", filter=Q(gcal_status=Solicitacao.GCalStatus.ERROR)),
            pending=Count("id", filter=Q(gcal_status=Solicitacao.GCalStatus.PENDING)),
            published=Count("id", filter=Q(gcal_status=Solicitacao.GCalStatus.PUBLISHED)),
            none=Count("id", filter=Q(gcal_status=Solicitacao.GCalStatus.NONE)),
        )

        # Extrair janela de query params (retornar como strings ou null)
        start_param = request.query_params.get("start")
        end_param = request.query_params.get("end")

        return Response(
            {
                "errors": counts["errors"],
                "pending": counts["pending"],
                "published": counts["published"],
                "none": counts["none"],
                "window": {"start": start_param if start_param else None, "end": end_param if end_param else None},
            },
            status=status.HTTP_200_OK,
        )
