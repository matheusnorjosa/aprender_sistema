"""
Solicitacao ViewSet (views ativas)
"""

import logging

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter

from .models import Solicitacao
from .permissions import IsCoordenadorOrDAT, IsSuperintendencia
from .serializers import SolicitacaoSerializer

logger = logging.getLogger(__name__)


def _get_client_ip(request):
    """
    Extrai o IP real do cliente, considerando proxies reversos.
    """
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    x_real_ip = request.META.get("HTTP_X_REAL_IP")
    if x_real_ip:
        return x_real_ip.strip()
    return request.META.get("REMOTE_ADDR", "unknown")


class SolicitacaoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para Solicitações de Evento.

    PA-01: Status sempre começa pendente.
    PA-02: Apenas Superintendência pode aprovar/reprovar.
    PR 8/N: Apenas Coordenador ou DAT podem criar solicitações.
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
    ordering = ["-inicio"]

    def get_permissions(self):
        if self.action == "create":
            return [IsCoordenadorOrDAT()]
        return [IsAuthenticated()]

    def get_queryset(self):
        if (
            self.request.user.is_superuser
            or self.request.user.groups.filter(name="Superintendência").exists()
        ):
            return Solicitacao.objects.select_related(
                "usuario", "municipio", "tipo_evento", "projeto"
            ).prefetch_related("formadores")
        return (
            Solicitacao.objects.filter(usuario=self.request.user)
            .select_related("usuario", "municipio", "tipo_evento", "projeto")
            .prefetch_related("formadores")
        )

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)

    @action(
        detail=True,
        methods=["patch"],
        permission_classes=[IsSuperintendencia],
        url_path="approve",
    )
    def approve(self, request, pk=None):
        """Aprovar solicitação (PA-02: apenas Superintendência)."""
        solicitacao = self.get_object()

        if solicitacao.status == "aprovado":
            return Response(
                {"detail": "Solicitação já está aprovada."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        solicitacao.status = "aprovado"
        solicitacao.save()

        client_ip = _get_client_ip(request)
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
                "justificativa": request.data.get("justificativa", ""),
                "timestamp": timezone.now().isoformat(),
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
    def reject(self, request, pk=None):
        """Reprovar solicitação (PA-02: apenas Superintendência)."""
        solicitacao = self.get_object()
        justificativa = request.data.get("justificativa", "")

        if solicitacao.status == "reprovado":
            return Response(
                {"detail": "Solicitação já está reprovada."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        solicitacao.status = "reprovado"
        solicitacao.save()

        client_ip = _get_client_ip(request)
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

        return Response(
            {
                "detail": "Solicitação reprovada.",
                "solicitacao": SolicitacaoSerializer(solicitacao).data,
            },
            status=status.HTTP_200_OK,
        )
