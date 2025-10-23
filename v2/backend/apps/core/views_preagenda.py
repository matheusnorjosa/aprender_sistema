"""
Pre-agenda API Views - Lista solicitações aprovadas com filtros por fluxo.
"""

from rest_framework import generics
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

    def get_queryset(self):
        """Retorna apenas solicitações aprovadas, com filtros opcionais."""
        queryset = Solicitacao.objects.filter(status='aprovado').select_related(
            'usuario', 'municipio', 'projeto', 'tipo_evento', 'coordenador'
        ).prefetch_related('participations__usuario')

        # Filtro por fluxo do projeto
        super_param = self.request.query_params.get('super')
        if super_param == '1':
            # Apenas projetos SUPER
            queryset = queryset.filter(projeto__fluxo='SUPER')
        elif super_param == '0':
            # Apenas projetos NAO_SUPER
            queryset = queryset.filter(projeto__fluxo='NAO_SUPER')

        return queryset.order_by('-created_at')

    def list(self, request, *args, **kwargs):
        """Override para retornar formato paginado com count."""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)

        return Response({
            'count': queryset.count(),
            'results': serializer.data
        })
