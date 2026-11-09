"""
Map Metrics Views - §9 Epic #459

Map-related metrics endpoints for geographic visualization.
Extracted from views_metrics.py.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Any

from django.db.models import Count, QuerySet
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.core.exceptions import ValidationAPIError
from apps.core.models import Participation, Projeto, Solicitacao, Usuario
from apps.core.permissions import HasPerm
from apps.core.services.compra_elegibilidade import _compras_validas, _q_libera  # pyright: ignore[reportPrivateUsage]
from apps.core.services.solicitacao_projetos import (
    contar_por_projeto,
    projetos_distintos_por,
    projetos_do_evento,
    q_tem_projeto,
)

MAP_LIMIT_MAX = 1000
VALID_STATUS_FILTERS = {"pendente", "aprovado", "reprovado"}


def coordenadores_do_evento(solicitacoes: QuerySet[Solicitacao]) -> set[tuple[int, int]]:
    """(pessoa, evento) dos coordenadores de cada evento de `solicitacoes`, para o Mapa.

    Decisão do dono (04/11/2026): o responsável (`Solicitacao.coordenador`; sem ele, quem criou)
    mais os coordenadores além dele (COORD_ACOMPANHA). Quem só criou o evento para outro responsável
    não conta. O conjunto deduplica a mesma pessoa em dois papéis no evento. Duas consultas.
    """
    pares = {
        (coordenador_id if coordenador_id is not None else criador_id, sol_id)
        for sol_id, coordenador_id, criador_id in solicitacoes.values_list("id", "coordenador_id", "usuario_id")
    }
    pares.update(
        Participation.objects.filter(
            role=Participation.Role.COORD_ACOMPANHA, solicitacao__in=solicitacoes, usuario__isnull=False
        ).values_list("usuario_id", "solicitacao_id")
    )
    return pares


@dataclass
class MapFilterValues:
    status: str | None = None
    projeto_id: int | None = None
    uf: str | None = None
    data_inicio: date | None = None
    data_fim: date | None = None


def _parse_map_limit(request: Request) -> int | None:
    """
    Parse de limit para endpoint de mapa.

    - Sem parâmetro: sem truncamento
    - Com parâmetro: inteiro positivo, limitado a MAP_LIMIT_MAX
    """
    limit_param = request.query_params.get("limit")
    if not limit_param:
        return None

    try:
        limit = int(limit_param)
    except (TypeError, ValueError):
        raise ValidationAPIError(
            message="limit deve ser um inteiro positivo",
            field="limit",
        ) from None

    if limit < 1:
        raise ValidationAPIError(
            message="limit deve ser maior que zero",
            field="limit",
        )

    return min(limit, MAP_LIMIT_MAX)


def _parse_map_filter_values(
    request: Request, *, require_uf: bool = False
) -> tuple[MapFilterValues, dict[str, object]]:
    """
    Parse e valida filtros comuns dos endpoints de mapa.
    """
    filters = MapFilterValues()
    filters_applied: dict[str, object] = {}

    status_filter = request.query_params.get("status")
    if status_filter:
        if status_filter not in VALID_STATUS_FILTERS:
            raise ValidationAPIError(
                message=f"Status inválido. Valores aceitos: {', '.join(sorted(VALID_STATUS_FILTERS))}",
                field="status",
            )
        filters.status = status_filter
        filters_applied["status"] = status_filter

    projeto_filter = request.query_params.get("projeto_id")
    if projeto_filter:
        if not projeto_filter.isdigit():
            raise ValidationAPIError(
                message="projeto_id deve ser um ID numérico válido",
                field="projeto_id",
            )
        filters.projeto_id = int(projeto_filter)
        filters_applied["projeto_id"] = filters.projeto_id

    uf_filter = request.query_params.get("uf")
    if uf_filter:
        uf_normalized = uf_filter.strip().upper()
        if len(uf_normalized) != 2 or not uf_normalized.isalpha():
            raise ValidationAPIError(
                message="uf deve ter 2 letras (ex: CE, SP, RJ)",
                field="uf",
            )
        filters.uf = uf_normalized
        filters_applied["uf"] = uf_normalized
    elif require_uf:
        raise ValidationAPIError(
            message="Parâmetro 'uf' é obrigatório",
            field="uf",
        )

    data_inicio_raw = request.query_params.get("data_inicio")
    data_fim_raw = request.query_params.get("data_fim")

    if data_inicio_raw:
        try:
            filters.data_inicio = date.fromisoformat(data_inicio_raw)
        except ValueError:
            raise ValidationAPIError(
                message="data_inicio deve estar no formato YYYY-MM-DD",
                field="data_inicio",
            ) from None
        filters_applied["data_inicio"] = filters.data_inicio.isoformat()

    if data_fim_raw:
        try:
            filters.data_fim = date.fromisoformat(data_fim_raw)
        except ValueError:
            raise ValidationAPIError(
                message="data_fim deve estar no formato YYYY-MM-DD",
                field="data_fim",
            ) from None
        filters_applied["data_fim"] = filters.data_fim.isoformat()

    if filters.data_inicio and filters.data_fim and filters.data_inicio > filters.data_fim:
        raise ValidationAPIError(
            message="data_inicio não pode ser maior que data_fim",
            field="data_inicio",
        )

    return filters, filters_applied


def _apply_filters_to_solicitacoes(
    queryset: QuerySet[Solicitacao],
    filters: MapFilterValues,
) -> QuerySet[Solicitacao]:
    """
    Aplica filtros parseados ao queryset de solicitações (eventos).
    """
    if filters.status:
        queryset = queryset.filter(status=filters.status)
    if filters.projeto_id is not None:
        queryset = queryset.filter(q_tem_projeto(pk=filters.projeto_id))  # as duas vagas (#2036)
    if filters.uf:
        queryset = queryset.filter(municipio__uf=filters.uf)
    if filters.data_inicio:
        queryset = queryset.filter(inicio__date__gte=filters.data_inicio)
    if filters.data_fim:
        queryset = queryset.filter(inicio__date__lte=filters.data_fim)
    return queryset


def _pares_de_compra(filters: MapFilterValues) -> set[tuple[int, str, int]]:
    """(município, UF, projeto) com compra pela regra da criação (`services/compra_elegibilidade`).

    Decisão do dono (05/11/2026): conta a lista atual (`DATCompra` ativa com quantidade > 0), por par
    município × projeto. Com o filtro de projeto vale a família da coleção: o par é município × projeto
    filtrado, liberado por compra de qualquer projeto que o libere. O filtro de datas olha
    `data_compra`; a compra sem data fica de fora só quando há filtro de datas.
    """
    compras = _compras_validas()
    if filters.projeto_id is not None:
        projeto = Projeto.objects.select_related("projeto_geral").filter(pk=filters.projeto_id).first()
        if projeto is None:
            return set()
        compras = compras.filter(_q_libera(projeto))
    if filters.uf:
        compras = compras.filter(municipio__uf=filters.uf)
    if filters.data_inicio:
        compras = compras.filter(data_compra__gte=filters.data_inicio)
    if filters.data_fim:
        compras = compras.filter(data_compra__lte=filters.data_fim)
    return {
        (municipio_id, uf, filters.projeto_id if filters.projeto_id is not None else projeto_id)
        for municipio_id, uf, projeto_id in compras.values_list("municipio_id", "municipio__uf", "projeto_id")
    }


@api_view(["GET"])
@permission_classes([HasPerm("view_map_metrics")])
@throttle_classes([ScopedRateThrottle])
def metrics_map(request: Request) -> Response:
    """
    GET /api/metrics/map/

    Retorna métricas agregadas para visualização em mapa.

    Query parameters:
    - status: filtrar por status (pendente, aprovado, reprovado)
    - projeto_id: filtrar por projeto ID
    - uf: filtrar por UF
    - data_inicio: filtrar eventos (início) e compras (data_compra) a partir da data (YYYY-MM-DD)
    - data_fim: filtrar eventos (início) e compras (data_compra) até a data (YYYY-MM-DD)
    - limit: limita quantidade de municípios retornados (opcional)

    "compras" conta pares município × projeto com compra pela regra da criação (`_pares_de_compra`).

    Response:
    {
        "meta": {
            "generated_at": "2025-10-21T...",
            "filters": {
                "status": "...",
                "projeto_id": 1,
                "uf": "CE",
                "data_inicio": "2025-01-01",
                "data_fim": "2025-01-31"
            }
        },
        "totals": {
            "all": 100,
            "by_status": {"pendente": 10, "aprovado": 80, "reprovado": 10},
            "compras": 25
        },
        "by_uf": [{"uf": "CE", "eventos": 40, "compras": 12, ...}, ...],
        "by_municipio": [{"municipio": "Fortaleza", "uf": "CE", "eventos": 10, "compras": 4, ...}, ...],
        "top_projetos": [{"nome": "Projeto A", "count": 5}, ...]
    }

    Permissions: HasPerm("view_map_metrics") (Controle, DAT, Superintendência, Gerência, Diretoria)
    """
    filters, filters_applied = _parse_map_filter_values(request)
    limit = _parse_map_limit(request)

    queryset = _apply_filters_to_solicitacoes(Solicitacao.objects.all(), filters)
    pares_de_compra = _pares_de_compra(filters)

    # Agregações por município (com coordenadas)
    by_municipio_queryset = (
        queryset.exclude(municipio__isnull=True)
        .exclude(municipio__latitude__isnull=True)  # Apenas municípios com coordenadas
        .exclude(municipio__longitude__isnull=True)
        .values(
            "municipio_id",
            "municipio__nome",
            "municipio__uf",
            "municipio__latitude",
            "municipio__longitude",
        )
        .annotate(eventos=Count("id"))
        .order_by("-eventos", "municipio__nome")
    )

    if limit is not None:
        by_municipio_queryset = by_municipio_queryset[:limit]

    # Projetos distintos pelas duas vagas (#2036): o evento conta uma vez, os projetos dele, os dois. Com o
    # filtro de projeto, só o projeto filtrado (o parceiro do combo não entra).
    com_municipio = queryset.exclude(municipio__isnull=True)
    projetos_por_municipio = projetos_distintos_por(com_municipio, "municipio_id", so_projeto=filters.projeto_id)
    projetos_por_uf = projetos_distintos_por(com_municipio, "municipio__uf", so_projeto=filters.projeto_id)

    # Coordenadores distintos por município e por UF, de uma só leitura dos pares (pessoa, evento)
    local_do_evento = {
        sol_id: (municipio_id, uf)
        for sol_id, municipio_id, uf in queryset.exclude(municipio__isnull=True).values_list(
            "id", "municipio_id", "municipio__uf"
        )
    }
    pessoas_por_municipio: dict[int, set[int]] = defaultdict(set)
    pessoas_por_uf: dict[str, set[int]] = defaultdict(set)
    for pessoa_id, sol_id in coordenadores_do_evento(queryset):
        if sol_id not in local_do_evento:
            continue
        municipio_id, uf = local_do_evento[sol_id]
        pessoas_por_municipio[int(municipio_id)].add(pessoa_id)
        if uf:
            pessoas_por_uf[str(uf)].add(pessoa_id)
    coordenadores_por_municipio = {mid: len(p) for mid, p in pessoas_por_municipio.items()}
    coordenadores_por_uf = {uf: len(p) for uf, p in pessoas_por_uf.items()}

    compras_por_municipio: dict[int, int] = defaultdict(int)
    compras_por_uf: dict[str, int] = defaultdict(int)
    for municipio_id, uf, _projeto_id in pares_de_compra:
        compras_por_municipio[municipio_id] += 1
        compras_por_uf[uf] += 1

    # Formatar resposta com coordenadores
    by_municipio_list: list[dict[str, object]] = []
    for item in by_municipio_queryset:
        municipio_id = int(item["municipio_id"])
        municipio_nome = item["municipio__nome"]
        by_municipio_list.append(
            {
                "municipio": municipio_nome,
                "uf": item["municipio__uf"],
                "latitude": float(item["municipio__latitude"]),
                "longitude": float(item["municipio__longitude"]),
                "projetos": projetos_por_municipio[municipio_id],
                "eventos": item["eventos"],
                "coordenadores": coordenadores_por_municipio.get(municipio_id, 0),
                "compras": compras_por_municipio.get(municipio_id, 0),
            }
        )

    by_uf_queryset = (
        queryset.exclude(municipio__isnull=True)
        .values("municipio__uf")
        .annotate(
            eventos=Count("id"),
            municipios=Count("municipio_id", distinct=True),
        )
        .order_by("-eventos", "municipio__uf")
    )

    by_uf_list: list[dict[str, object]] = []
    for item in by_uf_queryset:
        uf = str(item["municipio__uf"])
        by_uf_list.append(
            {
                "uf": uf,
                "eventos": int(item["eventos"]),
                "projetos": projetos_por_uf[uf],
                "municipios": int(item["municipios"]),
                "coordenadores": coordenadores_por_uf.get(uf, 0),
                "compras": compras_por_uf.get(uf, 0),
            }
        )

    # Conta o evento de dois projetos nos dois (#2036), ou só no projeto filtrado; ordena e corta depois da soma.
    por_projeto = contar_por_projeto(queryset, "nome", so_projeto=filters.projeto_id)
    top_projetos = sorted(por_projeto.items(), key=lambda par: (-par[1]["count"], par[0]))[:10]

    # Contagens por status
    status_counts = queryset.values("status").annotate(count=Count("id"))
    by_status = {item["status"]: item["count"] for item in status_counts}

    # Formatar top projetos
    top_projetos_list = [{"nome": nome, "count": valores["count"]} for nome, valores in top_projetos]

    return Response(
        {
            "meta": {
                "generated_at": timezone.now().isoformat(),
                "filters": filters_applied,
                "limit": limit,
                "max_limit": MAP_LIMIT_MAX,
            },
            "totals": {
                "all": queryset.count(),
                "by_status": by_status,
                "compras": len(pares_de_compra),
            },
            "by_uf": by_uf_list,
            "by_municipio": by_municipio_list,
            "top_projetos": top_projetos_list,
        }
    )


# Throttle scope for metrics_map (#409)
metrics_map.throttle_scope = "metrics"  # type: ignore[attr-defined]


@api_view(["GET"])
@permission_classes([HasPerm("view_map_metrics")])
@throttle_classes([ScopedRateThrottle])
def metrics_map_coordinators(request: Request) -> Response:
    """
    GET /api/metrics/map/coordinators/

    Retorna detalhes dos coordenadores para um estado específico (UF).

    Query parameters:
    - uf (required): UF do estado (ex: CE, SP, RJ)
    - status: filtrar por status da solicitação (opcional)
    - projeto_id: filtrar por projeto (opcional)
    - data_inicio: filtrar por início >= data (YYYY-MM-DD, opcional)
    - data_fim: filtrar por início <= data (YYYY-MM-DD, opcional)

    Response:
    {
        "uf": "CE",
        "meta": {"filters": {...}},
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

    Permissions: HasPerm("view_map_metrics") (Controle, DAT, Superintendência, Gerência, Diretoria)
    """
    filters, filters_applied = _parse_map_filter_values(request, require_uf=True)
    solicitacoes_filtradas = _apply_filters_to_solicitacoes(Solicitacao.objects.all(), filters)

    # Coordenadores do evento (responsável + COORD_ACOMPANHA, uma vez por evento) no estado especificado;
    # eventos e pessoas em consultas fixas, sem N+1
    pares = sorted(coordenadores_do_evento(solicitacoes_filtradas))
    eventos = solicitacoes_filtradas.select_related("projeto", "projeto_2", "municipio").in_bulk(
        {sol_id for _, sol_id in pares}
    )
    pessoas = Usuario.objects.in_bulk({user_id for user_id, _ in pares})

    # Agregar por coordenador com contagem detalhada
    coordenadores_data: dict[int, dict[str, Any]] = {}
    for user_id, sol_id in pares:
        solicitacao, pessoa = eventos.get(sol_id), pessoas.get(user_id)
        if solicitacao is None or pessoa is None:
            continue  # o evento saiu do filtro (ou a pessoa foi apagada) entre as leituras
        if user_id not in coordenadores_data:
            nome = str(pessoa)  # nome, ou "Usuario #id": nunca o login (CPF)
            coordenadores_data[user_id] = {
                "id": user_id,
                "nome": nome,
                "eventos": 0,
                "projetos": {},  # {nome_projeto: count}
                "municipios": {},  # {nome_municipio: count}
            }

        coordenadores_data[user_id]["eventos"] += 1

        # Contagem por projeto: o evento de dois projetos conta nos dois (#2036), ou só no projeto filtrado
        for projeto in projetos_do_evento(solicitacao):
            if filters.projeto_id is not None and projeto.pk != filters.projeto_id:
                continue
            proj_nome = projeto.nome
            coordenadores_data[user_id]["projetos"][proj_nome] = (
                coordenadores_data[user_id]["projetos"].get(proj_nome, 0) + 1
            )

        # Contagem por município
        if solicitacao.municipio:
            mun_nome = solicitacao.municipio.nome
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
            "uf": filters.uf,
            "meta": {
                "filters": filters_applied,
            },
            "coordenadores": coordenadores_list,
        }
    )


# Throttle scope for metrics_map_coordinators (#409)
metrics_map_coordinators.throttle_scope = "metrics"  # type: ignore[attr-defined]
