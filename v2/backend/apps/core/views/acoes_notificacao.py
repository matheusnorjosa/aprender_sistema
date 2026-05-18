"""
API endpoints for ciclos/acoes/ancoras/conclusoes/notificacoes (issue #872).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportArgumentType=false

from __future__ import annotations

from typing import Any

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from django_filters.rest_framework import DjangoFilterBackend

from apps.core.models import AcaoInstancia, AcaoTemplate, AuditLog, CicloAcoes, NotificacaoInterna
from apps.core.rbac import HasPerm
from apps.core.serializers import (
    AcaoInstanciaSerializer,
    CicloAcoesSerializer,
    ConcluirAcaoSerializer,
    NotificacaoInternaSerializer,
    RegistrarAncoraSerializer,
)

# Issue #1219 (Epic 1 RBAC Access Policy Realignment, 2026-04-24):
# Módulo "Ações Internas" é superuser-only por ora (feature em desenvolvimento).
# Helpers `_is_dat_or_super` e `_has_any_group` removidos — não são mais
# necessários porque `IsAdminUser` já filtra acesso a superusers apenas.
# QuerySets expõem tudo (superuser vê todos os ciclos/ações).


def _visible_cycles_queryset_for_user(user: AbstractBaseUser | AnonymousUser) -> QuerySet[CicloAcoes]:
    return CicloAcoes.objects.select_related("projeto", "municipio").all()


def _visible_actions_queryset_for_user(user: AbstractBaseUser | AnonymousUser) -> QuerySet[AcaoInstancia]:
    return AcaoInstancia.objects.select_related(
        "template",
        "ciclo",
        "ciclo__projeto",
        "ciclo__municipio",
    ).all()


class CicloAcoesViewSet(viewsets.ModelViewSet):
    """
    CRUD de ciclos + listagem de acoes por ciclo.

    Módulo "Ações Internas" é superuser-only (feature em desenvolvimento).
    """

    serializer_class = CicloAcoesSerializer
    permission_classes = [HasPerm("manage_internal_actions")]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["projeto", "municipio", "semestre", "ano", "status"]
    search_fields = ["projeto__nome", "municipio__nome"]
    ordering_fields = ["ano", "semestre", "created_at", "id"]
    ordering = ["-ano", "semestre", "id"]

    def get_queryset(self) -> QuerySet[CicloAcoes]:
        return _visible_cycles_queryset_for_user(self.request.user)

    def perform_create(self, serializer: CicloAcoesSerializer) -> None:
        with transaction.atomic():
            ciclo = serializer.save(created_by=self.request.user)
            templates = list(AcaoTemplate.objects.filter(ativo=True).order_by("ordem"))
            instances = [
                AcaoInstancia(
                    ciclo=ciclo,
                    template=template,
                    ordem=template.ordem,
                )
                for template in templates
            ]
            AcaoInstancia.objects.bulk_create(instances)

            AuditLog.objects.create(
                usuario=self.request.user,
                action=AuditLog.Action.CICLO_ACOES_CREATE,
                model_name="CicloAcoes",
                details={
                    "ciclo_id": ciclo.id,
                    "projeto_id": ciclo.projeto_id,
                    "municipio_id": ciclo.municipio_id,
                    "semestre": ciclo.semestre,
                    "ano": ciclo.ano,
                    "acoes_criadas": len(instances),
                },
            )

    @action(detail=True, methods=["get"], url_path="acoes")
    def acoes(self, request: Request, pk: Any = None) -> Response:
        ciclo = self.get_object()
        actions_qs = _visible_actions_queryset_for_user(request.user).filter(ciclo_id=ciclo.id).order_by("ordem")
        page = self.paginate_queryset(actions_qs)
        serializer = AcaoInstanciaSerializer(page if page is not None else actions_qs, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)


class AcaoInstanciaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Listagem de acoes e comandos operacionais (âncora/conclusão).

    Módulo "Ações Internas" é superuser-only (feature em desenvolvimento).
    """

    serializer_class = AcaoInstanciaSerializer
    permission_classes = [HasPerm("manage_internal_actions")]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["ciclo", "estado", "ordem"]
    ordering_fields = ["ordem", "estado", "data_vencimento", "created_at"]
    ordering = ["ordem"]

    def get_queryset(self) -> QuerySet[AcaoInstancia]:
        return _visible_actions_queryset_for_user(self.request.user)

    @action(detail=True, methods=["post"], url_path="registrar-ancora")
    def registrar_ancora(self, request: Request, pk: Any = None) -> Response:
        serializer = RegistrarAncoraSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            action_instance = AcaoInstancia.objects.select_for_update().get(pk=self.get_object().pk)

            try:
                registro = action_instance.registrar_ancora(
                    data_ancora=serializer.validated_data["data_ancora"],
                    usuario=request.user,
                    observacao=serializer.validated_data.get("observacao", ""),
                )
            except DjangoValidationError as exc:
                raise ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages) from exc

            AuditLog.objects.create(
                usuario=request.user,
                action=AuditLog.Action.ACAO_REGISTRAR_ANCORA,
                model_name="AcaoInstancia",
                details={
                    "acao_instancia_id": action_instance.id,
                    "ciclo_id": action_instance.ciclo_id,
                    "ordem": action_instance.ordem,
                    "registro_ancora_id": registro.id,
                    "data_ancora": str(registro.data_ancora),
                },
            )

        output = AcaoInstanciaSerializer(action_instance).data
        return Response(output, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="concluir")
    def concluir(self, request: Request, pk: Any = None) -> Response:
        action_instance = self.get_object()
        serializer = ConcluirAcaoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            registro = action_instance.concluir(
                data_realizacao=serializer.validated_data["data_realizacao"],
                observacao=serializer.validated_data["observacao"],
                usuario=request.user,
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages) from exc

        AuditLog.objects.create(
            usuario=request.user,
            action=AuditLog.Action.ACAO_CONCLUIR,
            model_name="AcaoInstancia",
            details={
                "acao_instancia_id": action_instance.id,
                "ciclo_id": action_instance.ciclo_id,
                "ordem": action_instance.ordem,
                "registro_conclusao_id": registro.id,
                "data_realizacao": str(registro.data_realizacao),
            },
        )

        output = AcaoInstanciaSerializer(action_instance).data
        return Response(output, status=status.HTTP_200_OK)


class NotificacaoInternaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Inbox de notificacoes in-app do usuario logado.
    """

    serializer_class = NotificacaoInternaSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["lida", "tipo", "nivel", "fase_disparo", "referencia_data"]
    ordering_fields = ["created_at", "referencia_data", "prioridade"]
    ordering = ["-created_at"]

    def get_queryset(self) -> QuerySet[NotificacaoInterna]:
        return NotificacaoInterna.objects.filter(destinatario=self.request.user).select_related("acao_instancia")

    @action(detail=True, methods=["post"], url_path="marcar-lida")
    def marcar_lida(self, request: Request, pk: Any = None) -> Response:
        notificacao = self.get_object()
        notificacao.marcar_lida()
        return Response(NotificacaoInternaSerializer(notificacao).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request: Request) -> Response:
        count = self.get_queryset().filter(lida=False).count()
        return Response({"count": count}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="marcar-todas-lidas")
    def marcar_todas_lidas(self, request: Request) -> Response:
        now = timezone.now()
        updated = self.get_queryset().filter(lida=False).update(lida=True, lida_em=now, updated_at=now)
        return Response({"updated": updated}, status=status.HTTP_200_OK)
