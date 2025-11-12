"""
Metrics API Views

Provides aggregated metrics for dashboard and monitoring.
"""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false

from __future__ import annotations
from typing import Any
from django.db.models import QuerySet
from rest_framework.request import Request
from rest_framework.response import Response

from django.db.models import Count
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import Solicitacao
from .permissions import IsControleOrDAT


@api_view(["GET"])
@permission_classes([IsControleOrDAT])
def metrics_map(request: Request) -> Response:
    """
    GET /api/metrics/map/

    Retorna métricas agregadas para visualização em mapa.

    Query parameters:
    - status: filtrar por status (pendente, aprovado, reprovado)
    - projeto: filtrar por projeto ID
    - uf: filtrar por UF

    Response:
    {
        "meta": {
            "generated_at": "2025-10-21T...",
            "filters": {"status": "...", "projeto": "...", "uf": "..."}
        },
        "totals": {
            "all": 100,
            "by_status": {"pendente": 10, "aprovado": 80, "reprovado": 10}
        },
        "by_uf": [{"uf": "CE", "count": 10}, ...],
        "top_projetos": [{"nome": "Projeto A", "count": 5}, ...]
    }

    Permissions: IsControleOrDAT (Controle, DAT ou Superintendência)
    """
    queryset = Solicitacao.objects.all()

    # Filtros opcionais
    filters_applied = {}

    status_filter = request.query_params.get("status")
    if status_filter:
        valid_statuses = ["pendente", "aprovado", "reprovado"]
        if status_filter not in valid_statuses:
            return Response(
                {"detail": f"Status inválido. Valores aceitos: {', '.join(valid_statuses)}"},
                status=400
            )
        queryset = queryset.filter(status=status_filter)
        filters_applied["status"] = status_filter

    projeto_filter = request.query_params.get("projeto_id")
    if projeto_filter:
        if not projeto_filter.isdigit():
            return Response({"detail": "projeto_id deve ser um ID numérico válido"}, status=400)
        projeto_id = int(projeto_filter)
        queryset = queryset.filter(projeto_id=projeto_id)
        filters_applied["projeto_id"] = projeto_id

    uf_filter = request.query_params.get("uf")
    if uf_filter:
        queryset = queryset.filter(municipio__uf=uf_filter)
        filters_applied["uf"] = uf_filter

    # Agregações
    by_uf = (
        queryset
        .exclude(municipio__isnull=True)
        .values("municipio__uf")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    top_projetos = (
        queryset
        .exclude(projeto__isnull=True)
        .values("projeto__nome")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )

    # Contagens por status
    status_counts = queryset.values("status").annotate(count=Count("id"))
    by_status = {item["status"]: item["count"] for item in status_counts}

    # Formatar resposta
    by_uf_list = [{"uf": item["municipio__uf"], "count": item["count"]} for item in by_uf]
    top_projetos_list = [
        {"nome": item["projeto__nome"], "count": item["count"]}
        for item in top_projetos
    ]

    return Response({
        "meta": {
            "generated_at": timezone.now().isoformat(),
            "filters": filters_applied,
        },
        "totals": {
            "all": queryset.count(),
            "by_status": by_status,
        },
        "by_uf": by_uf_list,
        "top_projetos": top_projetos_list,
    })
