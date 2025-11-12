"""
Pre-agenda API Views - Lista solicitações aprovadas com filtros por fluxo.
"""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false

from __future__ import annotations

from typing import Any

from django.db.models import QuerySet
from rest_framework import generics
from rest_framework.request import Request
from rest_framework.response import Response

from .models import Solicitacao
from .permissions import IsControleOrDAT
from .serializers import SolicitacaoSerializer


class PreAgendaListView(generics.ListAPIView):
    """
    GET /api/pre-agenda/

    Lista solicitações aprovadas (pré-agenda).

    Query parameters:
    - super: filtrar por fluxo do projeto
      - super=1: apenas projetos SUPER (requerem aprovação)
      - super=0: apenas projetos NAO_SUPER (auto-aprovados)
      - sem filtro: retorna ambos

    Permissions: IsControleOrDAT
    """
    permission_classes = [IsControleOrDAT]
    serializer_class = SolicitacaoSerializer

    def get_queryset(self) -> QuerySet[Solicitacao]:
        """Retorna apenas solicitações aprovadas, com filtros opcionais."""
        queryset: QuerySet[Solicitacao] = Solicitacao.objects.filter(status='aprovado').select_related(
            'usuario', 'municipio', 'projeto', 'tipo_evento', 'coordenador'
        ).prefetch_related('participations__usuario')

        # Filtro por fluxo do projeto
        super_param: str | None = self.request.query_params.get('super')
        if super_param == '1':
            # Apenas projetos SUPER
            queryset = queryset.filter(projeto__fluxo='SUPER')
        elif super_param == '0':
            # Apenas projetos NAO_SUPER
            queryset = queryset.filter(projeto__fluxo='NAO_SUPER')

        return queryset.order_by('-created_at')

    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Override para retornar formato paginado com count."""
        queryset: QuerySet[Solicitacao] = self.get_queryset()
        serializer: SolicitacaoSerializer = self.get_serializer(queryset, many=True)

        return Response({
            'count': queryset.count(),
            'results': serializer.data
        })
