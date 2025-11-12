"""
Solicitacao ViewSet (views ativas)
"""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false

from __future__ import annotations
from typing import Any
from django.db.models import QuerySet
from rest_framework.request import Request
from rest_framework.response import Response

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


def _get_client_ip(request: Request) -> Response:
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
    filterset_fields = []  # PR15: status handled manually in get_queryset with alias mapping
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
        # Actions approve, reject, preview_gcal, publish, resync_gcal, cancel_gcal têm permission_classes específicas
        # Não sobrescrever nesses casos
        if self.action in ["approve", "reject", "preview_gcal", "publish", "resync_gcal", "cancel_gcal"]:
            return super().get_permissions()
        if self.action == "create":
            return [IsCoordenadorOrDAT()]
        return [IsAuthenticated()]

    def get_queryset(self) -> QuerySet:
        # PR15: Filtro mine força filtro por usuário (mesmo para superusers)
        mine = self.request.query_params.get("mine")

        # Base queryset (permissões)
        if mine == "true":
            # Forçar filtro por usuário atual
            qs = (
                Solicitacao.objects.filter(usuario=self.request.user)
                .select_related("usuario", "municipio", "tipo_evento", "projeto")
                .prefetch_related("participations__usuario")
            )
        elif (
            self.request.user.is_superuser
            or self.request.user.groups.filter(name__in=["Superintendência", "Controle"]).exists()
        ):
            qs = Solicitacao.objects.select_related(
                "usuario", "municipio", "tipo_evento", "projeto"
            ).prefetch_related("participations__usuario")
        else:
            qs = (
                Solicitacao.objects.filter(usuario=self.request.user)
                .select_related("usuario", "municipio", "tipo_evento", "projeto")
                .prefetch_related("participations__usuario")
            )

        # PR15: Filtros adicionais via query params
        sector = self.request.query_params.get("sector")
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        q = self.request.query_params.get("q")
        flow = self.request.query_params.get("flow")  # PR15: SUPER ou NAO_SUPER
        status_filter = self.request.query_params.get("status")  # PR15: alias em inglês

        # PR15: Mapear status alias (inglês → português)
        STATUS_MAP = {
            "pending": "pendente",
            "approved": "aprovado",
            "rejected": "reprovado"
        }

        if status_filter:
            # Aceitar tanto alias em inglês quanto português
            mapped_status = STATUS_MAP.get(status_filter, status_filter)
            qs = qs.filter(status=mapped_status)

        # PR15: Filtro por fluxo do projeto
        if flow:
            qs = qs.filter(projeto__fluxo=flow)

        if sector:
            qs = qs.filter(projeto__nome__icontains=sector)

        if date_from:
            try:
                from datetime import date
                date_from_parsed = date.fromisoformat(date_from)
                qs = qs.filter(inicio__date__gte=date_from_parsed)
            except (ValueError, TypeError):
                pass  # Ignore invalid date format

        if date_to:
            try:
                from datetime import date
                date_to_parsed = date.fromisoformat(date_to)
                qs = qs.filter(inicio__date__lte=date_to_parsed)
            except (ValueError, TypeError):
                pass  # Ignore invalid date format

        if q:
            from django.db.models import Q
            qs = qs.filter(
                Q(municipio__nome__icontains=q)
                | Q(projeto__nome__icontains=q)
                | Q(tipo_evento__nome__icontains=q)
                | Q(observacoes__icontains=q)
                | Q(usuario__first_name__icontains=q)
                | Q(usuario__last_name__icontains=q)
                | Q(usuario__username__icontains=q)
            )

        return qs

    def perform_create(self, serializer):
        """
        Cria solicitação e define status baseado no fluxo do projeto:
        - SUPER: status='pendente' (requer aprovação manual)
        - NAO_SUPER: status='aprovado' (auto-aprovado)

        PR15: Suporta extra_participants para criar Participation automaticamente.
        """
        from .models import Participation

        # PR15: Salvar instance - o model.save() gerencia auto-aprovação baseado em projeto.fluxo
        instance = serializer.save(usuario=self.request.user)

        # PR15: Processar extra_participants
        extra_participants = self.request.data.get('extra_participants', {})
        if extra_participants:
            self._create_participants(instance, extra_participants)

    def _create_participants(self, solicitacao, extra):
        """
        PR15: Cria Participation entries baseado em extra_participants.

        IMPORTANTE: Mantemos o role original (FORMADOR, COORD_ACOMPANHA) mesmo para
        guest emails, pois build_attendees_for_solicitacao só considera esses roles
        ao montar a lista de participantes do Google Calendar.

        Formato esperado:
        {
            "coordenador_id": int,  # sempre o request.user, mas pode ser explícito
            "formador_ids": [int, ...],
            "formador_emails": [str, ...],
            "coord_acompanha_ids": [int, ...],
            "coord_acompanha_emails": [str, ...]
        }
        """
        from .models import Participation, Usuario

        # Sempre criar participação do coordenador (request.user)
        Participation.objects.get_or_create(
            solicitacao=solicitacao,
            usuario=self.request.user,
            defaults={'role': 'COORDENADOR'}
        )

        # Formadores por ID
        for formador_id in extra.get('formador_ids', []):
            if formador_id:
                try:
                    usuario = Usuario.objects.get(id=formador_id)
                    Participation.objects.get_or_create(
                        solicitacao=solicitacao,
                        usuario=usuario,
                        defaults={'role': 'FORMADOR'}
                    )
                except Usuario.DoesNotExist:
                    pass

        # Formadores por email (guest)
        for email in extra.get('formador_emails', []):
            if email and email.strip():
                # Tentar resolver email → Usuario
                try:
                    usuario = Usuario.objects.get(email__iexact=email.strip())
                    Participation.objects.get_or_create(
                        solicitacao=solicitacao,
                        usuario=usuario,
                        defaults={'role': 'FORMADOR'}
                    )
                except Usuario.DoesNotExist:
                    # Criar como guest_email mantendo role=FORMADOR para GCal
                    Participation.objects.get_or_create(
                        solicitacao=solicitacao,
                        guest_email=email.strip().lower(),
                        defaults={'role': 'FORMADOR'}
                    )

        # Coordenadores acompanhantes por ID
        for coord_id in extra.get('coord_acompanha_ids', []):
            if coord_id:
                try:
                    usuario = Usuario.objects.get(id=coord_id)
                    Participation.objects.get_or_create(
                        solicitacao=solicitacao,
                        usuario=usuario,
                        defaults={'role': 'COORD_ACOMPANHA'}
                    )
                except Usuario.DoesNotExist:
                    pass

        # Coordenadores acompanhantes por email (guest)
        for email in extra.get('coord_acompanha_emails', []):
            if email and email.strip():
                try:
                    usuario = Usuario.objects.get(email__iexact=email.strip())
                    Participation.objects.get_or_create(
                        solicitacao=solicitacao,
                        usuario=usuario,
                        defaults={'role': 'COORD_ACOMPANHA'}
                    )
                except Usuario.DoesNotExist:
                    # Criar como guest_email mantendo role=COORD_ACOMPANHA para GCal
                    Participation.objects.get_or_create(
                        solicitacao=solicitacao,
                        guest_email=email.strip().lower(),
                        defaults={'role': 'COORD_ACOMPANHA'}
                    )

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

        # PR15: Accept 'reason' as alias for 'justificativa'
        justificativa = request.data.get("reason") or request.data.get("justificativa", "")

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
                "justificativa": justificativa,
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

        # PR15: Accept 'reason' as alias for 'justificativa'
        justificativa = request.data.get("reason") or request.data.get("justificativa", "")

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

        # AuditLog (PR14: incluir payload_hash)
        client_ip = _get_client_ip(request)
        AuditLog.objects.create(
            usuario=request.user,
            action="PREVIEW_GCAL",
            model_name="Solicitacao",
            details={
                "solicitacao_id": solicitacao.id,
                "event_id": preview["event_id"],
                "summary": preview["payload"].get("summary", ""),
                "payload_hash": preview.get("payload_hash", ""),
                "ip_address": client_ip,
            },
        )

        logger.info(
            "preview_gcal",
            extra={
                "event": "preview_gcal",
                "user_id": request.user.id,
                "username": request.user.username,
                "solicitacao_id": solicitacao.id,
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
        from apps.core.models import AuditLog, GoogleOAuthCredential

        # OAuth Phase 4: Verificar credencial Google em modo OAuth
        auth_mode = getattr(settings, "GCAL_AUTH_MODE", "service_account")
        operator_user_id = None

        if auth_mode == "oauth":
            try:
                GoogleOAuthCredential.objects.get(user=request.user)
                operator_user_id = request.user.id
            except GoogleOAuthCredential.DoesNotExist:
                return Response(
                    {
                        "detail": "Conecte sua conta Google",
                        "code": "google_not_connected"
                    },
                    status=status.HTTP_403_FORBIDDEN
                )

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

        # RF05/PA-03: Bloquear apenas chamadas reais (dry_run=False) quando apply_blocked
        # dry_run deve sempre funcionar, independente de GCAL_CLIENT
        if features_apply_blocked and not apply_blocked and not dry_run:
            return Response(
                {
                    "detail": "Publicação bloqueada: GCAL_CLIENT não está configurado como 'google'.",
                    "hint": "Para forçar publicação em modo de teste, envie apply_blocked=true no corpo da requisição.",
                    "features_apply_blocked": True,
                    "dry_run_allowed": True,
                },
                status=status.HTTP_409_CONFLICT,
            )

        # PR14: Marcar como PENDING antes de enfileirar (se não for dry-run)
        if not dry_run:
            solicitacao.mark_gcal(
                status=Solicitacao.GCalStatus.PENDING,
                payload_hash=None,
                error=""
            )

        # Disparar task Celery (assíncrona)
        # OAuth Phase 3: Passar operator_user_id APENAS em modo OAuth
        if auth_mode == "oauth":
            task = task_publish_solicitacao_to_gcal.delay(
                solicitacao.id,
                dry_run=dry_run,
                apply_blocked=apply_blocked,
                operator_user_id=operator_user_id
            )
        else:
            # Service account mode: não passar operator_user_id (mantém assinatura antiga)
            task = task_publish_solicitacao_to_gcal.delay(
                solicitacao.id,
                dry_run=dry_run,
                apply_blocked=apply_blocked
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
                "solicitacao_id": solicitacao.id,
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

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsControleOrSuper],
        url_path="resync-gcal",
    )
    def resync_gcal(self, request, pk=None):
        """
        Republicar solicitação no Google Calendar (força UPDATE) - Fase 4.

        Reseta gcal_payload_hash para forçar UPDATE mesmo se já publicado.
        Enfileira task_publish_solicitacao_to_gcal para republicação.

        Permissão: Controle ou Superintendência
        Returns: 202 Accepted (processamento assíncrono)
        """
        from django.conf import settings
        from apps.core.tasks import task_publish_solicitacao_to_gcal
        from apps.core.models import AuditLog, GoogleOAuthCredential

        # OAuth Phase 4: Verificar credencial Google em modo OAuth
        auth_mode = getattr(settings, "GCAL_AUTH_MODE", "service_account")
        operator_user_id = None

        if auth_mode == "oauth":
            try:
                GoogleOAuthCredential.objects.get(user=request.user)
                operator_user_id = request.user.id
            except GoogleOAuthCredential.DoesNotExist:
                return Response(
                    {
                        "detail": "Conecte sua conta Google",
                        "code": "google_not_connected"
                    },
                    status=status.HTTP_403_FORBIDDEN
                )

        solicitacao = self.get_object()

        # Validar status aprovado
        if solicitacao.status != "aprovado":
            return Response(
                {"detail": "Apenas solicitações aprovadas podem ser resincronizadas."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Marcar como PENDING (será republicado)
        solicitacao.mark_gcal(
            status=Solicitacao.GCalStatus.PENDING,
            payload_hash=None,  # Resetar hash para forçar UPDATE
            error=""
        )

        # Enfileirar task de publicação (reutiliza lógica existente)
        # OAuth Phase 3: Passar operator_user_id APENAS em modo OAuth
        if auth_mode == "oauth":
            task = task_publish_solicitacao_to_gcal.delay(
                solicitacao.id,
                dry_run=False,
                apply_blocked=False,
                operator_user_id=operator_user_id
            )
        else:
            # Service account mode: não passar operator_user_id (mantém assinatura antiga)
            task = task_publish_solicitacao_to_gcal.delay(
                solicitacao.id,
                dry_run=False,
                apply_blocked=False
            )

        # AuditLog
        client_ip = _get_client_ip(request)
        AuditLog.objects.create(
            usuario=request.user,
            action="RESYNC_GCAL_REQUESTED",
            model_name="Solicitacao",
            details={
                "solicitacao_id": solicitacao.id,
                "task_id": task.id,
                "ip_address": client_ip,
            },
        )

        logger.info(
            "resync_gcal_requested",
            extra={
                "event": "resync_gcal_requested",
                "user_id": request.user.id,
                "username": request.user.username,
                "solicitacao_id": solicitacao.id,
                "task_id": task.id,
                "ip_address": client_ip,
                "timestamp": timezone.now().isoformat(),
            },
        )

        return Response(
            {
                "detail": "Resincronização solicitada com sucesso (processando em background).",
                "task_id": task.id,
                "solicitacao_id": solicitacao.id,
            },
            status=status.HTTP_202_ACCEPTED,
        )

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsControleOrSuper],
        url_path="cancel-gcal",
    )
    def cancel_gcal(self, request, pk=None):
        """
        Cancelar evento no Google Calendar e limpar campos - Fase 4.

        Deleta evento do Calendar (trata 404 como sucesso - idempotência) e limpa
        todos os campos relacionados: external_event_id, meet_link, gcal_payload_hash.

        Permissão: Controle ou Superintendência
        Returns: 202 Accepted (processamento assíncrono) ou 409 Conflict
        """
        from apps.core.tasks import task_cancel_solicitacao_from_gcal
        from apps.core.models import AuditLog

        solicitacao = self.get_object()

        # Validar que evento foi publicado
        if not solicitacao.external_event_id and solicitacao.gcal_status != Solicitacao.GCalStatus.PUBLISHED:
            return Response(
                {
                    "detail": "Solicitação não possui evento publicado no Google Calendar.",
                    "hint": "Apenas eventos publicados podem ser cancelados.",
                },
                status=status.HTTP_409_CONFLICT,
            )

        # Marcar como PENDING temporariamente (task mudará para NONE após deletar)
        solicitacao.mark_gcal(
            status=Solicitacao.GCalStatus.PENDING,
            payload_hash=solicitacao.gcal_payload_hash,  # Manter hash durante cancelamento
            error=""
        )

        # Enfileirar task de cancelamento
        task = task_cancel_solicitacao_from_gcal.delay(solicitacao.id)

        # AuditLog
        client_ip = _get_client_ip(request)
        AuditLog.objects.create(
            usuario=request.user,
            action="CANCEL_GCAL_REQUESTED",
            model_name="Solicitacao",
            details={
                "solicitacao_id": solicitacao.id,
                "task_id": task.id,
                "external_event_id": solicitacao.external_event_id,
                "ip_address": client_ip,
            },
        )

        logger.info(
            "cancel_gcal_requested",
            extra={
                "event": "cancel_gcal_requested",
                "user_id": request.user.id,
                "username": request.user.username,
                "solicitacao_id": solicitacao.id,
                "task_id": task.id,
                "external_event_id": solicitacao.external_event_id,
                "ip_address": client_ip,
                "timestamp": timezone.now().isoformat(),
            },
        )

        return Response(
            {
                "detail": "Cancelamento solicitado com sucesso (processando em background).",
                "task_id": task.id,
                "solicitacao_id": solicitacao.id,
            },
            status=status.HTTP_202_ACCEPTED,
        )
