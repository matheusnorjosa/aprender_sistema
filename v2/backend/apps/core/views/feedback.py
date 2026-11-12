"""
AS v2 — Feedback de uso da plataforma (pedido do dono, 11/11/2026)

- POST /api/feedback/: qualquer pessoa logada envia (botão "Dar feedback"); throttle `feedback` por pessoa.
- GET /api/feedback/ e GET /api/feedback/exportar/ (CSV): o superusuário e o DAT, pela capacidade
  `manage_admin_registries` (pacote ADMIN_OPERACIONAL), a mesma das telas de administração do DAT.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false, reportIncompatibleVariableOverride=false, reportIncompatibleMethodOverride=false

from __future__ import annotations

import csv
from typing import Any

from django.http import HttpResponse
from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request

from django_filters import rest_framework as filters
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema

from apps.core.models import Feedback
from apps.core.rbac import HasPerm
from apps.core.serializers.feedback import FeedbackSerializer
from apps.core.utils.csv_sanitize import sanitize_csv_value


class FeedbackFilter(filters.FilterSet):
    """tipo, nota e o período (`desde`/`ate`, dias de Fortaleza, inclusivos)."""

    desde = filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    ate = filters.DateFilter(field_name="created_at", lookup_expr="date__lte")

    class Meta:  # type: ignore[misc]
        model = Feedback
        fields = ["tipo", "nota"]


class FeedbackViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = Feedback.objects.select_related("usuario").order_by("-created_at", "-id")
    serializer_class = FeedbackSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = FeedbackFilter

    @property
    def throttle_scope(self) -> str | None:  # lido pelo ScopedRateThrottle
        return {"create": "feedback", "exportar": "export"}.get(getattr(self, "action", None) or "")

    def get_permissions(self) -> list[Any]:
        # Os @action não declaram permission_classes: quem decide é só este método.
        if self.action == "create":
            return [IsAuthenticated()]
        return [HasPerm("manage_admin_registries")()]

    def perform_create(self, serializer: FeedbackSerializer) -> None:
        serializer.save(usuario=self.request.user)

    @extend_schema(responses={(200, "text/csv"): OpenApiTypes.STR}, summary="Exportar feedbacks (CSV)")
    @action(detail=False, methods=["get"])
    def exportar(self, request: Request) -> HttpResponse:
        """CSV com os mesmos filtros da lista. A pessoa vai pelo nome, nunca pelo CPF ou login."""
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="feedbacks.csv"'
        response.write("﻿")  # BOM: o Excel abre os acentos certos
        writer = csv.writer(response)
        writer.writerow(["Data", "Pessoa", "Nota", "Tipo", "Tela", "Comentário"])
        for fb in self.filter_queryset(self.get_queryset()):
            writer.writerow(
                [
                    timezone.localtime(fb.created_at).strftime("%d/%m/%Y %H:%M"),
                    sanitize_csv_value(str(fb.usuario) if fb.usuario is not None else "Usuário removido"),
                    fb.nota,
                    fb.get_tipo_display(),
                    sanitize_csv_value(fb.pagina),
                    sanitize_csv_value(fb.comentario),
                ]
            )
        return response
