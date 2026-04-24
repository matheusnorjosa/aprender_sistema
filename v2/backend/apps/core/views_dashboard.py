"""
AS v2 - Dashboard Overview API

Endpoint consolidado para métricas do dashboard principal.
Ref: Issue #311
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false

from __future__ import annotations

from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema

from apps.core.permissions import HasPerm
from apps.core.serializers.gcal_dashboard_contract import DashboardOverviewResponseSerializer


@extend_schema(
    responses=DashboardOverviewResponseSerializer,
    tags=["Dashboard"],
)
@api_view(["GET"])
@permission_classes([HasPerm("view_overview_dashboard")])
def dashboard_overview(request: Request) -> Response:
    """
    GET /api/dashboard/overview/

    Retorna métricas consolidadas para o dashboard principal.

    Response:
    {
        "kpis": {
            "eventos_futuros": int,
            "eventos_aprovados": int,
            "total_participantes": int,
            "aprovacoes_pendentes": int
        },
        "por_fluxo": [
            {"fluxo": "SUPER", "quantidade": int},
            {"fluxo": "NAO_SUPER", "quantidade": int}
        ],
        "por_gerencia": [
            {"gerencia": str, "quantidade": int, "porcentagem": float},
            ...
        ],
        "top_coordenadores": [
            {"nome": str, "eventos": int},
            ...
        ]
    }

    Permissions: HasPerm("view_overview_dashboard")
    """
    from .models import Participation, Solicitacao

    now = timezone.now()
    hoje = now.date()

    # Base querysets
    qs_all = Solicitacao.objects.all()
    qs_aprovadas = qs_all.filter(status="aprovado")

    # KPIs
    eventos_futuros = qs_aprovadas.filter(inicio__date__gte=hoje).count()
    eventos_aprovados = qs_aprovadas.count()

    # Total formadores distintos em solicitações aprovadas (fix #594)
    total_formadores = (
        Participation.objects.filter(solicitacao__status="aprovado", usuario__isnull=False)
        .values("usuario_id")
        .distinct()
        .count()
    )

    aprovacoes_pendentes = qs_all.filter(status="pendente").count()

    kpis = {
        "eventos_futuros": eventos_futuros,
        "eventos_aprovados": eventos_aprovados,
        "total_formadores": total_formadores,
        "aprovacoes_pendentes": aprovacoes_pendentes,
    }

    # Por Fluxo (últimos 30 dias)
    start_30d = hoje - timedelta(days=30)
    qs_30d = qs_aprovadas.filter(inicio__date__gte=start_30d)

    por_fluxo_raw = (
        qs_30d.exclude(projeto__isnull=True)
        .values("projeto__fluxo")
        .annotate(quantidade=Count("id"))
        .order_by("-quantidade")
    )

    por_fluxo = [
        {
            "fluxo": item["projeto__fluxo"] or "N/A",
            "quantidade": item["quantidade"],
        }
        for item in por_fluxo_raw
    ]

    # Por Gerência (últimos 30 dias)
    por_gerencia_raw = (
        qs_30d.exclude(projeto__gerencia__isnull=True)
        .values("projeto__gerencia__nome")
        .annotate(quantidade=Count("id"))
        .order_by("-quantidade")
    )

    total_gerencia = sum(item["quantidade"] for item in por_gerencia_raw)

    por_gerencia = [
        {
            "gerencia": item["projeto__gerencia__nome"] or "Sem Gerência",
            "quantidade": item["quantidade"],
            "porcentagem": round((item["quantidade"] / total_gerencia * 100) if total_gerencia > 0 else 0, 1),
        }
        for item in por_gerencia_raw[:5]  # Top 5
    ]

    # Top Coordenadores (por eventos criados nos últimos 30 dias)
    top_coord_raw = (
        qs_30d.exclude(usuario__isnull=True)
        .values("usuario__first_name", "usuario__last_name", "usuario__username")
        .annotate(eventos=Count("id"))
        .order_by("-eventos")[:5]
    )

    top_coordenadores = []
    for item in top_coord_raw:
        first = item["usuario__first_name"] or ""
        last = item["usuario__last_name"] or ""
        nome_completo = f"{first} {last}".strip()
        top_coordenadores.append(
            {
                "nome": nome_completo or item["usuario__username"],
                "eventos": item["eventos"],
            }
        )

    return Response(
        {
            "kpis": kpis,
            "por_fluxo": por_fluxo,
            "por_gerencia": por_gerencia,
            "top_coordenadores": top_coordenadores,
        }
    )
