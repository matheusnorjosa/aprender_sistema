"""
GCal Dashboard Views (PR14 - Ajustes pós-merge + Fase 2 batch publish + Sprint 5)

Endpoints para painel de publicação com contrato padronizado:
- GET /api/gcal/status-summary/ - resumo de contadores
- GET /api/gcal/list/ - listagem com filtros
- GET /api/gcal/drift/ - detecção de drift
- POST /api/gcal/publish-batch/ - publicação em massa (Fase 2)

Sprint 5 - Dashboard/Monitoring:
- GET /api/gcal/dashboard/metrics/ - métricas + recent_errors (com start/end)
- GET /api/gcal/dashboard/events/ - lista paginada (DRF PageNumberPagination)

Todos restritos a grupos Controle/Superintendência.
Suportam filtros: date_from, date_to, sector, q, status (gcal_status).

Nota: Publicação de eventos no Google Calendar ocorre via página /pre-agenda:
- Individual: botão "Publicar" (POST /api/solicitacoes/{id}/publish/)
- Em massa: botão "Publicar Selecionados" (POST /api/gcal/publish-batch/)
"""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false, reportFunctionMemberAccess=false

from __future__ import annotations
from typing import Any
from django.db.models import QuerySet
from rest_framework.request import Request
from rest_framework.response import Response

import csv
import logging
import os
from datetime import date, datetime, timezone as dt_timezone
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db.models import Count, Q
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Solicitacao
from .permissions import IsControleOrSuper
from .serializers import SolicitacaoSerializer
from .services.gcal_sync_service import compute_payload_hash

logger = logging.getLogger(__name__)


def _filter_events_queryset(request: Request, base_qs: QuerySet[Solicitacao]) -> QuerySet[Solicitacao]:
    """
    Helper unificado para filtrar eventos do Dashboard GCal com lógica timezone-aware.

    Aplica filtros de status, start, end de forma determinística usando timezone local
    (America/Fortaleza) e converte para UTC antes de aplicar no queryset.

    Args:
        request: DRF Request com query params (status, start, end)
        base_qs: QuerySet base de Solicitacao (já com status='aprovado' e select_related)

    Returns:
        QuerySet filtrado e ordenado por updated_at desc

    Filtros suportados:
        - status: gcal_status (NONE/PENDING/PUBLISHED/ERROR)
        - start: Início >= start (formato YYYY-MM-DD, 00:00 local)
        - end: Início <= end (formato YYYY-MM-DD, 23:59:59.999999 local)

    Nota: Evita __date__gte/lte por causa de timezone. Usa inicio__gte/lte com
    datetimes UTC derivados da janela local.
    """
    # Base: apenas aprovadas com select_related
    qs = base_qs.filter(status='aprovado').select_related(
        'usuario', 'municipio', 'tipo_evento', 'projeto'
    )

    # Filtro por status (gcal_status)
    status_param = request.query_params.get('status')
    if status_param:
        qs = qs.filter(gcal_status=status_param)

    # Filtro por janela de datas (timezone-aware)
    start_param = request.query_params.get('start')
    end_param = request.query_params.get('end')

    # Timezone local do projeto (America/Fortaleza)
    tz_local = ZoneInfo(settings.TIME_ZONE)

    if start_param:
        try:
            # Converter data ISO para datetime local 00:00:00
            local_start = datetime.fromisoformat(start_param).replace(
                tzinfo=tz_local,
                hour=0,
                minute=0,
                second=0,
                microsecond=0
            )
            # Converter para UTC
            start_utc = local_start.astimezone(dt_timezone.utc)
            # Aplicar filtro inclusivo
            qs = qs.filter(inicio__gte=start_utc)
        except (ValueError, TypeError):
            # Data inválida: ignorar filtro
            pass

    if end_param:
        try:
            # Converter data ISO para datetime local 23:59:59.999999
            local_end = datetime.fromisoformat(end_param).replace(
                tzinfo=tz_local,
                hour=23,
                minute=59,
                second=59,
                microsecond=999999
            )
            # Converter para UTC
            end_utc = local_end.astimezone(dt_timezone.utc)
            # Aplicar filtro inclusivo
            qs = qs.filter(inicio__lte=end_utc)
        except (ValueError, TypeError):
            # Data inválida: ignorar filtro
            pass

    # Ordenação: updated_at desc, id desc (determinístico)
    qs = qs.order_by('-updated_at', '-id')

    return qs


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

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
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

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
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

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        # Base queryset: apenas PUBLISHED
        # MP4: select_related para evitar N+1 (compute_payload_hash acessa 5 FKs)
        qs = Solicitacao.objects.filter(
            status='aprovado',
            gcal_status=Solicitacao.GCalStatus.PUBLISHED
        ).select_related('municipio', 'projeto', 'tipo_evento', 'usuario', 'coordenador')

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

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
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
        gcal_client = getattr(settings, 'GCAL_CLIENT', 'fake')

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


