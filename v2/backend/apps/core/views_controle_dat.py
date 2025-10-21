"""
DRF Views para AcaoControle e AcaoDAT.

Endpoints:
- GET /api/controle/acoes/ - Lista AcaoControle com filtros de data
- GET /api/dat/acoes/ - Lista AcaoDAT
- POST /api/dat/acoes/ - Cria AcaoDAT
"""

from django.db.models import Q
from rest_framework import generics, status
from rest_framework.response import Response

from .models import AcaoControle, AcaoDAT
from .permissions import IsControleOrSuper, IsDATOrSuper
from .serializers import (
    AcaoControleSerializer,
    AcaoDATSerializer,
    AcaoDATCreateSerializer,
)


class ControleAcoesListView(generics.ListAPIView):
    """
    Lista AcaoControle com filtros de data.

    Permissão: IsControleOrSuper (grupos Controle ou Superintendência)

    Query params opcionais:
        data_inicio: YYYY-MM-DD - filtra por qualquer data >= data_inicio
        data_fim: YYYY-MM-DD - filtra por qualquer data <= data_fim

    Campos de data considerados:
        - data_entrega
        - data_carta
        - contato_inicial
        - data_reuniao

    Exemplo:
        GET /api/controle/acoes/?data_inicio=2025-01-01&data_fim=2025-12-31
        Retorna ações onde pelo menos uma das datas está no intervalo
    """

    permission_classes = [IsControleOrSuper]
    serializer_class = AcaoControleSerializer
    queryset = AcaoControle.objects.select_related(
        "municipio", "projeto", "coordenador"
    ).order_by("-data_reuniao", "-data_entrega")

    def get_queryset(self):
        """
        Filtra por data usando Q() para considerar qualquer uma das datas.
        """
        queryset = super().get_queryset()

        # Filtros de data via query params
        data_inicio = self.request.query_params.get("data_inicio")
        data_fim = self.request.query_params.get("data_fim")

        if data_inicio or data_fim:
            # Construir filtro Q() que considera todas as datas
            date_fields = [
                "data_entrega",
                "data_carta",
                "contato_inicial",
                "data_reuniao",
            ]

            q_filter = Q()

            for field in date_fields:
                if data_inicio and data_fim:
                    # Intervalo: data_inicio <= field <= data_fim
                    q_filter |= Q(**{
                        f"{field}__gte": data_inicio,
                        f"{field}__lte": data_fim,
                    })
                elif data_inicio:
                    # Apenas início: field >= data_inicio
                    q_filter |= Q(**{f"{field}__gte": data_inicio})
                elif data_fim:
                    # Apenas fim: field <= data_fim
                    q_filter |= Q(**{f"{field}__lte": data_fim})

            queryset = queryset.filter(q_filter).distinct()

        return queryset


class DATAcoesListCreateView(generics.ListCreateAPIView):
    """
    Lista e cria AcaoDAT.

    Permissão: IsDATOrSuper (grupos DAT ou Superintendência/superuser)

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

    permission_classes = [IsDATOrSuper]
    queryset = AcaoDAT.objects.select_related(
        "municipio", "projeto", "responsavel"
    ).order_by("-data_registro", "municipio_id")

    def get_serializer_class(self):
        """
        Retorna serializer apropriado para a ação.
        GET → AcaoDATSerializer (read)
        POST → AcaoDATCreateSerializer (write)
        """
        if self.request.method == "POST":
            return AcaoDATCreateSerializer
        return AcaoDATSerializer

    def get_queryset(self):
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

        return Response(
            read_serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )
