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

from apps.core.models import AuditLog, Participation, Solicitacao, Usuario
from apps.core.permissions import IsCoordenadorOrDAT, IsOwnerOrPrivileged, IsSuperintendencia
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
        "usuario", "municipio", "tipo_evento", "projeto", "projeto__gerencia"
    ).prefetch_related(
        "participations__usuario"  # Fix N+1: prefetch participations and their users
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
        Permissões por ação:
        - create: Coordenador ou DAT (PR 8/N)
        - update/partial_update: Owner ou privilegiado (Superintendência/DAT)
        - approve/reject: Superintendência (PA-02)
        - outras: IsAuthenticated
        """
        if self.action == "create":
            return [IsCoordenadorOrDAT()]
        if self.action in ["update", "partial_update"]:
            return [IsOwnerOrPrivileged()]
        return [IsAuthenticated()]

    def get_queryset(self) -> QuerySet:
        """
        Filtrar solicitações por usuário.

        PA-02 (Adaptada): Superintendência, DAT e superusers veem todas as solicitações.
        Outros usuários veem apenas suas próprias solicitações.
        """
        if (
            self.request.user.is_superuser
            or self.request.user.groups.filter(name__in=["Superintendência", "DAT"]).exists()
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

    def perform_update(self, serializer):
        """
        Registra edição de solicitação no AuditLog.

        Rastreia:
        - Campos alterados (antes/depois)
        - Formadores alterados (adicionados/removidos)
        - Usuário que editou
        - IP e User-Agent
        """
        instance = serializer.instance

        # Captura formadores atuais antes do update
        old_formador_ids = set(
            Participation.objects.filter(
                solicitacao=instance,
                role='FORMADOR'
            ).values_list('usuario_id', flat=True)
        )

        old_data = {
            "municipio_id": instance.municipio_id,
            "projeto_id": instance.projeto_id,
            "tipo_evento_id": instance.tipo_evento_id,
            "inicio": instance.inicio.isoformat() if instance.inicio else None,
            "fim": instance.fim.isoformat() if instance.fim else None,
            "local": instance.local,
            "observacoes": instance.observacoes,
            "is_online": instance.is_online,
            "coordenador_acompanha": instance.coordenador_acompanha,
            "coordenador_id": instance.coordenador_id,
            "tipo": instance.tipo,
            "encontro": instance.encontro,
            "segmento": instance.segmento,
            "formador_ids": list(old_formador_ids),
        }

        # Salva as alterações
        serializer.save()

        # Processa extra_participants se presente
        extra_participants = self.request.data.get('extra_participants', {})
        if extra_participants and 'formador_ids' in extra_participants:
            self._update_formadores(instance, extra_participants)

        # Coleta dados novos após save
        instance.refresh_from_db()

        # Captura formadores novos
        new_formador_ids = set(
            Participation.objects.filter(
                solicitacao=instance,
                role='FORMADOR'
            ).values_list('usuario_id', flat=True)
        )

        new_data = {
            "municipio_id": instance.municipio_id,
            "projeto_id": instance.projeto_id,
            "tipo_evento_id": instance.tipo_evento_id,
            "inicio": instance.inicio.isoformat() if instance.inicio else None,
            "fim": instance.fim.isoformat() if instance.fim else None,
            "local": instance.local,
            "observacoes": instance.observacoes,
            "is_online": instance.is_online,
            "coordenador_acompanha": instance.coordenador_acompanha,
            "coordenador_id": instance.coordenador_id,
            "tipo": instance.tipo,
            "encontro": instance.encontro,
            "segmento": instance.segmento,
            "formador_ids": list(new_formador_ids),
        }

        # Identifica campos alterados
        changed_fields = {
            k: {"old": old_data[k], "new": new_data[k]}
            for k in old_data
            if old_data[k] != new_data[k]
        }

        # Se houver alterações, registra no AuditLog
        if changed_fields:
            client_ip = _get_client_ip(self.request)

            # Logger estruturado
            logger.info(
                "solicitacao_updated",
                extra={
                    "event": "solicitacao_updated",
                    "user_id": self.request.user.id,
                    "username": self.request.user.username,
                    "solicitation_id": instance.id,
                    "action": "update",
                    "changed_fields": list(changed_fields.keys()),
                    "ip_address": client_ip,
                    "timestamp": timezone.now().isoformat(),
                },
            )

            # AuditLog persistente
            AuditLog.objects.create(
                usuario=self.request.user,
                action="UPDATE",
                model_name="Solicitacao",
                details={
                    "solicitacao_id": instance.id,
                    "changed_fields": changed_fields,
                    "ip_address": client_ip,
                    "user_agent": self.request.META.get("HTTP_USER_AGENT", "")[:200],
                },
            )

    def _update_formadores(self, solicitacao, extra):
        """
        Atualiza formadores de uma solicitação.

        Estratégia: substituição completa
        - Remove formadores não presentes na nova lista
        - Adiciona novos formadores

        Retorna True se houve alteração.
        """
        new_formador_ids = set(extra.get('formador_ids', []))

        # Formadores atuais
        current_participations = Participation.objects.filter(
            solicitacao=solicitacao,
            role='FORMADOR'
        )
        current_ids = set(p.usuario_id for p in current_participations if p.usuario_id)

        # Calcular diferenças
        to_remove = current_ids - new_formador_ids
        to_add = new_formador_ids - current_ids

        changed = False

        # Remover formadores
        if to_remove:
            Participation.objects.filter(
                solicitacao=solicitacao,
                role='FORMADOR',
                usuario_id__in=to_remove
            ).delete()
            changed = True

        # Adicionar formadores (batch fetch para evitar N+1)
        if to_add:
            # Batch fetch de usuários
            usuarios_map = {
                u.id: u for u in Usuario.objects.filter(id__in=to_add)
            }

            # Criar participations em batch
            participations_to_create = [
                Participation(
                    solicitacao=solicitacao,
                    usuario=usuarios_map[fid],
                    role='FORMADOR'
                )
                for fid in to_add
                if fid and fid in usuarios_map
            ]

            if participations_to_create:
                Participation.objects.bulk_create(
                    participations_to_create,
                    ignore_conflicts=True
                )
                changed = True

        return changed

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
