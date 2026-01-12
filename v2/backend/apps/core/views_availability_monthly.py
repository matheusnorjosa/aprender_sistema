"""
API View para grade mensal de disponibilidade.

Endpoint: GET /api/availability/monthly
Query params:
    - year: int (YYYY)
    - month: int (1..12)
    - role: str ("FORMADOR" | "COORDENADOR")
    - gerencia_id: int (opcional para superusers, obrigatório para outros)
    - sector: str (opcional, filtro por projeto.nome dentro da gerência)
    - q: str (opcional, filtro por nome/email)

Permissões:
    - Superusers: acesso a todas as gerências
    - Controle: BLOQUEADO (sem acesso à grade mensal)
    - Outros: apenas à própria gerência (via EquipeGerencia)

Cache Redis 5 minutos por (year, month, role, gerencia_id, sector, q).
"""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false

from __future__ import annotations
from typing import Any
from django.db.models import QuerySet
from rest_framework.request import Request
from rest_framework.response import Response

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.core.cache import cache

from apps.core.models import EquipeGerencia
from apps.core.permissions import HasSectorAccess
from apps.core.services.monthly_grid_service import build_monthly_grid


def get_user_gerencia_id(user) -> int | None:
    """
    Retorna o ID da primeira gerência do usuário (via EquipeGerencia).
    Usado para default quando não especificado e usuário não é superuser.
    """
    equipe = EquipeGerencia.objects.filter(usuario=user).first()
    return equipe.gerencia_id if equipe else None


class MonthlyAvailabilityView(APIView):
    """
    API para consultar grade mensal de disponibilidade.

    GET /api/availability/monthly?year=2025&month=10&role=FORMADOR&gerencia_id=2[&sector=...][&q=...]

    Permissões:
        - Superusers: acesso a todas as gerências (gerencia_id opcional)
        - Controle: BLOQUEADO
        - Outros: apenas à própria gerência (gerencia_id obrigatório ou default)

    Returns:
        {
            "days": int,
            "legend": {...},
            "people": [...],
            "cells": {...},
            "details_index": {...}
        }
    """

    def get_permissions(self):
        """
        Retorna permissões dinâmicas.
        Superusers usam apenas IsAuthenticated.
        Outros usam HasSectorAccess.
        """
        # Verificar se é superuser (antes de check_permissions)
        if hasattr(self, 'request') and self.request.user.is_superuser:
            return [IsAuthenticated()]
        return [IsAuthenticated(), HasSectorAccess()]

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

        # Obter gerencia_id
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
        elif not request.user.is_superuser:
            # Para não-superusers sem gerencia_id, usar a gerência do usuário
            gerencia_id = get_user_gerencia_id(request.user)
            if gerencia_id is None:
                return Response(
                    {"error": "Usuário não está vinculado a nenhuma gerência."},
                    status=status.HTTP_403_FORBIDDEN,
                )

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
