"""
Views for DAT Ingest app (ETL Observability)

Fase 5 - Desligamento gradual de planilhas
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.core.permissions import IsControleOrSuper
from .services.etl_observability import list_latest_reports


class EtlReportsLatestView(APIView):
    """
    GET /api/etl/reports/latest/

    Lista os relatórios ETL mais recentes.

    Query params:
        - limit: int (1-100, default=20)

    Returns:
        200: Lista de relatórios com metadados
        400: Parâmetro limit inválido
        403: Usuário sem permissão (requer Controle ou Superintendência)

    Permissions:
        - IsControleOrSuper (grupos: Controle, Superintendência ou superuser)

    Fase 5 - ETL Observability
    """

    permission_classes = [IsControleOrSuper]

    def get(self, request):
        """List latest ETL reports"""
        # Parse limit parameter
        limit_str = request.query_params.get('limit', '20')

        try:
            limit = int(limit_str)
        except ValueError:
            return Response(
                {
                    'detail': 'Parâmetro limit deve ser um número inteiro',
                    'param': 'limit',
                    'value': limit_str,
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate limit range
        if not (1 <= limit <= 100):
            return Response(
                {
                    'detail': 'Parâmetro limit deve estar entre 1 e 100',
                    'param': 'limit',
                    'value': limit,
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get reports
        try:
            reports = list_latest_reports(limit=limit)
        except Exception as e:
            # Log error but return empty list (graceful degradation)
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error listing ETL reports: {e}")
            reports = []

        return Response({
            'count': len(reports),
            'limit': limit,
            'reports': reports,
        }, status=status.HTTP_200_OK)
