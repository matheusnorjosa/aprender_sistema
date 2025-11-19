"""
Deslocamento CRUD API — Issue #188

Endpoints:
- GET /api/deslocamentos/ - List with filters
- GET /api/deslocamentos/{id}/ - Retrieve
- POST /api/deslocamentos/ - Create (AuditLog)
- PUT /api/deslocamentos/{id}/ - Update (AuditLog)
- DELETE /api/deslocamentos/{id}/ - Delete (AuditLog)

Permissions:
- IsControleOrDAT (Controle, DAT, Superintendência)

Filters:
- usuario_id: Filter by usuario ID
- data_inicio: Filter by start_date >= value (YYYY-MM-DD)
- data_fim: Filter by end_date <= value (YYYY-MM-DD)
- origem: Case-insensitive partial match
- destino: Case-insensitive partial match

Ordering:
- Default: -start_date (most recent first)
- Available: start_date, end_date, origem, destino

Pagination:
- 50 per page
"""
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false

from __future__ import annotations

from typing import Any

from django.db.models import Q, QuerySet
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request

from .models import AuditLog, Deslocamento
from .permissions import IsControleOrDAT
from .serializers import DeslocamentoSerializer


def _get_client_ip(request: Request) -> str:
    """
    Extrai o IP real do cliente, considerando proxies reversos.

    Prioridade:
    1. HTTP_X_FORWARDED_FOR (primeiro IP da lista)
    2. HTTP_X_REAL_IP
    3. REMOTE_ADDR

    Returns:
        str: IP do cliente
    """
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()

    x_real_ip = request.META.get("HTTP_X_REAL_IP")
    if x_real_ip:
        return x_real_ip.strip()

    return request.META.get("REMOTE_ADDR", "unknown")


class DeslocamentoPagination(PageNumberPagination):
    """Pagination for Deslocamento list (50 per page)."""
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 100


