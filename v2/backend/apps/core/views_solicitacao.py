"""
Solicitacao ViewSet (views ativas)

§1 Epic #459: Refactored to use service layer for approval/publish operations.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false, reportFunctionMemberAccess=false

from __future__ import annotations

import logging
from typing import Any

from django.db.models import QuerySet
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema, extend_schema_view

from apps.core.rbac_helpers import user_has_any_perm

from .api_schemas import (
    COMMON_ERROR_RESPONSES,
    SOLICITACAO_BATCH_APPROVE_REQUEST,
    SOLICITACAO_BATCH_APPROVE_RESPONSE,
    SOLICITACAO_CREATE_ONLINE_EXAMPLE,
    SOLICITACAO_CREATE_PRESENCIAL_EXAMPLE,
    SOLICITACAO_CREATED_EXAMPLE,
)
from .models import AuditLog, Solicitacao
from .permissions import HasPerm, IsOwnerOrPrivileged
from .rbac.policies import CanAccessSolicitacaoApprovals, CanUseGcal
from .serializers import SolicitacaoSerializer
from .services.solicitacao_approval import (
    approve_solicitacao,
    batch_approve_solicitacoes,
    batch_reject_solicitacoes,
    reject_solicitacao,
)
from .services.solicitacao_create import resolve_initial_status
from .services.solicitacao_publish import cancel_from_gcal
from .services.solicitacao_publish import preview_gcal as preview_gcal_service
from .services.solicitacao_publish import publish_to_gcal, resync_to_gcal

logger = logging.getLogger(__name__)


def _get_client_ip(request: Request) -> str:
    """Extract real client IP considering reverse proxies."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    x_real_ip = request.META.get("HTTP_X_REAL_IP")
    if x_real_ip:
        return x_real_ip.strip()
    return request.META.get("REMOTE_ADDR", "unknown")


