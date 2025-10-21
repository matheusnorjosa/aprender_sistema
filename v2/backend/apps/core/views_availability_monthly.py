"""
API View para grade mensal de disponibilidade.

Endpoint: GET /api/availability/monthly
Query params:
    - year: int (YYYY)
    - month: int (1..12)
    - role: str ("FORMADOR" | "COORDENADOR")
    - sector: str (opcional)
    - q: str (opcional, filtro por nome/email)

Cache Redis 5 minutos por (year, month, role, sector, q).
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.core.cache import cache

from apps.core.services.monthly_grid_service import build_monthly_grid


class MonthlyAvailabilityView(APIView):
    """
    API para consultar grade mensal de disponibilidade.

    GET /api/availability/monthly?year=2025&month=10&role=FORMADOR[&sector=...][&q=...]

    Returns:
        {
            "days": int,
            "legend": {...},
            "people": [...],
            "cells": {...},
            "details_index": {...}
        }
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Validação de parâmetros
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

        # Cache key
        cache_key = f"monthly:v1:{year}:{month}:{role}:{sector or '*'}:{(q or '').strip().lower()}"

        # Tentar buscar do cache
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        # Compor grade
        try:
            data = build_monthly_grid(
                year=year, month=month, role=role, sector=sector, q=q
            )
        except Exception as e:
            return Response(
                {"error": f"Erro ao compor grade mensal: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Armazenar no cache (5 minutos = 300 segundos)
        cache.set(cache_key, data, 300)

        return Response(data)
