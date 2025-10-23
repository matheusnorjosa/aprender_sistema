"""
GCal Dashboard Views (PR14 - Ajustes pós-merge)

4 endpoints para painel de publicação com contrato padronizado:
- GET /api/gcal/status-summary/ - resumo de contadores
- GET /api/gcal/list/ - listagem com filtros
- GET /api/gcal/drift/ - detecção de drift
- POST /api/gcal/reapply/ - republicação em massa

Todos restritos a grupos Controle/Superintendência.
Suportam filtros: date_from, date_to, sector, q, status (gcal_status).
"""

import logging
from datetime import date

from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Solicitacao
from .permissions import IsControleOrSuper
from .serializers import SolicitacaoSerializer
from .services.gcal_sync_service import compute_payload_hash

logger = logging.getLogger(__name__)


def _apply_common_filters(qs, request):
    """
    Aplica filtros comuns a todos os endpoints GCal.

    Filtros suportados:
    - date_from (YYYY-MM-DD): início >= date_from
    - date_to (YYYY-MM-DD): início <= date_to
    - sector: projeto__nome__icontains
    - q: busca em múltiplos campos
    - status: filtra por gcal_status (NONE/PENDING/PUBLISHED/ERROR)
    """
    # Filtro por datas
    date_from = request.query_params.get('date_from')
    if date_from:
        try:
            date_from_parsed = date.fromisoformat(date_from)
            qs = qs.filter(inicio__date__gte=date_from_parsed)
        except (ValueError, TypeError):
            pass

    date_to = request.query_params.get('date_to')
    if date_to:
        try:
            date_to_parsed = date.fromisoformat(date_to)
            qs = qs.filter(inicio__date__lte=date_to_parsed)
        except (ValueError, TypeError):
            pass

    # Filtro por setor (projeto)
    sector = request.query_params.get('sector')
    if sector:
        qs = qs.filter(projeto__nome__icontains=sector)

    # Filtro por gcal_status
    gcal_status_filter = request.query_params.get('status')
    if gcal_status_filter:
        qs = qs.filter(gcal_status=gcal_status_filter)

    # Busca textual
    q = request.query_params.get('q')
    if q:
        qs = qs.filter(
            Q(municipio__nome__icontains=q) |
            Q(projeto__nome__icontains=q) |
            Q(tipo_evento__nome__icontains=q) |
            Q(observacoes__icontains=q) |
            Q(usuario__first_name__icontains=q) |
            Q(usuario__last_name__icontains=q) |
            Q(usuario__username__icontains=q)
        )

    return qs


class GCalStatusSummaryView(APIView):
    """
    GET /api/gcal/status-summary/

    Retorna resumo de contadores por gcal_status.
    Suporta filtros: date_from, date_to, sector, q, status.

    Response:
    {
        "counts": {
            "NONE": 10,
            "PENDING": 2,
            "PUBLISHED": 150,
            "ERROR": 1
        },
        "total": 163
    }
    """
    permission_classes = [IsAuthenticated, IsControleOrSuper]

    def get(self, request):
        # Base queryset: apenas solicitações aprovadas
        qs = Solicitacao.objects.filter(status='aprovado')

        # Aplicar filtros comuns
        qs = _apply_common_filters(qs, request)

        # Agregar contadores por gcal_status
        summary = qs.values('gcal_status').annotate(count=Count('id'))

        # Transformar em dict
        counts = {item['gcal_status']: item['count'] for item in summary}

        # Garantir todas as chaves existem
        for status_key in ['NONE', 'PENDING', 'PUBLISHED', 'ERROR']:
            if status_key not in counts:
                counts[status_key] = 0

        return Response({
            'counts': counts,
            'total': sum(counts.values())
        })


class GCalListView(APIView):
    """
    GET /api/gcal/list/

    Lista solicitações aprovadas com campos GCal expostos.
    Suporta filtros: date_from, date_to, sector, q, status.

    Response:
    {
        "results": [...],  # SolicitacaoSerializer com campos gcal
        "count": 150
    }
    """
    permission_classes = [IsAuthenticated, IsControleOrSuper]

    def get(self, request):
        # Base queryset: apenas aprovadas
        qs = Solicitacao.objects.filter(status='aprovado').select_related(
            'usuario', 'municipio', 'tipo_evento', 'projeto'
        )

        # Aplicar filtros comuns
        qs = _apply_common_filters(qs, request)

        # Ordenação: mais recentes primeiro
        qs = qs.order_by('-inicio', '-id')

        # Limitar a 500 resultados (performance)
        qs = qs[:500]

        # Serializar
        serializer = SolicitacaoSerializer(qs, many=True)

        return Response({
            'results': serializer.data,
            'count': len(serializer.data)
        })


