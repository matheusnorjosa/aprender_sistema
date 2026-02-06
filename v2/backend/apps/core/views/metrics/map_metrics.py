"""
Map Metrics Views - §9 Epic #459

Map-related metrics endpoints for geographic visualization.
Extracted from views_metrics.py.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false

from __future__ import annotations

from django.db.models import Count
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.core.exceptions import ValidationAPIError
from apps.core.models import Participation, Solicitacao
from apps.core.permissions import IsMapMetrics


@api_view(["GET"])
@permission_classes([IsMapMetrics])
@throttle_classes([ScopedRateThrottle])
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
        "by_municipio": [{"municipio": "Fortaleza", "uf": "CE", ...}, ...],
        "top_projetos": [{"nome": "Projeto A", "count": 5}, ...]
    }

    Permissions: IsMapMetrics (Controle, DAT, Superintendência, Gerência, Diretoria)
    """
    queryset = Solicitacao.objects.all()

    # Parâmetro limit com default e máximo (#408)
    try:
        limit = min(int(request.query_params.get("limit", 50)), 100)
    except (ValueError, TypeError):
        limit = 50

    # Filtros opcionais
    filters_applied = {}

    status_filter = request.query_params.get("status")
    if status_filter:
        valid_statuses = ["pendente", "aprovado", "reprovado"]
        if status_filter not in valid_statuses:
            raise ValidationAPIError(
                message=f"Status inválido. Valores aceitos: {', '.join(valid_statuses)}",
                field="status",
            )
        queryset = queryset.filter(status=status_filter)
        filters_applied["status"] = status_filter

    projeto_filter = request.query_params.get("projeto_id")
    if projeto_filter:
        if not projeto_filter.isdigit():
            raise ValidationAPIError(
                message="projeto_id deve ser um ID numérico válido",
                field="projeto_id",
            )
        projeto_id = int(projeto_filter)
        queryset = queryset.filter(projeto_id=projeto_id)
        filters_applied["projeto_id"] = projeto_id

    uf_filter = request.query_params.get("uf")
    if uf_filter:
        queryset = queryset.filter(municipio__uf=uf_filter)
        filters_applied["uf"] = uf_filter

    # Agregações por município (com coordenadas)
    by_municipio = (
        queryset.exclude(municipio__isnull=True)
        .exclude(municipio__latitude__isnull=True)  # Apenas municípios com coordenadas
        .exclude(municipio__longitude__isnull=True)
        .values(
            "municipio__nome",
            "municipio__uf",
            "municipio__latitude",
            "municipio__longitude",
        )
        .annotate(
            projetos=Count("projeto_id", distinct=True),
            eventos=Count("id"),
        )
        .order_by("-eventos")[:limit]  # Respects limit param (#408)
    )

    # Contagem de coordenadores por município
    coordenadores_por_municipio = {}

    participations = (
        Participation.objects.filter(
            role=Participation.Role.COORDENADOR,
            solicitacao__in=queryset,
            solicitacao__municipio__isnull=False,
        )
        .values("solicitacao__municipio__nome")
        .annotate(coordenadores=Count("usuario_id", distinct=True))
    )

    for item in participations:
        coordenadores_por_municipio[item["solicitacao__municipio__nome"]] = item["coordenadores"]

    # Formatar resposta com coordenadores
    by_municipio_list = []
    for item in by_municipio:
        municipio_nome = item["municipio__nome"]
        by_municipio_list.append(
            {
                "municipio": municipio_nome,
                "uf": item["municipio__uf"],
                "latitude": float(item["municipio__latitude"]),
                "longitude": float(item["municipio__longitude"]),
                "projetos": item["projetos"],
                "eventos": item["eventos"],
                "coordenadores": coordenadores_por_municipio.get(municipio_nome, 0),
            }
        )

    top_projetos = (
        queryset.exclude(projeto__isnull=True)
        .values("projeto__nome")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )

    # Contagens por status
    status_counts = queryset.values("status").annotate(count=Count("id"))
    by_status = {item["status"]: item["count"] for item in status_counts}

    # Formatar top projetos
    top_projetos_list = [{"nome": item["projeto__nome"], "count": item["count"]} for item in top_projetos]

    return Response(
        {
            "meta": {
                "generated_at": timezone.now().isoformat(),
                "filters": filters_applied,
                "limit": limit,
                "max_limit": 100,
            },
            "totals": {
                "all": queryset.count(),
                "by_status": by_status,
            },
            "by_municipio": by_municipio_list,
            "top_projetos": top_projetos_list,
        }
    )


