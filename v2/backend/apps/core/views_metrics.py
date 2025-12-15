"""
Metrics API Views

Provides aggregated metrics for dashboard and monitoring.

Issue #189: Team Metrics Endpoints (productivity, formadores, quality)
"""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false

from __future__ import annotations
from datetime import timedelta
from django.db.models import Avg, Case, Count, F, Sum, When
from django.utils import timezone
from rest_framework import status as http_status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response

from .models import AuditLog, Participation, Solicitacao, Usuario
from .permissions import IsControle, IsControleOrDAT, IsGerencia


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

    # Agregações por município (com coordenadas)
    by_municipio = (
        queryset
        .exclude(municipio__isnull=True)
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
        .order_by("-eventos")[:50]  # Top 50 municípios
    )

    # Contagem de coordenadores por município
    coordenadores_por_municipio = {}

    participations = (
        Participation.objects
        .filter(
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
        by_municipio_list.append({
            "municipio": municipio_nome,
            "uf": item["municipio__uf"],
            "latitude": float(item["municipio__latitude"]),
            "longitude": float(item["municipio__longitude"]),
            "projetos": item["projetos"],
            "eventos": item["eventos"],
            "coordenadores": coordenadores_por_municipio.get(municipio_nome, 0),
        })

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

    # Formatar top projetos
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
        "by_municipio": by_municipio_list,  # Mudou de "by_uf"
        "top_projetos": top_projetos_list,
    })