# ================================================================
# Sprint 5 - Dashboard/Monitoring
# ================================================================

class DashboardMetricsView(APIView):
    """
    GET /api/gcal/dashboard/metrics/

    Retorna métricas de publicação GCal com erros recentes.

    Query params:
    - start (ISO date): Filtro início >= start (formato: YYYY-MM-DD)
    - end (ISO date): Filtro início <= end (formato: YYYY-MM-DD)

    Response:
    {
        "counts": {
            "NONE": 10,
            "PENDING": 2,
            "PUBLISHED": 150,
            "ERROR": 1
        },
        "recent_errors": [
            {
                "id": 789,
                "summary": "Fortaleza - CE Fundamental I Online [ACERTA]",
                "gcal_last_error": "500 Internal Server Error",
                "updated_at": "2025-11-08T10:30:00Z"
            },
            ...
        ],
        "window": {
            "start": "2025-10-01",
            "end": "2025-11-30"
        }
    }

    Permissions: IsControleOrSuper
    """
    permission_classes = [IsAuthenticated, IsControleOrSuper]

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        # Base queryset: apenas solicitações aprovadas
        qs = Solicitacao.objects.filter(status='aprovado')

        # Parse filtros de janela (start/end)
        start_param = request.query_params.get('start')
        end_param = request.query_params.get('end')

        start_date = None
        end_date = None

        if start_param:
            try:
                start_date = date.fromisoformat(start_param)
                qs = qs.filter(inicio__date__gte=start_date)
            except (ValueError, TypeError):
                pass

        if end_param:
            try:
                end_date = date.fromisoformat(end_param)
                qs = qs.filter(inicio__date__lte=end_date)
            except (ValueError, TypeError):
                pass

        # Contadores por gcal_status
        summary = qs.values('gcal_status').annotate(count=Count('id'))
        counts = {item['gcal_status']: item['count'] for item in summary}

        # Garantir todas as chaves existem
        for status_key in ['NONE', 'PENDING', 'PUBLISHED', 'ERROR']:
            if status_key not in counts:
                counts[status_key] = 0

        # Recent errors (top 5, ordenados por updated_at desc)
        error_qs = qs.filter(gcal_status=Solicitacao.GCalStatus.ERROR).select_related(
            'municipio', 'projeto'
        ).order_by('-updated_at')[:5]

        recent_errors = []
        for s in error_qs:
            # Gerar summary simples para exibição
            municipio_nome = s.municipio.nome if s.municipio else ''
            municipio_uf = s.municipio.uf if s.municipio else ''
            projeto_nome = s.projeto.nome if s.projeto else ''
            summary_text = f"{municipio_nome} - {municipio_uf} {projeto_nome}" if municipio_nome else f"Solicitação #{s.id}"

            recent_errors.append({
                'id': s.id,
                'summary': summary_text.strip(),
                'gcal_last_error': s.gcal_last_error or '',
                'updated_at': s.updated_at.isoformat() if s.updated_at else None
            })

        return Response({
            'counts': counts,
            'recent_errors': recent_errors,
            'window': {
                'start': start_date.isoformat() if start_date else None,
                'end': end_date.isoformat() if end_date else None
            }
        })


