"""
Endpoint DRF para listagem de Compras.

GET /api/controle/compras/
- Permission: IsControleOrSuper
- Query params: municipio, projeto, uf, from, to, q
- Returns: Lista de compras com campos relacionados
"""

from __future__ import annotations
from typing import Any
from django.db.models import QuerySet
from rest_framework.request import Request
from rest_framework.response import Response

from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers
from django.db.models import Q

from apps.core.permissions import IsControleOrSuper
from apps.core.models import Compra


class CompraSerializer(serializers.ModelSerializer):
    """
    Serializer para Compra com campos relacionados.
    """
    municipio = serializers.CharField(source="municipio.nome", read_only=True)
    uf = serializers.CharField(source="municipio.uf", read_only=True)
    projeto = serializers.CharField(source="projeto.nome", read_only=True)

    class Meta:
        model = Compra
        fields = (
            "id",
            "codigo",
            "projeto",
            "municipio",
            "uf",
            "quantidade",
            "data",
            "uso",
            "created_at",
        )


class ControleComprasListView(ListAPIView):
    """
    Lista Compras com filtros opcionais.

    Requer permissão: IsControleOrSuper (grupos Controle ou Superintendência)

    Query params:
        municipio: Filtro por nome do município (icontains)
        projeto: Filtro por nome do projeto (icontains)
        uf: Filtro por UF do município (iexact)
        from: Filtro por data >= (YYYY-MM-DD)
        to: Filtro por data <= (YYYY-MM-DD)
        q: Busca textual em uso ou código (icontains)

    Returns:
        [
            {
                "id": 1,
                "codigo": "C001",
                "projeto": "ACerta",
                "municipio": "Fortaleza",
                "uf": "CE",
                "quantidade": 100,
                "data": "2025-01-15",
                "uso": "Formação",
                "created_at": "2025-10-21T..."
            },
            ...
        ]
    """
    permission_classes = [IsAuthenticated, IsControleOrSuper]
    serializer_class = CompraSerializer

    def get_queryset(self) -> QuerySet:
        # Queryset base com related fields otimizados
        qs = Compra.objects.select_related("municipio", "projeto").order_by(
            "-data", "-created_at"
        )

        # Aplicar filtros opcionais
        params = self.request.query_params

        if params.get("municipio"):
            qs = qs.filter(municipio__nome__icontains=params["municipio"])

        if params.get("projeto"):
            qs = qs.filter(projeto__nome__icontains=params["projeto"])

        if params.get("uf"):
            qs = qs.filter(municipio__uf__iexact=params["uf"])

        if params.get("from"):
            qs = qs.filter(data__gte=params["from"])

        if params.get("to"):
            qs = qs.filter(data__lte=params["to"])

        if params.get("q"):
            q_value = params["q"]
            qs = qs.filter(
                Q(uso__icontains=q_value) | Q(codigo__icontains=q_value)
            )

        return qs
