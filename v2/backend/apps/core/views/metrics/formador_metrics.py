"""
Formador Metrics Views - §9 Epic #459

Formadores ranking and performance metrics.
Extracted from views_metrics.py.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false

from __future__ import annotations

from datetime import datetime, time, timedelta

from django.db.models import Count
from django.utils import timezone
from rest_framework import status as http_status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.core.models import Participation
from apps.core.permissions import HasPerm
from apps.core.services.horas_formacao import horas_formacao


@api_view(["GET"])
@permission_classes(
    # Onda 2 A3 (β, 2026-04-27): adicionado `manage_admin_registries` para DAT
    # como ator transversal (validar/suportar). Mesma decisão dos demais
    # endpoints metrics — preserva Lote 4.2.b2 (composition OR ad-hoc por
    # objetos semanticamente diferentes). Ver ADR-019 (v2/docs/adr/ADR-019-metrics-composition-or.md).
    [HasPerm("run_daily_operations") | HasPerm("supervise_operations") | HasPerm("manage_admin_registries")]
)
@throttle_classes([ScopedRateThrottle])
def formadores_metrics(request: Request) -> Response:
    """
    Formadores ranking by performance (top 10) (Issue #189).

    Query params:
        days (int): Number of days to look back (default: 30)

    Returns:
        {
            "period": "30d",
            "formadores": [
                {
                    "id": 1,
                    "nome": "João Silva",
                    "eventos": 45,
                    "horas_trabalhadas": 180.0,
                    "municipios_atendidos": 12
                },
                ...
            ]
        }

    Calculations:
        - Filter Participation by role=FORMADOR and solicitacao__status=aprovado, events
          whose local start date is in [today - days, today]
        - Aggregate by usuario: count events, count distinct municipios
        - horas_trabalhadas: services/horas_formacao.py (teto por evento, mesma conta da
          Grade Mensal)
        - Order by -eventos, limit to top 10

    Permissions: HasPerm("run_daily_operations") | HasPerm("supervise_operations") (only authorized users)
    """
    days = int(request.GET.get("days", 30))
    # Período = dias locais [hoje − days, hoje], pelo INÍCIO do evento (antes filtrava
    # `created_at`, e um evento antigo importado hoje entrava como hora do período).
    ate = timezone.localdate()
    de = ate - timedelta(days=days)
    tz = timezone.get_current_timezone()
    janela_inicio = datetime.combine(de, time.min, tzinfo=tz)
    janela_fim = datetime.combine(ate + timedelta(days=1), time.min, tzinfo=tz)

    # Query participations (formador role only, approved events only, in date range)
    participations = Participation.objects.filter(
        role=Participation.Role.FORMADOR,
        solicitacao__status="aprovado",
        solicitacao__inicio__gte=janela_inicio,
        solicitacao__inicio__lt=janela_fim,
        usuario__isnull=False,  # Exclude guest participations
    )

    # Aggregate by usuario — include username to avoid N+1 fallback (#781)
    formadores_stats = (
        participations.values(
            "usuario_id",
            "usuario__first_name",
            "usuario__last_name",
            "usuario__username",
        )
        .annotate(
            eventos=Count("solicitacao_id", distinct=True),
            municipios_atendidos=Count("solicitacao__municipio_id", distinct=True),
        )
        .order_by("-eventos")[:10]
    )

    # Horas = a contagem única de horas de formação (teto por evento), a mesma da Grade
    # Mensal: duas consultas para os 10, sem N+1.
    formadores_stats = list(formadores_stats)
    horas_por_pessoa = horas_formacao([stat["usuario_id"] for stat in formadores_stats], de=de, ate=ate)

    formadores_list = []
    for stat in formadores_stats:
        horas = round(horas_por_pessoa[stat["usuario_id"]].total, 1)

        # Build full name — use username from same query as fallback
        nome = f"{stat['usuario__first_name']} {stat['usuario__last_name']}".strip()
        if not nome:
            nome = stat["usuario__username"] or f"Usuário #{stat['usuario_id']}"

        formadores_list.append(
            {
                "id": stat["usuario_id"],
                "nome": nome,
                "eventos": stat["eventos"],
                "horas_trabalhadas": horas,
                "municipios_atendidos": stat["municipios_atendidos"],
            }
        )

    return Response(
        {"period": f"{days}d", "formadores": formadores_list},
        status=http_status.HTTP_200_OK,
    )


# Throttle scope for formadores_metrics (#409)
formadores_metrics.throttle_scope = "metrics"  # type: ignore[attr-defined]