class DashboardEventsPagination(PageNumberPagination):
    """Paginação customizada para dashboard events"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class DashboardEventsView(APIView):
    """
    GET /api/gcal/dashboard/events/

    Lista paginada de eventos com campos GCal essenciais.

    Query params:
    - status: Filtro por gcal_status (NONE/PENDING/PUBLISHED/ERROR)
    - start (ISO date): Filtro início >= start (formato: YYYY-MM-DD)
    - end (ISO date): Filtro início <= end (formato: YYYY-MM-DD)
    - page: Número da página (default: 1)
    - page_size: Itens por página (default: 20, max: 100)

    Response:
    {
        "count": 150,
        "next": "http://localhost:8000/api/gcal/dashboard/events/?page=2",
        "previous": null,
        "results": [
            {
                "id": 123,
                "summary": "...",
                "gcal_status": "PUBLISHED",
                "gcal_last_error": "",
                "gcal_last_sync_at": "2025-11-08T10:00:00Z",
                ...
            },
            ...
        ]
    }

    Permissions: IsControleOrSuper
    """
    permission_classes = [IsAuthenticated, IsControleOrSuper]

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        # Usar helper unificado timezone-aware (Issue #96 follow-up #124)
        qs = _filter_events_queryset(request, Solicitacao.objects.all())

        # Paginação DRF
        paginator = DashboardEventsPagination()
        page = paginator.paginate_queryset(qs, request)

        if page is not None:
            serializer = SolicitacaoSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        # Fallback sem paginação (não deveria acontecer)
        serializer = SolicitacaoSerializer(qs, many=True)
        return Response(serializer.data)


# ================================================================
# Issue #95 - Batch Reapply/Resync
# ================================================================

class GCalBatchReapplyView(APIView):
    """
    POST /api/gcal/dashboard/batch/reapply/

    Reaplica eventos já publicados (não reseta hash).
    Útil para forçar update no Google Calendar sem alterar o estado local.

    Request Body:
    {
        "ids": [123, 456, 789],      // Array de IDs (max 500)
        "dry_run": false,             // Opcional (default: false)
        "apply_blocked": false        // Opcional (default: false)
    }

    Response 202 Accepted:
    {
        "queued": 2,
        "errors": [
            {"id": 789, "detail": "Solicitação não encontrada"}
        ],
        "dry_run": false,
        "apply_blocked": false
    }

    OAuth Mode:
    - Se GCAL_AUTH_MODE=='oauth', requer GoogleOAuthCredential
    - Sem credencial → 403 {code: 'google_not_connected'}
    - Com credencial → passa operator_user_id para task

    Permissions: IsControleOrSuper
    """
    permission_classes = [IsAuthenticated, IsControleOrSuper]

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        from django.conf import settings
        from .models import GoogleOAuthCredential
        from .tasks import task_publish_solicitacao_to_gcal

        # OAuth Phase 7: Verificar credencial Google em modo OAuth
        auth_mode = getattr(settings, "GCAL_AUTH_MODE", "service_account")
        operator_user_id = None

        if auth_mode == "oauth":
            try:
                GoogleOAuthCredential.objects.get(user=request.user)
                operator_user_id = request.user.id
            except GoogleOAuthCredential.DoesNotExist:
                return Response(
                    {
                        "detail": "Conecte sua conta Google para realizar ações em massa",
                        "code": "google_not_connected"
                    },
                    status=status.HTTP_403_FORBIDDEN
                )

        # Parse request body
        ids = request.data.get('ids', [])
        dry_run = request.data.get('dry_run', False)
        apply_blocked = request.data.get('apply_blocked', False)

        # Validação: array de IDs obrigatório
        if not isinstance(ids, list) or not ids:
            return Response(
                {'detail': 'ids deve ser um array não-vazio de IDs'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Limitar a 500 IDs
        if len(ids) > 500:
            return Response(
                {'detail': 'Limite de 500 IDs por requisição'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Buscar solicitações
        solicitacoes = Solicitacao.objects.filter(id__in=ids)

        # MP4: Otimização O(N) - dict lookup em vez de linear search O(N²)
        solicitacoes_dict = {s.id: s for s in solicitacoes}

        # Verificar GCAL_CLIENT
        gcal_client = getattr(settings, 'GCAL_CLIENT', 'fake')

        queued_count = 0
        errors = []

        for sol_id in ids:
            # Verificar se existe (O(1) dict lookup)
            sol = solicitacoes_dict.get(sol_id)
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
                    'detail': f'GCAL_CLIENT={gcal_client} requer dry_run=true ou apply_blocked=true'
                })
                continue

            # Válida: enfileirar (reapply não reseta hash)
            if not dry_run:
                try:
                    # OAuth mode: passar operator_user_id
                    if auth_mode == "oauth":
                        task_publish_solicitacao_to_gcal.delay(
                            sol.id,
                            dry_run=dry_run,
                            apply_blocked=apply_blocked,
                            operator_user_id=operator_user_id
                        )
                    else:
                        # Service account mode: sem operator_user_id
                        task_publish_solicitacao_to_gcal.delay(
                            sol.id,
                            dry_run=dry_run,
                            apply_blocked=apply_blocked
                        )
                    queued_count += 1
                    logger.info(f"Batch reapply queued: id={sol.id}, operator={operator_user_id}")
                except Exception as e:
                    logger.error(f"Failed to queue reapply id={sol.id}: {e}")
                    errors.append({
                        'id': sol.id,
                        'detail': f'Erro ao enfileirar: {str(e)}'
                    })
            else:
                # Dry-run: apenas simula
                queued_count += 1

        return Response({
            'queued': queued_count,
            'errors': errors,
            'dry_run': dry_run,
            'apply_blocked': apply_blocked
        }, status=status.HTTP_202_ACCEPTED)


class GCalBatchResyncView(APIView):
    """
    POST /api/gcal/dashboard/batch/resync/

    Força resync de eventos (reseta hash + marca PENDING).
    Útil para corrigir drift ou reprocessar eventos com erros.

    Request Body:
    {
        "ids": [123, 456, 789],      // Array de IDs (max 500)
        "dry_run": false,             // Opcional (default: false)
        "apply_blocked": false        // Opcional (default: false)
    }

    Response 202 Accepted:
    {
        "queued": 2,
        "errors": [
            {"id": 789, "detail": "Solicitação não encontrada"}
        ],
        "dry_run": false,
        "apply_blocked": false
    }

    OAuth Mode:
    - Se GCAL_AUTH_MODE=='oauth', requer GoogleOAuthCredential
    - Sem credencial → 403 {code: 'google_not_connected'}
    - Com credencial → passa operator_user_id para task

    Permissions: IsControleOrSuper
    """
    permission_classes = [IsAuthenticated, IsControleOrSuper]

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        from django.conf import settings
        from .models import GoogleOAuthCredential
        from .tasks import task_publish_solicitacao_to_gcal

        # OAuth Phase 7: Verificar credencial Google em modo OAuth
        auth_mode = getattr(settings, "GCAL_AUTH_MODE", "service_account")
        operator_user_id = None

        if auth_mode == "oauth":
            try:
                GoogleOAuthCredential.objects.get(user=request.user)
                operator_user_id = request.user.id
            except GoogleOAuthCredential.DoesNotExist:
                return Response(
                    {
                        "detail": "Conecte sua conta Google para realizar ações em massa",
                        "code": "google_not_connected"
                    },
                    status=status.HTTP_403_FORBIDDEN
                )

        # Parse request body
        ids = request.data.get('ids', [])
        dry_run = request.data.get('dry_run', False)
        apply_blocked = request.data.get('apply_blocked', False)

        # Validação: array de IDs obrigatório
        if not isinstance(ids, list) or not ids:
            return Response(
                {'detail': 'ids deve ser um array não-vazio de IDs'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Limitar a 500 IDs
        if len(ids) > 500:
            return Response(
                {'detail': 'Limite de 500 IDs por requisição'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Buscar solicitações
        solicitacoes = Solicitacao.objects.filter(id__in=ids)

        # MP4: Otimização O(N) - dict lookup em vez de linear search O(N²)
        solicitacoes_dict = {s.id: s for s in solicitacoes}

        # Verificar GCAL_CLIENT
        gcal_client = getattr(settings, 'GCAL_CLIENT', 'fake')

        queued_count = 0
        errors = []

        for sol_id in ids:
            # Verificar se existe (O(1) dict lookup)
            sol = solicitacoes_dict.get(sol_id)
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
                    'detail': f'GCAL_CLIENT={gcal_client} requer dry_run=true ou apply_blocked=true'
                })
                continue

            # Válida: resetar hash + marcar PENDING + enfileirar
            if not dry_run:
                try:
                    # Resync: resetar hash para forçar reprocessamento
                    sol.gcal_payload_hash = None
                    sol.gcal_status = Solicitacao.GCalStatus.PENDING
                    sol.save(update_fields=['gcal_payload_hash', 'gcal_status', 'updated_at'])

                    # OAuth mode: passar operator_user_id
                    if auth_mode == "oauth":
                        task_publish_solicitacao_to_gcal.delay(
                            sol.id,
                            dry_run=dry_run,
                            apply_blocked=apply_blocked,
                            operator_user_id=operator_user_id
                        )
                    else:
                        # Service account mode: sem operator_user_id
                        task_publish_solicitacao_to_gcal.delay(
                            sol.id,
                            dry_run=dry_run,
                            apply_blocked=apply_blocked
                        )
                    queued_count += 1
                    logger.info(f"Batch resync queued: id={sol.id}, operator={operator_user_id}")
                except Exception as e:
                    logger.error(f"Failed to queue resync id={sol.id}: {e}")
                    errors.append({
                        'id': sol.id,
                        'detail': f'Erro ao enfileirar: {str(e)}'
                    })
            else:
                # Dry-run: apenas simula
                queued_count += 1

        return Response({
            'queued': queued_count,
            'errors': errors,
            'dry_run': dry_run,
            'apply_blocked': apply_blocked
        }, status=status.HTTP_202_ACCEPTED)


# ================================================================
# Issue #96 - Export CSV/JSON
# ================================================================

class DashboardEventsExportView(APIView):
    """
    GET /api/gcal/dashboard/events/export/

    Exporta eventos do Dashboard GCal em CSV ou JSON.

    Query params:
    - status: Filtro por gcal_status (NONE/PENDING/PUBLISHED/ERROR)
    - start (ISO date): Filtro início >= start (formato: YYYY-MM-DD)
    - end (ISO date): Filtro início <= end (formato: YYYY-MM-DD)
    - format: csv|json (default: csv)

    CSV Response:
    - Content-Type: text/csv; charset=utf-8
    - Content-Disposition: attachment; filename=gcal_events_{YYYYMMDD}.csv
    - BOM UTF-8 para compatibilidade Excel
    - Separador ","
    - Datas em ISO 8601

    JSON Response:
    - Content-Type: application/json
    - Estrutura: {count, results} (sem paginação)

    Permissions: IsControleOrSuper
    """
    permission_classes = [IsAuthenticated, IsControleOrSuper]

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response | HttpResponse:
        # Usar helper unificado timezone-aware (Issue #96 follow-up #124)
        # MP4: select_related para evitar N+1 em CSV export (.iterator() bypassa cache)
        qs = _filter_events_queryset(
            request,
            Solicitacao.objects.select_related(
                'municipio', 'projeto', 'tipo_evento', 'usuario', 'coordenador'
            )
        )

        # Determinar formato (default: csv)
        # Usamos 'export_format' em vez de 'format' para evitar conflito com DRF content negotiation
        export_format = request.query_params.get('export_format', request.query_params.get('format', 'csv')).lower()

        if export_format == 'json':
            return self._export_json(qs)
        else:
            return self._export_csv(qs)

    def _export_csv(self, qs: QuerySet[Solicitacao]) -> HttpResponse:
        """Exporta queryset como CSV com BOM UTF-8 para Excel"""
        # Gerar nome do arquivo com timestamp
        today = date.today().strftime('%Y%m%d')
        filename = f'gcal_events_{today}.csv'

        # Criar response com Content-Type e Content-Disposition
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        # Escrever BOM UTF-8 para compatibilidade Excel
        response.write('\ufeff')

        # Criar writer CSV
        writer = csv.writer(response)

        # Escrever cabeçalhos (ordem definida na especificação)
        writer.writerow([
            'id',
            'municipio',
            'projeto',
            'tipo_evento',
            'inicio',
            'fim',
            'usuario',
            'coordenador',
            'fluxo',
            'gcal_status',
            'external_event_id',
            'gcal_last_sync_at',
            'gcal_last_error',
            'meet_link',
            'gcal_payload_hash',
            'updated_at'
        ])

        # Escrever linhas
        for s in qs.iterator():
            # Determinar fluxo (SUPER ou NAO_SUPER)
            fluxo = s.projeto.fluxo if s.projeto else ''

            writer.writerow([
                s.id,
                s.municipio.nome if s.municipio else '',
                s.projeto.nome if s.projeto else '',
                s.tipo_evento.nome if s.tipo_evento else '',
                s.inicio.isoformat() if s.inicio else '',
                s.fim.isoformat() if s.fim else '',
                s.usuario.username if s.usuario else '',
                s.coordenador.username if s.coordenador else '',
                fluxo,
                s.gcal_status,
                s.external_event_id or '',
                s.gcal_last_sync_at.isoformat() if s.gcal_last_sync_at else '',
                s.gcal_last_error or '',
                s.meet_link or '',
                s.gcal_payload_hash or '',
                s.updated_at.isoformat() if s.updated_at else ''
            ])

        return response

    def _export_json(self, qs: QuerySet[Solicitacao]) -> Response:
        """Exporta queryset como JSON com estrutura {count, results}"""
        # Serializar sem paginação (exporta tudo filtrado)
        serializer = SolicitacaoSerializer(qs, many=True)

        return Response({
            'count': len(serializer.data),
            'results': serializer.data
        })


# ================================================================
# Issue #98 - Event Detail with Timeline
# ================================================================

class EventDetailAPIView(APIView):
    """
    GET /api/gcal/dashboard/events/{id}/detail/

    Retorna detalhes completos de um evento GCal com timeline de AuditLog.

    Response 200:
    {
        "id": 123,
        "municipio_nome": "Fortaleza",
        "projeto_nome": "Gestão Escolar",
        "tipo_evento_nome": "Formação Online",
        "inicio": "2025-11-15T08:00:00-03:00",
        "fim": "2025-11-15T12:00:00-03:00",
        "usuario_username": "joao.silva",
        "coordenador_username": "maria.coord",
        "fluxo": "SUPER",
        "gcal_status": "PUBLISHED",
        "external_event_id": "asv2-123",
        "gcal_last_sync_at": "2025-11-12T10:30:00Z",
        "gcal_last_error": "",
        "meet_link": "https://meet.google.com/abc-defg-hij",
        "gcal_payload_hash": "a1b2c3...",
        "updated_at": "2025-11-12T10:30:00Z",
        "participations": [
            {
                "usuario": {"id": 10, "first_name": "João", "last_name": "Silva", "email": "joao@example.com"},
                "guest_email": null,
                "email": "joao@example.com",
                "role": "instrutor",
                "ch_horas": 4,
                "observacao": ""
            }
        ],
        "timeline": [
            {
                "id": 456,
                "action": "PUBLISH_GCAL",
                "usuario_nome": "Maria Coordenadora",
                "details": {"solicitacao_id": 123, "dry_run": false, "status": "success"},
                "created_at": "2025-11-12T10:30:00Z"
            },
            {
                "id": 455,
                "action": "PUBLISH_GCAL_REQUESTED",
                "usuario_nome": "Sistema",
                "details": {"solicitacao_id": 123},
                "created_at": "2025-11-12T10:29:00Z"
            }
        ]
    }

    Response 404:
    {"detail": "Solicitação não encontrada"}

    Response 403:
    {"detail": "Você não tem permissão para acessar este recurso"}

    Permissions: IsControleOrSuper
    """
    permission_classes = [IsAuthenticated, IsControleOrSuper]

    def get(self, request: Request, pk: int, *args: Any, **kwargs: Any) -> Response:
        # Importar serializer
        from .serializers import EventDetailSerializer

        # Buscar solicitação com select_related para otimizar queries
        try:
            solicitacao = Solicitacao.objects.select_related(
                'usuario', 'municipio', 'tipo_evento', 'projeto', 'coordenador'
            ).prefetch_related('participations__usuario').get(pk=pk)
        except Solicitacao.DoesNotExist:
            return Response(
                {'detail': 'Solicitação não encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Serializar
        serializer = EventDetailSerializer(solicitacao)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AlertsSummaryView(APIView):
    """
    GET /api/gcal/dashboard/alerts/summary/?start=&end=

    Retorna contagens de eventos por gcal_status para exibir badge/toast no frontend.

    Query params:
        - start (YYYY-MM-DD, opcional): Filtrar eventos >= start (00:00 local)
        - end (YYYY-MM-DD, opcional): Filtrar eventos <= end (23:59:59.999999 local)

    Response 200:
    {
        "errors": int,
        "pending": int,
        "published": int,
        "none": int,
        "window": {
            "start": "YYYY-MM-DD" | null,
            "end": "YYYY-MM-DD" | null
        }
    }

    Response 403:
    {"detail": "Você não tem permissão para acessar este recurso"}

    Permissions: IsControleOrSuper
    Timezone-aware: Usa helper _filter_events_queryset (clamp local→UTC)
    """
    permission_classes = [IsAuthenticated, IsControleOrSuper]

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        # Reutilizar helper TZ-aware
        qs = _filter_events_queryset(request, Solicitacao.objects.all())

        # Contar por gcal_status
        errors = qs.filter(gcal_status=Solicitacao.GCalStatus.ERROR).count()
        pending = qs.filter(gcal_status=Solicitacao.GCalStatus.PENDING).count()
        published = qs.filter(gcal_status=Solicitacao.GCalStatus.PUBLISHED).count()
        none = qs.filter(gcal_status=Solicitacao.GCalStatus.NONE).count()

        # Extrair janela de query params (retornar como strings ou null)
        start_param = request.query_params.get('start')
        end_param = request.query_params.get('end')

        return Response({
            'errors': errors,
            'pending': pending,
            'published': published,
            'none': none,
            'window': {
                'start': start_param if start_param else None,
                'end': end_param if end_param else None
            }
        }, status=status.HTTP_200_OK)


class SuccessRateView(APIView):
    """
    GET /api/gcal/dashboard/insights/success-rate/?start=&end=

    Retorna taxa de sucesso de publicação GCal (published / (published + error)).

    Query params:
        - start (YYYY-MM-DD, opcional): Filtrar eventos >= start
        - end (YYYY-MM-DD, opcional): Filtrar eventos <= end

    Response 200:
    {
        "published": int,
        "error": int,
        "pending": int,
        "none": int,
        "rate": float,  // 0.0 a 1.0 (round 4 casas)
        "window": { "start": "YYYY-MM-DD" | null, "end": "YYYY-MM-DD" | null }
    }

    Permissions: IsControleOrSuper
    """
    permission_classes = [IsAuthenticated, IsControleOrSuper]

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        # Reutilizar helper TZ-aware
        qs = _filter_events_queryset(request, Solicitacao.objects.all())

        # Contar por gcal_status
        published = qs.filter(gcal_status=Solicitacao.GCalStatus.PUBLISHED).count()
        error = qs.filter(gcal_status=Solicitacao.GCalStatus.ERROR).count()
        pending = qs.filter(gcal_status=Solicitacao.GCalStatus.PENDING).count()
        none = qs.filter(gcal_status=Solicitacao.GCalStatus.NONE).count()

        # Calcular rate (apenas published e error contam como "tentativas")
        denom = published + error
        rate = 0.0 if denom == 0 else round(published / denom, 4)

        # Extrair janela
        start_param = request.query_params.get('start')
        end_param = request.query_params.get('end')

        return Response({
            'published': published,
            'error': error,
            'pending': pending,
            'none': none,
            'rate': rate,
            'window': {
                'start': start_param if start_param else None,
                'end': end_param if end_param else None
            }
        }, status=status.HTTP_200_OK)


class TopInsightsView(APIView):
    """
    GET /api/gcal/dashboard/insights/top/?metric=municipios|projetos&start=&end=&limit=5

    Retorna top N municípios ou projetos por contagem de erros/eventos.

    Query params:
        - metric: "municipios" ou "projetos" (aceita aliases "municipio", "projeto")
        - start, end: janela de datas (opcional)
        - limit: número de resultados (default 5, min 1, max 20)

    Response 200:
    {
        "items": [
            {
                "name": "Fortaleza - CE",
                "count": 14,
                "published": 12,
                "error": 2,
                "rate": 0.8571
            },
            ...
        ],
        "window": { "start": "YYYY-MM-DD" | null, "end": "YYYY-MM-DD" | null },
        "metric": "municipios" | "projetos",
        "limit": 5
    }

    Response 400: metric inválido

    Permissions: IsControleOrSuper
    Ordenação: -error, -count
    """
    permission_classes = [IsAuthenticated, IsControleOrSuper]

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        # Validar metric
        metric_param = request.query_params.get('metric', '').lower()
        if metric_param in ('municipios', 'municipio'):
            group_field = 'municipio__nome'
            metric = 'municipios'
        elif metric_param in ('projetos', 'projeto'):
            group_field = 'projeto__nome'
            metric = 'projetos'
        else:
            return Response(
                {'detail': f'Parâmetro "metric" inválido: {metric_param}. Use "municipios" ou "projetos".'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validar limit
        try:
            limit = int(request.query_params.get('limit', 5))
            limit = max(1, min(20, limit))  # clamp entre 1 e 20
        except ValueError:
            limit = 5

        # Reutilizar helper TZ-aware
        qs = _filter_events_queryset(request, Solicitacao.objects.all())

        # Aggregations
        items_qs = qs.values(group_field).annotate(
            count=Count('id'),
            published=Count('id', filter=Q(gcal_status=Solicitacao.GCalStatus.PUBLISHED)),
            error=Count('id', filter=Q(gcal_status=Solicitacao.GCalStatus.ERROR))
        ).order_by('-error', '-count')[:limit]

        # Formatar items com rate
        items = []
        for item in items_qs:
            pub = item['published']
            err = item['error']
            denom = pub + err
            rate = 0.0 if denom == 0 else round(pub / denom, 4)

            items.append({
                'name': item[group_field] or '—',
                'count': item['count'],
                'published': pub,
                'error': err,
                'rate': rate
            })

        # Extrair janela
        start_param = request.query_params.get('start')
        end_param = request.query_params.get('end')

        return Response({
            'items': items,
            'window': {
                'start': start_param if start_param else None,
                'end': end_param if end_param else None
            },
            'metric': metric,
            'limit': limit
        }, status=status.HTTP_200_OK)