@extend_schema_view(
    list=extend_schema(
        summary="Lista solicitações",
        description="Retorna lista paginada de solicitações filtradas por status, projeto, etc.",
        parameters=[
            OpenApiParameter(
                "status", OpenApiTypes.STR, description="Filtrar por status (pendente/aprovado/reprovado)"
            ),
            OpenApiParameter(
                "mine", OpenApiTypes.BOOL, description="Se true, retorna apenas solicitações do usuário atual"
            ),
            OpenApiParameter(
                "search", OpenApiTypes.STR, description="Busca textual em usuário, município, observações"
            ),
        ],
        responses={200: SolicitacaoSerializer(many=True), **COMMON_ERROR_RESPONSES},
        tags=["solicitacoes"],
    ),
    retrieve=extend_schema(
        summary="Detalhe da solicitação",
        description="Retorna detalhes completos de uma solicitação específica.",
        responses={200: SolicitacaoSerializer, **COMMON_ERROR_RESPONSES},
        tags=["solicitacoes"],
    ),
    create=extend_schema(
        summary="Criar solicitação",
        description="""Cria nova solicitação de evento.

## Fluxo
1. Frontend envia dados do wizard (4 steps)
2. Backend valida disponibilidade (RD-01~08)
3. Status inicial: `pendente` (SUPER) ou `aprovado` (NAO_SUPER) conforme PA-01

## Exemplo curl
```bash
curl -X POST /api/v1/solicitacoes/ \\
  -H "Content-Type: application/json" \\
  -H "X-CSRFToken: $CSRF" \\
  -d '{"titulo": "Formacao", "inicio": "2026-01-20T09:00:00-03:00", ...}'
```
""",
        request=SolicitacaoSerializer,
        responses={201: SolicitacaoSerializer, **COMMON_ERROR_RESPONSES},
        examples=[
            SOLICITACAO_CREATE_PRESENCIAL_EXAMPLE,
            SOLICITACAO_CREATE_ONLINE_EXAMPLE,
            SOLICITACAO_CREATED_EXAMPLE,
        ],
        tags=["solicitacoes"],
    ),
    update=extend_schema(
        summary="Atualizar solicitação",
        description="Atualiza todos os campos de uma solicitação. Requer ser o proprietário ou ter privilégio especial.",
        request=SolicitacaoSerializer,
        responses={200: SolicitacaoSerializer, **COMMON_ERROR_RESPONSES},
        tags=["solicitacoes"],
    ),
    partial_update=extend_schema(
        summary="Atualizar parcialmente",
        description="Atualiza campos específicos de uma solicitação.",
        request=SolicitacaoSerializer,
        responses={200: SolicitacaoSerializer, **COMMON_ERROR_RESPONSES},
        tags=["solicitacoes"],
    ),
    destroy=extend_schema(
        summary="Excluir solicitação",
        description="Remove uma solicitação. Requer ser o proprietário ou ter privilégio especial.",
        responses={204: None, **COMMON_ERROR_RESPONSES},
        tags=["solicitacoes"],
    ),
)
class SolicitacaoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para Solicitações de Evento.

    PA-01: Status sempre começa pendente.
    PA-02 (Adaptada): Superintendência, DAT e Superusuários podem aprovar/reprovar.
    PR 8/N: Apenas Coordenador ou DAT podem criar solicitações.
    """

    queryset = Solicitacao.objects.select_related("usuario", "municipio", "tipo_evento", "projeto", "coordenador")
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
        # Actions com permission_classes específicas definidas no decorator
        # Não sobrescrever nesses casos - usar super() para pegar do decorator
        actions_with_custom_permissions = [
            "approve",
            "reject",
            "preview_gcal",
            "publish",
            "resync_gcal",
            "cancel_gcal",
            "batch_approve",
            "batch_reject",
        ]
        if self.action in actions_with_custom_permissions:
            return super().get_permissions()
        if self.action == "create":
            return [HasPerm("create_solicitation")()]
        if self.action in ["update", "partial_update", "destroy"]:
            return [IsOwnerOrPrivileged()]
        return [IsAuthenticated()]

    def get_queryset(self) -> QuerySet:
        # PR15: Filtro mine força filtro por usuário (mesmo para superusers)
        mine = self.request.query_params.get("mine")

        # Base queryset (permissões)
        if mine == "true":
            # Forçar filtro por usuário atual
            qs = (
                Solicitacao.objects.filter(usuario=self.request.user)
                .select_related("usuario", "municipio", "tipo_evento", "projeto", "coordenador")
                .prefetch_related("participations__usuario")
            )
        # Epic 3.2 RBAC Refactor (2026-04-23): hardcoded
        # `groups.filter(name__in=["Superintendência", "Controle", "DAT"])`
        # trocado por capability check.
        # Issue #1222 (Epic 1 RBAC Access Policy Realignment, 2026-04-24):
        # após realinhamento do seed, `operate_preagenda` ficou só em Controle.
        # Super (que aprova solicitações) precisa ver todas; adicionada
        # `approve_solicitation` ao OR para preservar visibilidade de Super.
        elif user_has_any_perm(
            self.request.user,
            "operate_preagenda",
            "approve_solicitation",
            "approve_solicitation_batch",
            "manage_admin_registries",
        ):
            qs = Solicitacao.objects.select_related(
                "usuario", "municipio", "tipo_evento", "projeto", "coordenador"
            ).prefetch_related("participations__usuario")
        else:
            qs = (
                Solicitacao.objects.filter(usuario=self.request.user)
                .select_related("usuario", "municipio", "tipo_evento", "projeto", "coordenador")
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
        STATUS_MAP = {"pending": "pendente", "approved": "aprovado", "rejected": "reprovado"}

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
        from .exceptions import ValidationAPIError
        from .services.availability_service import check_conflicts

        inicio = serializer.validated_data.get("inicio")
        fim = serializer.validated_data.get("fim")
        municipio = serializer.validated_data.get("municipio")

        if inicio is not None and fim is not None:
            result = check_conflicts(usuario=self.request.user, inicio=inicio, fim=fim, municipio=municipio)
            if not result.ok:
                raise ValidationAPIError(
                    message="Conflito de disponibilidade detectado.",
                    code="availability_conflict",
                    extra={"conflicts": [c.__dict__ for c in result.conflicts]},
                )

        projeto = serializer.validated_data.get("projeto")
        initial_status = resolve_initial_status(projeto=projeto)

        # ASQ-002: status inicial decidido em camada de serviço (não no model.save()).
        instance = serializer.save(usuario=self.request.user, status=initial_status.status)

        logger.info(
            "solicitacao_initial_status_decided",
            extra={
                "event": "solicitacao_initial_status_decided",
                "user_id": self.request.user.id,
                "username": self.request.user.username,
                "solicitacao_id": instance.id,
                "projeto_id": getattr(projeto, "id", None),
                "projeto_fluxo": initial_status.fluxo,
                "initial_status": initial_status.status,
                "reason": initial_status.reason,
            },
        )

        # PR15: Processar extra_participants
        extra_participants = self.request.data.get("extra_participants", {})
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
        Participation.objects.get_or_create(solicitacao=solicitacao, usuario=self.request.user, role="COORDENADOR")

        # PERF-SQL-02: Batch fetch all referenced users in 2 queries instead of N
        all_ids = set()
        all_ids.update(fid for fid in extra.get("formador_ids", []) if fid)
        all_ids.update(cid for cid in extra.get("coord_acompanha_ids", []) if cid)
        usuarios_by_id = {u.id: u for u in Usuario.objects.filter(id__in=all_ids)} if all_ids else {}

        all_emails = set()
        all_emails.update(e.strip().lower() for e in extra.get("formador_emails", []) if e and e.strip())
        all_emails.update(e.strip().lower() for e in extra.get("coord_acompanha_emails", []) if e and e.strip())
        usuarios_by_email = (
            {u.email.lower(): u for u in Usuario.objects.filter(email__in=all_emails)} if all_emails else {}
        )

        # Formadores por ID
        for formador_id in extra.get("formador_ids", []):
            if formador_id:
                usuario = usuarios_by_id.get(formador_id)
                if usuario:
                    Participation.objects.get_or_create(solicitacao=solicitacao, usuario=usuario, role="FORMADOR")

        # Formadores por email (guest)
        for email in extra.get("formador_emails", []):
            if email and email.strip():
                usuario = usuarios_by_email.get(email.strip().lower())
                if usuario:
                    Participation.objects.get_or_create(solicitacao=solicitacao, usuario=usuario, role="FORMADOR")
                else:
                    # Criar como guest_email mantendo role=FORMADOR para GCal
                    Participation.objects.get_or_create(
                        solicitacao=solicitacao, guest_email=email.strip().lower(), role="FORMADOR"
                    )

        # Coordenadores acompanhantes por ID
        for coord_id in extra.get("coord_acompanha_ids", []):
            if coord_id:
                usuario = usuarios_by_id.get(coord_id)
                if usuario:
                    Participation.objects.get_or_create(
                        solicitacao=solicitacao, usuario=usuario, role="COORD_ACOMPANHA"
                    )

        # Coordenadores acompanhantes por email (guest)
        for email in extra.get("coord_acompanha_emails", []):
            if email and email.strip():
                usuario = usuarios_by_email.get(email.strip().lower())
                if usuario:
                    Participation.objects.get_or_create(
                        solicitacao=solicitacao, usuario=usuario, role="COORD_ACOMPANHA"
                    )
                else:
                    # Criar como guest_email mantendo role=COORD_ACOMPANHA para GCal
                    Participation.objects.get_or_create(
                        solicitacao=solicitacao, guest_email=email.strip().lower(), role="COORD_ACOMPANHA"
                    )

    def perform_update(self, serializer):
        """
        Registra edição de solicitação no AuditLog.

        Rastreia:
        - Campos alterados (antes/depois)
        - Formadores alterados (adicionados/removidos)
        - Usuário que editou
        - IP e User-Agent
        """
        from .models import Participation, Usuario

        instance = serializer.instance

        # Captura formadores atuais antes do update
        old_formador_ids = set(
            Participation.objects.filter(solicitacao=instance, role="FORMADOR").values_list("usuario_id", flat=True)
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
        extra_participants = self.request.data.get("extra_participants", {})
        if extra_participants and "formador_ids" in extra_participants:
            self._update_formadores(instance, extra_participants)

        # Coleta dados novos após save
        instance.refresh_from_db()

        # Captura formadores novos
        new_formador_ids = set(
            Participation.objects.filter(solicitacao=instance, role="FORMADOR").values_list("usuario_id", flat=True)
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
        changed_fields = {k: {"old": old_data[k], "new": new_data[k]} for k in old_data if old_data[k] != new_data[k]}

        # Se houver alterações, registra no AuditLog
        if changed_fields:
            client_ip = _get_client_ip(self.request)

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
        - Adiciona novos formadores com batch fetch (#406)

        Retorna True se houve alteração.
        """
        from .models import Participation, Usuario

        new_formador_ids = set(extra.get("formador_ids", []))

        # Formadores atuais
        current_participations = Participation.objects.filter(solicitacao=solicitacao, role="FORMADOR")
        current_ids = set(p.usuario_id for p in current_participations if p.usuario_id)

        # Calcular diferenças
        to_remove = current_ids - new_formador_ids
        to_add = new_formador_ids - current_ids

        changed = False

        # Remover formadores
        if to_remove:
            Participation.objects.filter(solicitacao=solicitacao, role="FORMADOR", usuario_id__in=to_remove).delete()
            changed = True

        # Adicionar formadores com batch fetch (#406 - Query Optimization)
        if to_add:
            # Batch fetch: 1 query para todos os usuários em vez de N queries
            usuarios_map = {u.id: u for u in Usuario.objects.filter(id__in=to_add)}

            # Bulk create participations
            participations_to_create = [
                Participation(solicitacao=solicitacao, usuario=usuarios_map[formador_id], role="FORMADOR")
                for formador_id in to_add
                if formador_id and formador_id in usuarios_map
            ]

            if participations_to_create:
                Participation.objects.bulk_create(participations_to_create, ignore_conflicts=True)
                changed = True

        return changed

    def perform_destroy(self, instance):
        """
        Exclui solicitação com validações e AuditLog.

        Regras por fluxo do projeto:
        - SUPER: Pode excluir apenas se status=pendente E não publicado no GCal
        - NAO_SUPER: Pode excluir se não publicado no GCal (auto-aprovado)

        Registra exclusão no AuditLog antes de deletar.
        """
        from rest_framework.exceptions import ValidationError

        # Bloquear exclusão de solicitações publicadas (ambos os fluxos)
        if instance.gcal_status == "PUBLISHED":
            raise ValidationError(
                {
                    "detail": "Não é possível excluir uma solicitação já publicada no Google Calendar. "
                    "Cancele o evento primeiro se precisar excluir."
                }
            )

        # Validação adicional para fluxo SUPER
        projeto_fluxo = instance.projeto.fluxo if instance.projeto else None
        if projeto_fluxo == "SUPER" and instance.status != "pendente":
            raise ValidationError(
                {
                    "detail": "Solicitações do fluxo SUPER só podem ser excluídas enquanto estiverem pendentes. "
                    "Esta solicitação já foi aprovada ou reprovada."
                }
            )

        # Capturar dados antes da exclusão para o AuditLog
        solicitacao_data = {
            "id": instance.id,
            "municipio_id": instance.municipio_id,
            "municipio_nome": instance.municipio.nome if instance.municipio else None,
            "projeto_id": instance.projeto_id,
            "projeto_nome": instance.projeto.nome if instance.projeto else None,
            "tipo_evento_id": instance.tipo_evento_id,
            "inicio": instance.inicio.isoformat() if instance.inicio else None,
            "fim": instance.fim.isoformat() if instance.fim else None,
            "status": instance.status,
        }

        client_ip = _get_client_ip(self.request)

        # Registrar exclusão no AuditLog ANTES de deletar
        AuditLog.objects.create(
            usuario=self.request.user,
            action="DELETE",
            model_name="Solicitacao",
            details={
                "solicitacao_data": solicitacao_data,
                "ip_address": client_ip,
                "user_agent": self.request.META.get("HTTP_USER_AGENT", "")[:200],
            },
        )

        # Executar exclusão
        instance.delete()

    @extend_schema(
        summary="Aprovar solicitação",
        description="Aprova uma solicitação pendente. Apenas Superintendência, DAT ou superuser (PA-02).",
        request=None,
        responses={
            200: SolicitacaoSerializer,
            400: COMMON_ERROR_RESPONSES[400],
            403: COMMON_ERROR_RESPONSES[403],
        },
        tags=["solicitacoes"],
    )
    @action(
        detail=True,
        methods=["patch"],
        permission_classes=[CanAccessSolicitacaoApprovals],
        url_path="approve",
    )
    def approve(self, request, pk=None):
        """Aprovar solicitação (PA-02 Adaptada: Superintendência, DAT e Superusuários)."""
        solicitacao = self.get_object()
        justificativa = request.data.get("reason") or request.data.get("justificativa", "")

        # §1 Epic #459: Delegate to service layer
        result = approve_solicitacao(
            solicitacao=solicitacao,
            user=request.user,
            request=request,
            justificativa=justificativa,
        )

        return Response(
            {
                "detail": result.message,
                "solicitacao": SolicitacaoSerializer(result.solicitacao).data,
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Reprovar solicitação",
        description="Reprova uma solicitação pendente. Requer justificativa. Apenas Superintendência, DAT ou superuser (PA-02).",
        request=None,
        responses={
            200: SolicitacaoSerializer,
            400: COMMON_ERROR_RESPONSES[400],
            403: COMMON_ERROR_RESPONSES[403],
        },
        tags=["solicitacoes"],
    )
    @action(
        detail=True,
        methods=["patch"],
        permission_classes=[CanAccessSolicitacaoApprovals],
        url_path="reject",
    )
    def reject(self, request, pk=None):
        """Reprovar solicitação (PA-02 Adaptada: Superintendência, DAT e Superusuários)."""
        solicitacao = self.get_object()
        justificativa = request.data.get("reason") or request.data.get("justificativa", "")

        # §1 Epic #459: Delegate to service layer
        result = reject_solicitacao(
            solicitacao=solicitacao,
            user=request.user,
            request=request,
            justificativa=justificativa,
        )

        return Response(
            {
                "detail": result.message,
                "solicitacao": SolicitacaoSerializer(result.solicitacao).data,
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        # Issue #1233 (Epic 4.2.a): operações GCal usam Policy `use_gcal`
        # (Controle + Super). Antes Epic 1.6 já havia composto `operate_preagenda
        # | approve_solicitation` aqui — agora encapsulado em CanUseGcal.
        permission_classes=[CanUseGcal],
        url_path="preview-gcal",
    )
    def preview_gcal(self, request, pk=None):
        """Preview do payload GCal sem publicar (Controle ou Superintendência)."""
        solicitacao = self.get_object()

        # §1 Epic #459: Delegate to service layer
        result = preview_gcal_service(
            solicitacao=solicitacao,
            user=request.user,
            request=request,
        )

        return Response(
            {
                "detail": result.message,
                "preview": result.preview,
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        # Issue #1233 (Epic 4.2.a): operações GCal usam Policy `use_gcal`
        # (Controle + Super). Antes Epic 1.6 já havia composto `operate_preagenda
        # | approve_solicitation` aqui — agora encapsulado em CanUseGcal.
        permission_classes=[CanUseGcal],
        url_path="publish",
    )
    def publish(self, request, pk=None):
        """Publica solicitação no Google Calendar via Celery (Controle ou Superintendência)."""
        solicitacao = self.get_object()
        dry_run = request.data.get("dry_run", False)
        apply_blocked = request.data.get("apply_blocked", False)

        # §1 Epic #459: Delegate to service layer
        result = publish_to_gcal(
            solicitacao=solicitacao,
            user=request.user,
            request=request,
            dry_run=dry_run,
            apply_blocked=apply_blocked,
        )

        return Response(
            {
                "detail": result.message,
                "task_id": result.task_id,
                "solicitacao_id": result.solicitacao_id,
            },
            status=status.HTTP_202_ACCEPTED,
        )

    @action(
        detail=True,
        methods=["post"],
        # Issue #1233 (Epic 4.2.a): operações GCal usam Policy `use_gcal`
        # (Controle + Super). Antes Epic 1.6 já havia composto `operate_preagenda
        # | approve_solicitation` aqui — agora encapsulado em CanUseGcal.
        permission_classes=[CanUseGcal],
        url_path="resync-gcal",
    )
    def resync_gcal(self, request, pk=None):
        """
        Republicar solicitação no Google Calendar (força UPDATE) - Fase 4.

        Permissão: Controle ou Superintendência
        Returns: 202 Accepted (processamento assíncrono)
        """
        solicitacao = self.get_object()

        # §1 Epic #459: Delegate to service layer
        result = resync_to_gcal(
            solicitacao=solicitacao,
            user=request.user,
            request=request,
        )

        return Response(
            {
                "detail": result.message,
                "task_id": result.task_id,
                "solicitacao_id": result.solicitacao_id,
            },
            status=status.HTTP_202_ACCEPTED,
        )

    @action(
        detail=True,
        methods=["post"],
        # Issue #1233 (Epic 4.2.a): operações GCal usam Policy `use_gcal`
        # (Controle + Super). Antes Epic 1.6 já havia composto `operate_preagenda
        # | approve_solicitation` aqui — agora encapsulado em CanUseGcal.
        permission_classes=[CanUseGcal],
        url_path="cancel-gcal",
    )
    def cancel_gcal(self, request, pk=None):
        """
        Cancelar evento no Google Calendar e limpar campos - Fase 4.

        Permissão: Controle ou Superintendência
        Returns: 202 Accepted (processamento assíncrono)
        """
        solicitacao = self.get_object()

        # §1 Epic #459: Delegate to service layer
        result = cancel_from_gcal(
            solicitacao=solicitacao,
            user=request.user,
            request=request,
        )

        return Response(
            {
                "detail": result.message,
                "task_id": result.task_id,
                "solicitacao_id": result.solicitacao_id,
            },
            status=status.HTTP_202_ACCEPTED,
        )

    @extend_schema(
        summary="Aprovar em lote",
        description="Aprova múltiplas solicitações em lote (PA-05). Máx 100 por requisição.",
        request={"type": "object", "properties": {"ids": {"type": "array", "items": {"type": "integer"}}}},
        responses={
            200: {"type": "object", "properties": {"approved": {"type": "integer"}, "errors": {"type": "array"}}}
        },
        examples=[SOLICITACAO_BATCH_APPROVE_REQUEST, SOLICITACAO_BATCH_APPROVE_RESPONSE],
        tags=["solicitacoes"],
    )
    @action(
        detail=False,
        methods=["post"],
        permission_classes=[CanAccessSolicitacaoApprovals],
        url_path="batch-approve",
    )
    def batch_approve(self, request):
        """
        Aprovar múltiplas solicitações em lote.

        POST /api/solicitacoes/batch-approve/
        Body: { "ids": [1, 2, 3] }

        Response 200: { "approved": 2, "errors": [{"id": 3, "detail": "..."}] }

        Permissão: Superintendência, DAT ou superusers (PA-02 Adaptada).
        PA-05: Cada solicitação gera um AuditLog individual com batch=true.
        Limite: máximo 100 solicitações por requisição.
        """
        ids = request.data.get("ids", [])

        # §1 Epic #459: Delegate to service layer
        result = batch_approve_solicitacoes(
            ids=ids,
            user=request.user,
            request=request,
        )

        return Response(
            {
                "approved": result.approved_count,
                "errors": result.errors,
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=False,
        methods=["post"],
        permission_classes=[CanAccessSolicitacaoApprovals],
        url_path="batch-reject",
    )
    def batch_reject(self, request):
        """
        Reprovar múltiplas solicitações em lote.

        POST /api/solicitacoes/batch-reject/
        Body: { "ids": [1, 2, 3] }

        Response 200: { "rejected": 2, "errors": [{"id": 3, "detail": "..."}] }

        Permissão: Superintendência, DAT ou superusers (PA-02 Adaptada).
        PA-05: Cada solicitação gera um AuditLog individual com batch=true.
        Limite: máximo 100 solicitações por requisição.
        """
        ids = request.data.get("ids", [])

        # §1 Epic #459: Delegate to service layer
        result = batch_reject_solicitacoes(
            ids=ids,
            user=request.user,
            request=request,
        )

        return Response(
            {
                "rejected": result.rejected_count,
                "errors": result.errors,
            },
            status=status.HTTP_200_OK,
        )