class DeslocamentoViewSet(viewsets.ModelViewSet):
    """
    CRUD ViewSet for Deslocamento model (Issue #188).

    Provides full CRUD operations for travel records between municipalities.

    Permissions:
        - IsControleOrDAT (Controle, DAT, Superintendência)

    Filters:
        - usuario_id: Filter by usuario ID
        - data_inicio: Filter by start_date >= value (YYYY-MM-DD)
        - data_fim: Filter by end_date <= value (YYYY-MM-DD)
        - origem: Case-insensitive partial match
        - destino: Case-insensitive partial match

    Ordering:
        - Default: -start_date (most recent first)
        - Available: start_date, end_date, origem, destino

    Pagination:
        - 50 per page

    AuditLog:
        - CREATE: Records creation with usuario, IP, and details
        - UPDATE: Records update with changed fields
        - DELETE: Records deletion with original data
    """

    queryset = Deslocamento.objects.select_related("usuario").all()
    serializer_class = DeslocamentoSerializer
    permission_classes = [IsAuthenticated, IsControleOrDAT]
    pagination_class = DeslocamentoPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["start_date", "end_date", "origem", "destino"]
    ordering = ["-start_date"]  # Default: most recent first

    def get_queryset(self) -> QuerySet:
        """
        Apply custom filters via query params:
        - usuario_id: Filter by usuario ID
        - data_inicio: Filter by start_date >= value (YYYY-MM-DD)
        - data_fim: Filter by end_date <= value (YYYY-MM-DD)
        - origem: Case-insensitive partial match
        - destino: Case-insensitive partial match
        """
        queryset = super().get_queryset()

        # Filter by usuario_id
        usuario_id = self.request.query_params.get("usuario_id")
        if usuario_id:
            queryset = queryset.filter(usuario_id=usuario_id)

        # Filter by data_inicio (start_date >= value)
        data_inicio = self.request.query_params.get("data_inicio")
        if data_inicio:
            queryset = queryset.filter(start_date__gte=data_inicio)

        # Filter by data_fim (end_date <= value)
        data_fim = self.request.query_params.get("data_fim")
        if data_fim:
            queryset = queryset.filter(end_date__lte=data_fim)

        # Filter by origem (case-insensitive partial match)
        origem = self.request.query_params.get("origem")
        if origem:
            queryset = queryset.filter(origem__icontains=origem)

        # Filter by destino (case-insensitive partial match)
        destino = self.request.query_params.get("destino")
        if destino:
            queryset = queryset.filter(destino__icontains=destino)

        return queryset

    def perform_create(self, serializer: DeslocamentoSerializer) -> None:
        """
        Create Deslocamento and log to AuditLog.

        AuditLog records:
        - action: CREATE_DESLOCAMENTO
        - details: usuario_id, origem, destino, start_date, end_date, ip_address, user_agent
        """
        deslocamento = serializer.save()

        # Create AuditLog
        AuditLog.objects.create(
            usuario=self.request.user,
            action="CREATE_DESLOCAMENTO",
            model_name="Deslocamento",
            details={
                "deslocamento_id": deslocamento.id,
                "usuario_id": deslocamento.usuario_id,
                "origem": deslocamento.origem,
                "destino": deslocamento.destino,
                "start_date": deslocamento.start_date.isoformat(),
                "end_date": deslocamento.end_date.isoformat(),
                "observacao": deslocamento.observacao or "",
                "ip_address": _get_client_ip(self.request),
                "user_agent": self.request.META.get("HTTP_USER_AGENT", "")[:200],
            }
        )

    def perform_update(self, serializer: DeslocamentoSerializer) -> None:
        """
        Update Deslocamento and log to AuditLog.

        AuditLog records:
        - action: UPDATE_DESLOCAMENTO
        - details: deslocamento_id, changed_fields, prev_values, new_values, ip_address, user_agent
        """
        instance = self.get_object()

        # Track changed fields
        changed_fields = {}
        prev_values = {}
        new_values = {}

        for field in ["origem", "destino", "start_date", "end_date", "observacao"]:
            old_value = getattr(instance, field, None)
            new_value = serializer.validated_data.get(field, old_value)

            # Convert dates to ISO format for comparison
            if field in ["start_date", "end_date"]:
                old_value_str = old_value.isoformat() if old_value else None
                new_value_str = new_value.isoformat() if new_value else None
            else:
                old_value_str = str(old_value) if old_value else ""
                new_value_str = str(new_value) if new_value else ""

            if old_value_str != new_value_str:
                changed_fields[field] = True
                prev_values[field] = old_value_str
                new_values[field] = new_value_str

        deslocamento = serializer.save()

        # Create AuditLog if there are changes
        if changed_fields:
            AuditLog.objects.create(
                usuario=self.request.user,
                action="UPDATE_DESLOCAMENTO",
                model_name="Deslocamento",
                details={
                    "deslocamento_id": deslocamento.id,
                    "usuario_id": deslocamento.usuario_id,
                    "changed_fields": list(changed_fields.keys()),
                    "prev_values": prev_values,
                    "new_values": new_values,
                    "ip_address": _get_client_ip(self.request),
                    "user_agent": self.request.META.get("HTTP_USER_AGENT", "")[:200],
                }
            )

    def perform_destroy(self, instance: Deslocamento) -> None:
        """
        Delete Deslocamento and log to AuditLog.

        AuditLog records:
        - action: DELETE_DESLOCAMENTO
        - details: deslocamento_id, usuario_id, origem, destino, start_date, end_date, ip_address, user_agent
        """
        # Create AuditLog before deletion
        AuditLog.objects.create(
            usuario=self.request.user,
            action="DELETE_DESLOCAMENTO",
            model_name="Deslocamento",
            details={
                "deslocamento_id": instance.id,
                "usuario_id": instance.usuario_id,
                "origem": instance.origem,
                "destino": instance.destino,
                "start_date": instance.start_date.isoformat(),
                "end_date": instance.end_date.isoformat(),
                "observacao": instance.observacao or "",
                "ip_address": _get_client_ip(self.request),
                "user_agent": self.request.META.get("HTTP_USER_AGENT", "")[:200],
            }
        )

        # Delete instance
        instance.delete()
