"""
AS v2 — Solicitacao ViewSet

PA-01: Nenhuma solicitação é auto-aprovada.
PA-02: Apenas Superintendência pode aprovar/reprovar.
PA-05: Registrar usuário, data/hora e justificativa em AuditLog.
"""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false

from __future__ import annotations

import logging

from django.db.models import QuerySet
from django.utils import timezone

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.core.models import AuditLog, Solicitacao
from apps.core.permissions import IsCoordenadorOrDAT, IsSuperintendencia
from apps.core.serializers import SolicitacaoSerializer
from apps.core.views.utils import _get_client_ip

logger = logging.getLogger(__name__)


class SolicitacaoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para Solicitações de Evento.

    PA-01: Status sempre começa pendente.
    PA-02: Apenas Superintendência pode aprovar/reprovar.
    PR 8/N: Apenas Coordenador ou DAT podem criar solicitações.

    Filtros disponíveis:
    - status: exato (pendente/aprovado/reprovado)
    - search: busca textual em usuario, municipio, motivo, observacoes
    - ordering: inicio, fim, id
    """

    queryset = Solicitacao.objects.select_related(
        "usuario", "municipio", "tipo_evento", "projeto"
    )
    serializer_class = SolicitacaoSerializer
    permission_classes = [IsAuthenticated]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status"]
    search_fields = [
        "usuario__username",
        "usuario__first_name",
        "usuario__last_name",
        "municipio__nome",
        "observacoes",
    ]
    ordering_fields = ["inicio", "fim", "id"]
    ordering = ["-inicio"]  # default ordering

    def get_permissions(self):
        """
        PR 8/N: Apenas Coordenador ou DAT podem criar solicitações.
        Outras ações: IsAuthenticated.
        """
        if self.action == "create":
            return [IsCoordenadorOrDAT()]
        return [IsAuthenticated()]

    def get_queryset(self) -> QuerySet:
        """
        Filtrar solicitações por usuário (exceto Superintendência/superuser que vê todas).
        """
        if (
            self.request.user.is_superuser
            or self.request.user.groups.filter(name="Superintendência").exists()
        ):
            return Solicitacao.objects.select_related(
                "usuario", "municipio", "tipo_evento", "projeto"
            ).prefetch_related("participations__usuario")
        return (
            Solicitacao.objects.filter(usuario=self.request.user)
            .select_related("usuario", "municipio", "tipo_evento", "projeto")
            .prefetch_related("participations__usuario")
        )

    def perform_create(self, serializer):
        """
        PR 8/N: Preenche usuario automaticamente com request.user ao criar solicitação.
        PA-01: Status sempre começa pendente (garantido pelo modelo).
        """
        serializer.save(usuario=self.request.user)

    @action(
        detail=True,
        methods=["patch"],
        permission_classes=[IsSuperintendencia],
        url_path="approve",
    )
    def approve(self, request: Request, pk=None) -> Response:
        """
        Aprovar solicitação (PA-02: apenas Superintendência).

        POST /api/solicitacoes/<id>/approve/
        Body: {"justificativa": "..."}  # opcional
        """
        solicitacao = self.get_object()

        if solicitacao.status == "aprovado":
            return Response(
                {"detail": "Solicitação já está aprovada."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        prev_status = solicitacao.status
        solicitacao.status = "aprovado"
        solicitacao.save()

        # ================================================================
        # PA-05: Log estruturado de auditoria + AuditLog persistente
        # ================================================================
        client_ip = _get_client_ip(request)
        justificativa = request.data.get("justificativa", "")

        # Logger estruturado (para monitoramento em tempo real)
        logger.info(
            "solicitacao_approved",
            extra={
                "event": "solicitacao_approved",
                "user_id": request.user.id,
                "username": request.user.username,
                "solicitation_id": solicitacao.id,
                "action": "approve",
                "ip_address": client_ip,
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:200],
                "justificativa": justificativa,
                "timestamp": timezone.now().isoformat(),
            },
        )

        # AuditLog persistente (para rastreabilidade e compliance)
        AuditLog.objects.create(
            usuario=request.user,
            action="APPROVE",
            model_name="Solicitacao",
            details={
                "solicitacao_id": solicitacao.id,
                "prev_status": prev_status,
                "new_status": "aprovado",
                "justificativa": justificativa,
                "ip_address": client_ip,
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:200],
            },
        )

        return Response(
            {
                "detail": "Solicitação aprovada com sucesso.",
                "solicitacao": SolicitacaoSerializer(solicitacao).data,
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["patch"],
        permission_classes=[IsSuperintendencia],
        url_path="reject",
    )
    def reject(self, request: Request, pk=None) -> Response:
        """
        Reprovar solicitação (PA-02: apenas Superintendência).

        POST /api/solicitacoes/<id>/reject/
        Body: {"justificativa": "..."} # opcional
        """
        solicitacao = self.get_object()
        justificativa = request.data.get("justificativa", "")

        if solicitacao.status == "reprovado":
            return Response(
                {"detail": "Solicitação já está reprovada."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        prev_status = solicitacao.status
        solicitacao.status = "reprovado"
        solicitacao.save()

        # ================================================================
        # PA-05: Log estruturado de auditoria + AuditLog persistente
        # ================================================================
        client_ip = _get_client_ip(request)

        # Logger estruturado (para monitoramento em tempo real)
        logger.info(
            "solicitacao_rejected",
            extra={
                "event": "solicitacao_rejected",
                "user_id": request.user.id,
                "username": request.user.username,
                "solicitation_id": solicitacao.id,
                "action": "reject",
                "ip_address": client_ip,
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:200],
                "justificativa": justificativa,
                "timestamp": timezone.now().isoformat(),
            },
        )

        # AuditLog persistente (para rastreabilidade e compliance)
        AuditLog.objects.create(
            usuario=request.user,
            action="REJECT",
            model_name="Solicitacao",
            details={
                "solicitacao_id": solicitacao.id,
                "prev_status": prev_status,
                "new_status": "reprovado",
                "justificativa": justificativa,
                "ip_address": client_ip,
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:200],
            },
        )

        return Response(
            {
                "detail": "Solicitação reprovada.",
                "solicitacao": SolicitacaoSerializer(solicitacao).data,
            },
            status=status.HTTP_200_OK,
        )
