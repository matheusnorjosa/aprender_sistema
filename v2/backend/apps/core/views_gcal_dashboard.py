"""
GCal Dashboard Views (PR14 - Ajustes pós-merge + Fase 2 batch publish)

3 endpoints para painel de publicação com contrato padronizado:
- GET /api/gcal/status-summary/ - resumo de contadores
- GET /api/gcal/list/ - listagem com filtros
- GET /api/gcal/drift/ - detecção de drift
- POST /api/gcal/publish-batch/ - publicação em massa (Fase 2)

Todos restritos a grupos Controle/Superintendência.
Suportam filtros: date_from, date_to, sector, q, status (gcal_status).

Nota: Publicação de eventos no Google Calendar ocorre via página /pre-agenda:
- Individual: botão "Publicar" (POST /api/solicitacoes/{id}/publish/)
- Em massa: botão "Publicar Selecionados" (POST /api/gcal/publish-batch/)
"""

import logging
import os
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


class GCalPublishBatchView(APIView):
    """
    POST /api/gcal/publish-batch/

    Publicação em massa de solicitações aprovadas no Google Calendar.
    Restrict: Controle/Superintendência

    Request Body:
    {
        "solicitacao_ids": [123, 456, 789],  // Array de IDs
        "dry_run": false,                     // Opcional (default: false)
        "apply_blocked": false                // Opcional (default: false)
    }

    Response 202 Accepted:
    {
        "queued": 2,                          // Quantidade enfileirada
        "errors": [                           // Lista de erros
            {
                "id": 789,
                "detail": "Status deve ser 'aprovado' (atual: pendente)"
            }
        ],
        "dry_run": false,
        "apply_blocked": false
    }

    Regras:
    - Apenas solicitações com status='aprovado' são processadas
    - Se GCAL_CLIENT != "google" e dry_run=false e apply_blocked=false → erro
    - Válidas: marca gcal_status=PENDING e enfileira task Celery
    - Inválidas: retorna em 'errors' com motivo
    """
    permission_classes = [IsAuthenticated, IsControleOrSuper]

    def post(self, request):
        # Parse request body
        solicitacao_ids = request.data.get('solicitacao_ids', [])
        dry_run = request.data.get('dry_run', False)
        apply_blocked = request.data.get('apply_blocked', False)

        # Validação: array de IDs obrigatório
        if not isinstance(solicitacao_ids, list) or not solicitacao_ids:
            return Response(
                {'detail': 'solicitacao_ids deve ser um array não-vazio de IDs'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Buscar solicitações
        solicitacoes = Solicitacao.objects.filter(id__in=solicitacao_ids).select_related(
            'projeto', 'municipio'
        )

        # Verificar GCAL_CLIENT
        gcal_client = os.getenv('GCAL_CLIENT', 'fake')

        queued = []
        errors = []

        for sol_id in solicitacao_ids:
            # Verificar se existe
            sol = next((s for s in solicitacoes if s.id == sol_id), None)
            if not sol:
                errors.append({
                    'id': sol_id,
                    'detail': 'Solicitação não encontrada'
                })
                continue

            # Validar status='aprovado'
            if sol.status != 'aprovado':
                errors.append({
                    'id': sol_id,
                    'detail': f"Status deve ser 'aprovado' (atual: {sol.status})"
                })
                continue

            # Validar apply_blocked com GCAL_CLIENT
            if gcal_client != 'google' and not dry_run and not apply_blocked:
                errors.append({
                    'id': sol_id,
                    'detail': f'GCAL_CLIENT={gcal_client} (não-google) requer dry_run=true ou apply_blocked=true'
                })
                continue

            # Válida: marcar como PENDING e enfileirar
            if not dry_run:
                sol.gcal_status = Solicitacao.GCalStatus.PENDING
                sol.save(update_fields=['gcal_status', 'updated_at'])

                # Importar e enfileirar task Celery
                try:
                    from .tasks import task_publish_solicitacao_to_gcal
                    task_publish_solicitacao_to_gcal.delay(
                        solicitacao_id=sol.id,
                        dry_run=dry_run,
                        apply_blocked=apply_blocked
                    )
                    queued.append(sol.id)
                    logger.info(f"Batch publish queued: solicitacao_id={sol.id}, dry_run={dry_run}")
                except Exception as e:
                    logger.error(f"Failed to queue solicitacao_id={sol.id}: {e}")
                    errors.append({
                        'id': sol.id,
                        'detail': f'Erro ao enfileirar task: {str(e)}'
                    })
            else:
                # Dry-run: apenas simula
                queued.append(sol.id)
                logger.info(f"Batch publish dry-run: solicitacao_id={sol.id}")

        return Response({
            'queued': len(queued),
            'errors': errors,
            'dry_run': dry_run,
            'apply_blocked': apply_blocked
        }, status=status.HTTP_202_ACCEPTED)
