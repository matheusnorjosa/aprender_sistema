"""
API View para grade mensal de disponibilidade.

Endpoint: GET /api/availability/monthly
Query params:
    - year: int (YYYY) - obrigatório
    - month: int (1..12) - obrigatório
    - role: str ("FORMADOR" | "COORDENADOR") - obrigatório
    - gerencia_id: int (opcional)
    - sector: str (opcional) - Filtro por nome do projeto
    - q: str (opcional) - Filtro por nome/email

Permissões (Bug 1 fix pós RBAC Access Policy Realignment, 2026-04-27):
    - Superusers: acesso a todas as gerências
    - Capability `view_all_availability` (Controle/Gerente/Coordenador/
      Apoio de Coordenação por seed 0077): acesso a todas as gerências
    - Sem capability + sem gerencia_id: comportamento SUPER (permitido)
    - Sem capability + com gerencia_id: verifica EquipeGerencia

Cache Redis 5 minutos por (year, month, role, escopo, sector, q).
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false

from __future__ import annotations

import logging
from typing import Any

from django.core.cache import cache
from django.db.models import QuerySet
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import OpenApiParameter, extend_schema

from apps.core.models import EquipeGerencia
from apps.core.permissions import HasSectorAccess
from apps.core.rbac.policies import CanViewAllAvailability
from apps.core.serializers.openapi_critical_contract import (
    MonthlyAvailabilityErrorResponseSerializer,
    MonthlyAvailabilityResponseSerializer,
)
from apps.core.services.monthly_grid_service import build_monthly_grid

logger = logging.getLogger(__name__)


class MonthlyAvailabilityView(APIView):
    """
    API para consultar grade mensal de disponibilidade.

    GET /api/availability/monthly?year=2025&month=10&role=FORMADOR[&gerencia_id=2][&sector=...][&q=...]

    Permissões (conforme PLAN_multi_sector_availability.md):
        - Superusers: acesso a todas as gerências
        - Controle: BLOQUEADO
        - Com gerencia_id: verifica se usuário pertence à gerência
        - Sem gerencia_id: escopo filtrado por gerências vinculadas do usuário

    Returns:
        {
            "days": int,
            "legend": {...},
            "people": [...],
            "cells": {...},
            "details_index": {...}
        }
    """

    # Bug 1 fix (2026-04-27): camada de tradução semântica.
    # Quem tem capability `view_all_availability` (Controle/Gerente/Coord/Apoio
    # via seed 0077) bypassa scope. Quem não tem cai em HasSectorAccess
    # (verificação por gerencia_id via EquipeGerencia).
    permission_classes = [IsAuthenticated, CanViewAllAvailability | HasSectorAccess]

    @extend_schema(
        summary="Grade mensal de disponibilidade",
        parameters=[
            OpenApiParameter(
                name="year",
                location=OpenApiParameter.QUERY,
                required=True,
                type=int,
            ),
            OpenApiParameter(
                name="month",
                location=OpenApiParameter.QUERY,
                required=True,
                type=int,
            ),
            OpenApiParameter(
                name="role",
                location=OpenApiParameter.QUERY,
                required=True,
                type=str,
                enum=["FORMADOR", "COORDENADOR"],
            ),
            OpenApiParameter(
                name="gerencia_id",
                location=OpenApiParameter.QUERY,
                required=False,
                type=int,
            ),
            OpenApiParameter(
                name="sector",
                location=OpenApiParameter.QUERY,
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="q",
                location=OpenApiParameter.QUERY,
                required=False,
                type=str,
            ),
        ],
        responses={
            200: MonthlyAvailabilityResponseSerializer,
            400: MonthlyAvailabilityErrorResponseSerializer,
            500: MonthlyAvailabilityErrorResponseSerializer,
        },
        tags=["availability"],
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        # Validação de parâmetros básicos
        try:
            year = int(request.GET.get("year", 0))
            month = int(request.GET.get("month", 0))
        except (ValueError, TypeError):
            return Response(
                {"error": "Parâmetros 'year' e 'month' devem ser inteiros válidos."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if year < 1900 or year > 2100:
            return Response(
                {"error": "Ano inválido (deve estar entre 1900 e 2100)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if month < 1 or month > 12:
            return Response(
                {"error": "Mês inválido (deve estar entre 1 e 12)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        role = request.GET.get("role", "").upper()
        if role not in ["FORMADOR", "COORDENADOR"]:
            return Response(
                {"error": "Parâmetro 'role' deve ser 'FORMADOR' ou 'COORDENADOR'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sector = request.GET.get("sector", None)
        q = request.GET.get("q", None)

        # Obter gerencia_id (opcional - se omitido, assume SUPER)
        gerencia_id_str = request.GET.get("gerencia_id", None)
        gerencia_id: int | None = None

        if gerencia_id_str:
            try:
                gerencia_id = int(gerencia_id_str)
            except (ValueError, TypeError):
                return Response(
                    {"error": "Parâmetro 'gerencia_id' deve ser um inteiro válido."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        # Sem gerencia_id, restringir escopo para evitar vazamento global:
        # - Perfis amplos (super/capability pode_ver_todas_disponibilidades): visão ampla
        # - Demais perfis: limitar aos usuários das gerências vinculadas
        #
        # Epic 3.2 RBAC Refactor (2026-04-23): hardcoded
        # `groups.filter(name__in=["Superintendência", "Gerência", "Diretoria"])`
        # substituído por capability. user_has_any_perm trata superuser bypass
        # internamente.
        from apps.core.rbac_helpers import user_has_any_perm

        allowed_user_ids: list[int] | None = None
        cache_scope = "global"
        if gerencia_id is None:
            has_wide_scope = user_has_any_perm(request.user, "view_all_availability")
            if has_wide_scope:
                cache_scope = "wide"
            else:
                user_gerencia_ids = list(
                    EquipeGerencia.objects.filter(
                        usuario=request.user,
                        ativo=True,
                    ).values_list("gerencia_id", flat=True)
                )
                if user_gerencia_ids:
                    # PERF-SQL-04: filter nulls at DB level instead of Python
                    allowed_user_ids = list(
                        EquipeGerencia.objects.filter(
                            gerencia_id__in=user_gerencia_ids,
                            ativo=True,
                            usuario_id__isnull=False,
                        )
                        .values_list("usuario_id", flat=True)
                        .distinct()
                    )
                else:
                    # Usuário sem vínculo explícito: restringe ao próprio usuário
                    user_id: int = request.user.id  # type: ignore[assignment]
                    allowed_user_ids = [user_id]
                cache_scope = f"user:{request.user.id}"
        else:
            cache_scope = f"gerencia:{gerencia_id}"

        # ASQ-007: Include monthly version in cache key for targeted invalidation
        from apps.core.utils.cache_utils import get_monthly_cache_version

        monthly_ver = get_monthly_cache_version(request.user.id)
        cache_key = (
            f"monthly:v5:{monthly_ver}:{year}:{month}:{role}:"
            f"{cache_scope}:{sector or '*'}:{(q or '').strip().lower()}"
        )

        # Tentar buscar do cache
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        # Compor grade
        try:
            data = build_monthly_grid(
                year=year,
                month=month,
                role=role,
                gerencia_id=gerencia_id,
                sector=sector,
                q=q,
                allowed_user_ids=allowed_user_ids,
            )
        except Exception as e:
            logger.exception("Erro ao compor grade mensal: %s", e)
            return Response(
                {"error": "Erro ao compor grade mensal."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # ASQ-007: TTL with jitter to prevent cache stampede
        from apps.core.utils.cache_utils import _ttl_with_jitter

        cache.set(cache_key, data, _ttl_with_jitter())

        return Response(data)