@api_view(["GET"])
@permission_classes([IsControleOrDAT])
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

    Permissions: IsControleOrDAT (Controle, DAT ou Superintendência)
    """
    uf = request.query_params.get("uf")
    if not uf:
        return Response({"detail": "Parâmetro 'uf' é obrigatório"}, status=400)

    # Buscar participações de coordenadores para o estado especificado
    participations = (
        Participation.objects
        .filter(
            role=Participation.Role.COORDENADOR,
            solicitacao__municipio__uf=uf,
            usuario__isnull=False,
        )
        .select_related("usuario", "solicitacao", "solicitacao__projeto", "solicitacao__municipio")
    )

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

        coordenadores_list.append({
            "id": data["id"],
            "nome": data["nome"],
            "eventos": data["eventos"],
            "projetos": projetos_list,
            "municipios": municipios_list,
        })

    coordenadores_list.sort(key=lambda x: int(x["eventos"] or 0), reverse=True)

    return Response({
        "uf": uf,
        "coordenadores": coordenadores_list,
    })


@api_view(["GET"])
@permission_classes([IsControle | IsGerencia])
def productivity_metrics(request: Request) -> Response:
    """
    Productivity metrics for the last N days (Issue #189).

    Query params:
        days (int): Number of days to look back (default: 7)

    Returns:
        {
            "period": "7d",
            "events_created": 120,
            "events_approved": 95,
            "events_rejected": 10,
            "approval_rate": 79.17,
            "avg_approval_time_hours": 18.5,
            "gcal_published": 85,
            "gcal_error_rate": 5.26
        }

    Calculations:
        - approval_rate = (approved / total) * 100 (0.0 if division by zero)
        - avg_approval_time_hours = avg(updated_at - created_at).total_seconds() / 3600
        - gcal_error_rate = (errors / approved) * 100 (0.0 if division by zero)

    Permissions: IsControle | IsGerencia (only authorized users)
    """
    days = int(request.GET.get("days", 7))
    cutoff = timezone.now() - timedelta(days=days)

    # Query all solicitações in the period
    qs = Solicitacao.objects.filter(created_at__gte=cutoff)

    # Aggregate counts by status
    stats = qs.aggregate(
        total=Count("id"),
        approved=Count(Case(When(status="aprovado", then=1))),
        rejected=Count(Case(When(status="reprovado", then=1))),
    )

    # Calculate approval rate (avoid division by zero)
    total = stats["total"] or 0
    approved = stats["approved"] or 0
    rejected = stats["rejected"] or 0
    approval_rate = (approved / total * 100) if total > 0 else 0.0

    # Calculate average approval time (only for approved events)
    approved_qs = qs.filter(status="aprovado")
    avg_time_seconds = approved_qs.aggregate(
        avg_time=Avg(
            (F("updated_at") - F("created_at")),
            output_field=None,
        )
    )["avg_time"]

    # Convert timedelta to hours (handle None case)
    if avg_time_seconds is not None:
        avg_approval_time_hours = round(avg_time_seconds.total_seconds() / 3600, 2)
    else:
        avg_approval_time_hours = 0.0

    # GCal metrics
    gcal_stats = approved_qs.aggregate(
        published=Count(Case(When(gcal_status="PUBLISHED", then=1))),
        errors=Count(Case(When(gcal_status="ERROR", then=1))),
    )

    gcal_published = gcal_stats["published"] or 0
    gcal_errors = gcal_stats["errors"] or 0
    gcal_error_rate = (gcal_errors / approved * 100) if approved > 0 else 0.0

    return Response(
        {
            "period": f"{days}d",
            "events_created": total,
            "events_approved": approved,
            "events_rejected": rejected,
            "approval_rate": round(approval_rate, 2),
            "avg_approval_time_hours": avg_approval_time_hours,
            "gcal_published": gcal_published,
            "gcal_error_rate": round(gcal_error_rate, 2),
        },
        status=http_status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsControle | IsGerencia])
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

    Permissions: IsControle | IsGerencia (only authorized users)
    """
    days = int(request.GET.get("days", 30))
    cutoff = timezone.now() - timedelta(days=days)

    # Query participations (formador role only, approved events only, in date range)
    participations = Participation.objects.filter(
        role=Participation.Role.FORMADOR,
        solicitacao__status="aprovado",
        solicitacao__created_at__gte=cutoff,
        usuario__isnull=False,  # Exclude guest participations
    ).select_related("usuario", "solicitacao")

    # Aggregate by usuario
    formadores_stats = (
        participations.values("usuario_id", "usuario__first_name", "usuario__last_name")
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

        # Build full name
        nome = f"{stat['usuario__first_name']} {stat['usuario__last_name']}".strip()
        if not nome:
            # Fallback to username if no first/last name
            try:
                usuario = Usuario.objects.get(id=stat["usuario_id"])
                nome = usuario.username
            except Usuario.DoesNotExist:
                nome = f"Usuário #{stat['usuario_id']}"

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


@api_view(["GET"])
@permission_classes([IsControle | IsGerencia])
def quality_metrics(request: Request) -> Response:
    """
    Quality metrics for the last N days (Issue #189).

    Query params:
        days (int): Number of days to look back (default: 30)

    Returns:
        {
            "period": "30d",
            "rejection_rate": 8.3,
            "conflict_rate": 5.2,
            "rework_rate": 12.1,
            "avg_approval_time_hours": 18.5,
            "avg_publish_time_minutes": 3.2
        }

    Calculations:
        - rejection_rate = (rejected / total) * 100
        - conflict_rate = (with conflicts / total) * 100 (count solicitações with 'conflict' in observacoes)
        - rework_rate = (edited after creation / total) * 100 (check AuditLog for UPDATE actions)
        - avg_approval_time_hours = avg(updated_at - created_at).total_seconds() / 3600
        - avg_publish_time_minutes = avg(gcal_last_sync_at - updated_at).total_seconds() / 60

    Permissions: IsControle | IsGerencia (only authorized users)
    """
    days = int(request.GET.get("days", 30))
    cutoff = timezone.now() - timedelta(days=days)

    # Query all solicitações in the period
    qs = Solicitacao.objects.filter(created_at__gte=cutoff)

    # Aggregate counts
    stats = qs.aggregate(
        total=Count("id"),
        rejected=Count(Case(When(status="reprovado", then=1))),
        # Count solicitações with "conflict" keyword in observacoes (case-insensitive)
        with_conflicts=Count(
            Case(When(observacoes__icontains="conflict", then=1))
        ),
    )

    total = stats["total"] or 0
    rejected = stats["rejected"] or 0
    with_conflicts = stats["with_conflicts"] or 0

    # Rejection rate
    rejection_rate = (rejected / total * 100) if total > 0 else 0.0

    # Conflict rate
    conflict_rate = (with_conflicts / total * 100) if total > 0 else 0.0

    # Rework rate: count solicitações that have UPDATE actions in AuditLog
    # (edited after creation)
    reworked_ids = (
        AuditLog.objects.filter(
            action="UPDATE",
            model_name="Solicitacao",
            created_at__gte=cutoff,
        )
        .values_list("details__solicitacao_id", flat=True)
        .distinct()
    )
    reworked_count = len(list(reworked_ids))
    rework_rate = (reworked_count / total * 100) if total > 0 else 0.0

    # Average approval time (approved events only)
    approved_qs = qs.filter(status="aprovado")
    avg_approval_time_seconds = approved_qs.aggregate(
        avg_time=Avg(
            (F("updated_at") - F("created_at")),
            output_field=None,
        )
    )["avg_time"]

    if avg_approval_time_seconds is not None:
        avg_approval_time_hours = round(
            avg_approval_time_seconds.total_seconds() / 3600, 2
        )
    else:
        avg_approval_time_hours = 0.0

    # Average publish time (PUBLISHED events only, exclude None gcal_last_sync_at)
    published_qs = approved_qs.filter(
        gcal_status="PUBLISHED",
        gcal_last_sync_at__isnull=False,
    )
    avg_publish_time_seconds = published_qs.aggregate(
        avg_time=Avg(
            (F("gcal_last_sync_at") - F("updated_at")),
            output_field=None,
        )
    )["avg_time"]

    if avg_publish_time_seconds is not None:
        avg_publish_time_minutes = round(
            avg_publish_time_seconds.total_seconds() / 60, 2
        )
    else:
        avg_publish_time_minutes = 0.0

    return Response(
        {
            "period": f"{days}d",
            "rejection_rate": round(rejection_rate, 2),
            "conflict_rate": round(conflict_rate, 2),
            "rework_rate": round(rework_rate, 2),
            "avg_approval_time_hours": avg_approval_time_hours,
            "avg_publish_time_minutes": avg_publish_time_minutes,
        },
        status=http_status.HTTP_200_OK,
    )