class GCalDriftView(APIView):
    """
    GET /api/gcal/drift/

    Detecta solicitações publicadas cujo payload mudou (drift).
    Suporta filtros: date_from, date_to, sector, q.

    Response:
    {
        "count": 5,
        "items": [
            {
                "id": 123,
                "inicio": "2025-10-15T08:00:00-03:00",
                "fim": "2025-10-15T12:00:00-03:00",
                "municipio": "Fortaleza",
                "projeto": "Gestão Escolar",
                "stored_hash": "abc123...",
                "current_hash": "def456...",
                "external_event_id": "asv2-123"
            },
            ...
        ]
    }
    """
    permission_classes = [IsAuthenticated, IsControleOrSuper]

    def get(self, request):
        # Base queryset: apenas PUBLISHED
        qs = Solicitacao.objects.filter(
            status='aprovado',
            gcal_status=Solicitacao.GCalStatus.PUBLISHED
        ).select_related('municipio', 'projeto')

        # Aplicar filtros comuns (exceto status, já filtrado)
        date_from = request.query_params.get('date_from')
        if date_from:
            try:
                date_from_parsed = date.fromisoformat(date_from)
                qs = qs.filter(inicio__date__gte=date_from_parsed)
            except (ValueError, TypeError):
                pass

        date_to = request.query_params.get('date_to')
        if date_to:
            try:
                date_to_parsed = date.fromisoformat(date_to)
                qs = qs.filter(inicio__date__lte=date_to_parsed)
            except (ValueError, TypeError):
                pass

        sector = request.query_params.get('sector')
        if sector:
            qs = qs.filter(projeto__nome__icontains=sector)

        q = request.query_params.get('q')
        if q:
            qs = qs.filter(
                Q(municipio__nome__icontains=q) |
                Q(projeto__nome__icontains=q)
            )

        # Detectar drift (comparar hashes)
        drift_items = []
        for s in qs:
            current_hash = compute_payload_hash(s)
            if s.gcal_payload_hash != current_hash:
                drift_items.append({
                    'id': s.id,
                    'inicio': s.inicio.isoformat(),
                    'fim': s.fim.isoformat(),
                    'municipio': s.municipio.nome if s.municipio else '',
                    'projeto': s.projeto.nome if s.projeto else '',
                    'stored_hash': s.gcal_payload_hash,
                    'current_hash': current_hash,
                    'external_event_id': s.external_event_id or f'asv2-{s.id}',
                })

        return Response({
            'count': len(drift_items),
            'items': drift_items
        })


class GCalBulkReapplyView(APIView):
    """
    POST /api/gcal/reapply/

    Reenfileira publicação para lista de IDs.

    Request body:
    {
        "ids": [1, 2, 3],
        "dry_run": false
    }

    Response:
    {
        "queued": 3,
        "errors": [],  # Lista de {id, detail}
        "dry_run": false
    }
    """
    permission_classes = [IsAuthenticated, IsControleOrSuper]

    def post(self, request):
        from apps.core.tasks import task_publish_solicitacao_to_gcal

        ids = request.data.get('ids', [])
        dry_run = request.data.get('dry_run', False)

        if not ids:
            return Response(
                {'detail': 'Campo ids é obrigatório'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validar que todas são aprovadas
        qs = Solicitacao.objects.filter(id__in=ids, status='aprovado')
        found_ids = set(qs.values_list('id', flat=True))
        requested_ids = set(ids)

        # Detectar IDs inválidos
        invalid_ids = requested_ids - found_ids
        errors = []
        for invalid_id in invalid_ids:
            errors.append({
                'id': invalid_id,
                'detail': 'ID não encontrado ou não está aprovado'
            })

        # Marcar como PENDING e enfileirar
        queued = 0
        for s in qs:
            if not dry_run:
                s.mark_gcal(
                    status=Solicitacao.GCalStatus.PENDING,
                    payload_hash=None,
                    error=''
                )

            task_publish_solicitacao_to_gcal.delay(s.id, dry_run=dry_run, apply_blocked=False)
            queued += 1

        return Response({
            'queued': queued,
            'errors': errors,
            'dry_run': dry_run
        }, status=status.HTTP_202_ACCEPTED if queued > 0 else status.HTTP_200_OK)
