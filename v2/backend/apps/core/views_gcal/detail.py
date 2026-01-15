"""
AS v2 — GCal Dashboard Detail Views

Views for event details, listing, export, and drift detection.
Type-checked with Pyright (strict mode).
"""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false, reportFunctionMemberAccess=false

from __future__ import annotations

import csv
from datetime import date
from typing import Any

from django.db.models import Q, QuerySet
from django.http import HttpResponse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import Solicitacao
from apps.core.permissions import IsControleOrSuper
from apps.core.serializers import EventDetailSerializer, SolicitacaoSerializer
from apps.core.services.gcal import compute_payload_hash
from apps.core.views_gcal.helpers import (
    DashboardEventsPagination,
    _filter_events_queryset,
)


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


class DashboardEventsExportView(APIView):
    """
    GET /api/gcal/dashboard/events/export/

    Exporta eventos do Dashboard GCal em CSV ou JSON.

    Query params:
    - status: Filtro por gcal_status (NONE/PENDING/PUBLISHED/ERROR)
    - start (ISO date): Filtro início >= start (formato: YYYY-MM-DD)
    - end (ISO date): Filtro início <= end (formato: YYYY-MM-DD)
    - format: csv|json (default: csv)

    Permissions: IsControleOrSuper
    """
    permission_classes = [IsAuthenticated, IsControleOrSuper]

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response | HttpResponse:
        # Usar helper unificado timezone-aware (Issue #96 follow-up #124)
        # MP4: select_related para evitar N+1 em CSV export (.iterator() bypassa cache)
        # Fix N+1: added projeto__gerencia and prefetch participations
        qs = _filter_events_queryset(
            request,
            Solicitacao.objects.select_related(
                'municipio', 'projeto', 'tipo_evento', 'usuario', 'coordenador',
                'projeto__gerencia'
            ).prefetch_related('participations__usuario')
        )

        # Determinar formato (default: csv)
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

        # Escrever cabeçalhos
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

        # Escrever linhas (chunk_size required when using iterator() with prefetch_related)
        for s in qs.iterator(chunk_size=2000):
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
        serializer = SolicitacaoSerializer(qs, many=True)

        return Response({
            'count': len(serializer.data),
            'results': serializer.data
        })


class EventDetailAPIView(APIView):
    """
    GET /api/gcal/dashboard/events/{id}/detail/

    Retorna detalhes completos de um evento GCal com timeline de AuditLog.

    Permissions: IsControleOrSuper
    """
    permission_classes = [IsAuthenticated, IsControleOrSuper]

    def get(self, request: Request, pk: int, *args: Any, **kwargs: Any) -> Response:
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

        # Aplicar filtros
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
