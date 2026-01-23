"""
API View para grade mensal de disponibilidade.

Endpoint: GET /api/availability/monthly
Query params:
    - year: int (YYYY) - obrigatório
    - month: int (1..12) - obrigatório
    - role: str ("FORMADOR" | "COORDENADOR") - obrigatório
    - gerencia_id: int (opcional) - Se omitido, assume SUPERINTENDENCIA (SUPER)
    - sector: str (opcional) - Filtro por nome do projeto
    - q: str (opcional) - Filtro por nome/email

Permissões (conforme PLAN_multi_sector_availability.md):
    - Superusers: acesso a todas as gerências
    - Controle: BLOQUEADO (sem acesso à grade mensal)
    - Com gerencia_id: verifica se usuário pertence à gerência
    - Sem gerencia_id: assume SUPER (comportamento atual)

Cache Redis 5 minutos por (year, month, role, gerencia_id, sector, q).
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false

from __future__ import annotations

from typing import Any

from django.core.cache import cache
from django.db.models import QuerySet
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import HasSectorAccess
from apps.core.services.monthly_grid_service import build_monthly_grid


class MonthlyAvailabilityView(APIView):
    """
    API para consultar grade mensal de disponibilidade.

    GET /api/availability/monthly?year=2025&month=10&role=FORMADOR[&gerencia_id=2][&sector=...][&q=...]

    Permissões (conforme PLAN_multi_sector_availability.md):
        - Superusers: acesso a todas as gerências
        - Controle: BLOQUEADO
        - Com gerencia_id: verifica se usuário pertence à gerência
        - Sem gerencia_id: assume SUPER (comportamento atual)

    Returns:
        {
            "days": int,
            "legend": {...},
            "people": [...],
            "cells": {...},
            "details_index": {...}
        }
    """

    permission_classes = [IsAuthenticated, HasSectorAccess]

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
        # Se não fornecido, gerencia_id permanece None (assume SUPER no service)

        # Cache key (incluindo gerencia_id)
        cache_key = (
            f"monthly:v3:{year}:{month}:{role}:"
            f"{gerencia_id or 'all'}:{sector or '*'}:"
            f"{(q or '').strip().lower()}"
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
            )
        except Exception as e:
            return Response(
                {"error": f"Erro ao compor grade mensal: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Armazenar no cache (5 minutos = 300 segundos)
        cache.set(cache_key, data, 300)

        return Response(data)
