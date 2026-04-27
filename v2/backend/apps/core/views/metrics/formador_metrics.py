"""
Formador Metrics Views - §9 Epic #459

Formadores ranking and performance metrics.
Extracted from views_metrics.py.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false

from __future__ import annotations

from datetime import timedelta

from django.db.models import Count, F, Sum
from django.utils import timezone
from rest_framework import status as http_status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.core.models import Participation
from apps.core.permissions import HasPerm


@api_view(["GET"])
@permission_classes(
    # Onda 2 A3 (β, 2026-04-27): adicionado `manage_admin_registries` para DAT
    # como ator transversal (validar/suportar). Mesma decisão dos demais
    # endpoints metrics — preserva Lote 4.2.b2 (composition OR ad-hoc por
    # objetos semanticamente diferentes).
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
        - Filter Participation by role=FORMADOR and solicitacao__status=aprovado
        - Aggregate by usuario: count events, sum hours, count distinct municipios
        - Order by -eventos, limit to top 10

    Permissions: HasPerm("run_daily_operations") | HasPerm("supervise_operations") (only authorized users)
    """
    days = int(request.GET.get("days", 30))
    cutoff = timezone.now() - timedelta(days=days)

    # Query participations (formador role only, approved events only, in date range)
    participations = Participation.objects.filter(
        role=Participation.Role.FORMADOR,
        solicitacao__status="aprovado",
        solicitacao__created_at__gte=cutoff,
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
            # Calculate hours worked: sum of (solicitacao.fim - solicitacao.inicio)
            horas_trabalhadas=Sum(
                (F("solicitacao__fim") - F("solicitacao__inicio")),
                output_field=None,
            ),
            municipios_atendidos=Count("solicitacao__municipio_id", distinct=True),
        )
        .order_by("-eventos")[:10]
    )

    # Convert timedelta to hours and format response
    formadores_list = []
    for stat in formadores_stats:
        # Convert timedelta to hours
        horas = 0.0
        if stat["horas_trabalhadas"] is not None:
            horas = round(stat["horas_trabalhadas"].total_seconds() / 3600, 1)

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
