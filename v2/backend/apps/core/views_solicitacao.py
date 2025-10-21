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

from .models import Solicitacao, AuditLog
from .permissions import IsCoordenadorOrDAT, IsSuperintendencia, IsControleOrSuper
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
        # Actions approve, reject, preview_gcal, publish têm permission_classes específicas
        # Não sobrescrever nesses casos
        if self.action in ["approve", "reject", "preview_gcal", "publish"]:
            return super().get_permissions()
        if self.action == "create":
            return [IsCoordenadorOrDAT()]
        return [IsAuthenticated()]

    def get_queryset(self):
        if (
            self.request.user.is_superuser
            or self.request.user.groups.filter(name__in=["Superintendência", "Controle"]).exists()
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

        # Capturar status anterior
        prev_status = solicitacao.status

        solicitacao.status = "aprovado"
        solicitacao.save()

        client_ip = _get_client_ip(request)

        # Persistir AuditLog
        AuditLog.objects.create(
            usuario=request.user,
            action="APPROVE",
            model_name="Solicitacao",
            details={
                "solicitacao_id": solicitacao.id,
                "prev_status": prev_status,
                "new_status": solicitacao.status,
                "ip_address": client_ip,
            },
        )

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

        # Capturar status anterior
        prev_status = solicitacao.status

        solicitacao.status = "reprovado"
        solicitacao.save()

        client_ip = _get_client_ip(request)

        # Persistir AuditLog
        AuditLog.objects.create(
            usuario=request.user,
            action="REJECT",
            model_name="Solicitacao",
            details={
                "solicitacao_id": solicitacao.id,
                "prev_status": prev_status,
                "new_status": solicitacao.status,
                "justificativa": justificativa,
                "ip_address": client_ip,
            },
        )

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

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsControleOrSuper],
        url_path="preview-gcal",
    )
    def preview_gcal(self, request, pk=None):
        """Preview do payload GCal sem publicar (Controle ou Superintendência)."""
        from apps.core.services.gcal_sync_service import build_preview_for_solicitacao
        from apps.core.models import AuditLog

        solicitacao = self.get_object()

        # Gerar preview
        preview = build_preview_for_solicitacao(solicitacao)

        # AuditLog
        client_ip = _get_client_ip(request)
        AuditLog.objects.create(
            usuario=request.user,
            action="PREVIEW_GCAL",
            model_name="Solicitacao",
            details={
                "solicitacao_id": solicitacao.id,
                "event_id": preview["event_id"],
                "summary": preview["payload"].get("summary", ""),
                "ip_address": client_ip,
            },
        )

        logger.info(
            "preview_gcal",
            extra={
                "event": "preview_gcal",
                "user_id": request.user.id,
                "username": request.user.username,
                "solicitation_id": solicitacao.id,
                "event_id": preview["event_id"],
                "ip_address": client_ip,
                "timestamp": timezone.now().isoformat(),
            },
        )

        return Response(
            {
                "detail": "Preview gerado com sucesso.",
                "preview": preview,
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsControleOrSuper],
        url_path="publish",
    )
    def publish(self, request, pk=None):
        """Publica solicitação no Google Calendar via Celery (Controle ou Superintendência)."""
        from django.conf import settings
        from apps.core.tasks import task_publish_solicitacao_to_gcal
        from apps.core.models import AuditLog

        solicitacao = self.get_object()

        # Verificar se já está aprovada
        if solicitacao.status != "aprovado":
            return Response(
                {"detail": "Apenas solicitações aprovadas podem ser publicadas no Google Calendar."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Parâmetros opcionais
        dry_run = request.data.get("dry_run", False)
        apply_blocked = request.data.get("apply_blocked", False)

        # Verificar se apply está bloqueado (GCAL_CLIENT != "google")
        gcal_client = getattr(settings, "GCAL_CLIENT", None)
        features_apply_blocked = gcal_client != "google"

        if features_apply_blocked and not apply_blocked:
            return Response(
                {
                    "detail": "Publicação bloqueada: GCAL_CLIENT não está configurado como 'google'.",
                    "hint": "Para forçar publicação em modo de teste, envie apply_blocked=true no corpo da requisição.",
                    "features_apply_blocked": True,
                },
                status=status.HTTP_409_CONFLICT,
            )

        # Disparar task Celery (assíncrona)
        task = task_publish_solicitacao_to_gcal.delay(
            solicitacao.id, dry_run=dry_run, apply_blocked=apply_blocked
        )

        # AuditLog
        client_ip = _get_client_ip(request)
        AuditLog.objects.create(
            usuario=request.user,
            action="PUBLISH_GCAL_REQUESTED",
            model_name="Solicitacao",
            details={
                "solicitacao_id": solicitacao.id,
                "task_id": task.id,
                "dry_run": dry_run,
                "apply_blocked": apply_blocked,
                "ip_address": client_ip,
            },
        )

        logger.info(
            "publish_gcal_requested",
            extra={
                "event": "publish_gcal_requested",
                "user_id": request.user.id,
                "username": request.user.username,
                "solicitation_id": solicitacao.id,
                "task_id": task.id,
                "dry_run": dry_run,
                "apply_blocked": apply_blocked,
                "ip_address": client_ip,
                "timestamp": timezone.now().isoformat(),
            },
        )

        return Response(
            {
                "detail": "Publicação solicitada com sucesso (processando em background).",
                "task_id": task.id,
                "solicitacao_id": solicitacao.id,
            },
            status=status.HTTP_202_ACCEPTED,
        )
