"""
DRF Views para AcaoDAT (legacy).

Endpoints:
- GET /api/dat/acoes/ - Lista AcaoDAT
- POST /api/dat/acoes/ - Cria AcaoDAT
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false

from __future__ import annotations

from typing import Any

from django.db.models import QuerySet
from rest_framework import generics, status
from rest_framework.request import Request
from rest_framework.response import Response

from .models import AcaoDAT
from .permissions import HasPerm
from .serializers import AcaoDATCreateSerializer, AcaoDATSerializer


class DATAcoesListCreateView(generics.ListCreateAPIView):
    """
    Lista e cria AcaoDAT.

    Permissão: HasPerm("manage_admin_registries") (grupos DAT ou Superintendência/superuser)

    GET: Lista todas as ações DAT
    POST: Cria nova ação DAT

    Serializers:
        - GET: AcaoDATSerializer (StringRelatedField para FKs)
        - POST: AcaoDATCreateSerializer (FK IDs nativos)

    Query params opcionais (GET):
        projeto: ID do projeto (filtro exato)
        municipio: ID do município (filtro exato)
        tipo_acao: Texto do tipo de ação (filtro icontains)
        data_inicio: YYYY-MM-DD - filtra data_registro >= data_inicio
        data_fim: YYYY-MM-DD - filtra data_registro <= data_fim

    Body (POST):
        {
            "municipio": <id>,
            "projeto": <id>,
            "tipo_acao": "...",
            "responsavel": <id>,  # opcional
            "observacao": "...",  # opcional
            "data_registro": "YYYY-MM-DD"  # opcional
        }
    """

    permission_classes = [HasPerm("manage_admin_registries")]
    queryset = AcaoDAT.objects.select_related("municipio", "projeto", "responsavel").order_by(
        "-data_registro", "municipio_id"
    )

    def get_serializer_class(self):
        """
        Retorna serializer apropriado para a ação.
        GET → AcaoDATSerializer (read)
        POST → AcaoDATCreateSerializer (write)
        """
        if self.request.method == "POST":
            return AcaoDATCreateSerializer
        return AcaoDATSerializer

    def get_queryset(self) -> QuerySet:
        """
        Filtra por query params opcionais.
        """
        queryset = super().get_queryset()

        # Filtros exatos
        projeto_id = self.request.query_params.get("projeto")
        if projeto_id:
            queryset = queryset.filter(projeto_id=projeto_id)

        municipio_id = self.request.query_params.get("municipio")
        if municipio_id:
            queryset = queryset.filter(municipio_id=municipio_id)

        # Filtro parcial (icontains)
        tipo_acao = self.request.query_params.get("tipo_acao")
        if tipo_acao:
            queryset = queryset.filter(tipo_acao__icontains=tipo_acao)

        # Filtros de data
        data_inicio = self.request.query_params.get("data_inicio")
        if data_inicio:
            queryset = queryset.filter(data_registro__gte=data_inicio)

        data_fim = self.request.query_params.get("data_fim")
        if data_fim:
            queryset = queryset.filter(data_registro__lte=data_fim)

        return queryset

    def create(self, request, *args, **kwargs):
        """
        Cria AcaoDAT e retorna com serializer de leitura.
        """
        # Validar e criar com serializer de escrita
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        # Retornar com serializer de leitura (StringRelatedField)
        read_serializer = AcaoDATSerializer(instance)
        headers = self.get_success_headers(read_serializer.data)

        return Response(read_serializer.data, status=status.HTTP_201_CREATED, headers=headers)