# Throttle scope for metrics_map (#409)
metrics_map.throttle_scope = "metrics"  # type: ignore[attr-defined]


@api_view(["GET"])
@permission_classes([IsMapMetrics])
@throttle_classes([ScopedRateThrottle])
def metrics_map_coordinators(request: Request) -> Response:
    """
    GET /api/metrics/map/coordinators/

    Retorna detalhes dos coordenadores para um estado específico (UF).

    Query parameters:
    - uf (required): UF do estado (ex: CE, SP, RJ)

    Response:
    {
        "uf": "CE",
        "coordenadores": [
            {
                "id": 1,
                "nome": "João Silva",
                "eventos": 10,
                "projetos": [{"nome": "Projeto A", "eventos": 5}, ...],
                "municipios": [{"nome": "Fortaleza", "eventos": 3}, ...]
            },
            ...
        ]
    }

    Permissions: IsMapMetrics (Controle, DAT, Superintendência, Gerência, Diretoria)
    """
    uf = request.query_params.get("uf")
    if not uf:
        raise ValidationAPIError(
            message="Parâmetro 'uf' é obrigatório",
            field="uf",
        )

    # Buscar participações de coordenadores para o estado especificado
    participations = Participation.objects.filter(
        role=Participation.Role.COORDENADOR,
        solicitacao__municipio__uf=uf,
        usuario__isnull=False,
    ).select_related("usuario", "solicitacao", "solicitacao__projeto", "solicitacao__municipio")

    # Agregar por coordenador com contagem detalhada
    coordenadores_data: dict[int, dict] = {}
    for p in participations:
        user_id = p.usuario_id
        if user_id not in coordenadores_data:
            nome = f"{p.usuario.first_name} {p.usuario.last_name}".strip()
            if not nome:
                nome = p.usuario.username
            coordenadores_data[user_id] = {
                "id": user_id,
                "nome": nome,
                "eventos": 0,
                "projetos": {},  # {nome_projeto: count}
                "municipios": {},  # {nome_municipio: count}
            }

        coordenadores_data[user_id]["eventos"] += 1

        # Contagem por projeto
        if p.solicitacao.projeto:
            proj_nome = p.solicitacao.projeto.nome
            coordenadores_data[user_id]["projetos"][proj_nome] = (
                coordenadores_data[user_id]["projetos"].get(proj_nome, 0) + 1
            )

        # Contagem por município
        if p.solicitacao.municipio:
            mun_nome = p.solicitacao.municipio.nome
            coordenadores_data[user_id]["municipios"][mun_nome] = (
                coordenadores_data[user_id]["municipios"].get(mun_nome, 0) + 1
            )

    # Converter dicts para listas ordenadas por eventos desc
    coordenadores_list: list[dict[str, object]] = []
    for data in coordenadores_data.values():
        # Ordenar projetos por quantidade de eventos desc
        projetos_items: list[tuple[str, int]] = list(data["projetos"].items())
        projetos_items.sort(key=lambda x: x[1], reverse=True)
        projetos_list = [{"nome": nome, "eventos": count} for nome, count in projetos_items]

        # Ordenar municípios por quantidade de eventos desc
        municipios_items: list[tuple[str, int]] = list(data["municipios"].items())
        municipios_items.sort(key=lambda x: x[1], reverse=True)
        municipios_list = [{"nome": nome, "eventos": count} for nome, count in municipios_items]

        coordenadores_list.append(
            {
                "id": data["id"],
                "nome": data["nome"],
                "eventos": data["eventos"],
                "projetos": projetos_list,
                "municipios": municipios_list,
            }
        )

    coordenadores_list.sort(key=lambda x: int(x["eventos"] or 0), reverse=True)

    return Response(
        {
            "uf": uf,
            "coordenadores": coordenadores_list,
        }
    )


# Throttle scope for metrics_map_coordinators (#409)
metrics_map_coordinators.throttle_scope = "metrics"  # type: ignore[attr-defined]
