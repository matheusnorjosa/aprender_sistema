"""
AS v2 — Me Views

Endpoints `/api/me/*` para o usuário autenticado.

Issue #1224 (Epic 2 RBAC Access Policy Realignment): novo endpoint
`GET /api/me/events/` lista eventos onde o user é participante. Formador é
o caso primário (única página acessível por intent matrix); qualquer user
autenticado pode chamar.

Type-checked with Pyright (strict mode).
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false

from __future__ import annotations

from django.db.models import QuerySet
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from drf_spectacular.utils import extend_schema, extend_schema_view

from apps.core.api_schemas import COMMON_ERROR_RESPONSES
from apps.core.models import Solicitacao
from apps.core.serializers.me import MeEventSerializer


@extend_schema_view(
    get=extend_schema(
        summary="Listar eventos do usuário autenticado",
        description=(
            "Retorna a lista paginada de eventos (Solicitacoes aprovadas) onde o "
            "usuário autenticado é participante (qualquer role). Formador é o caso "
            "primário, mas qualquer user autenticado pode consumir."
        ),
        responses={
            200: MeEventSerializer(many=True),
            401: COMMON_ERROR_RESPONSES[401],
        },
        tags=["me"],
    )
)
class MeEventsListView(generics.ListAPIView):
    """
    Lista eventos em que o user autenticado é participante.

    GET /api/me/events/

    Filtros aplicados:
        - participations__usuario = request.user
        - status = "aprovado" (eventos pendentes/reprovados não aparecem)

    Ordenação: -inicio (mais recente primeiro).
    Paginação: padrão DRF (PageNumberPagination).
    """

    serializer_class = MeEventSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self) -> QuerySet[Solicitacao]:
        return (
            Solicitacao.objects.filter(
                participations__usuario=self.request.user,
                status="aprovado",
            )
            .select_related("municipio", "projeto", "tipo_evento")
            .prefetch_related("participations__usuario")
            .order_by("-inicio")
            .distinct()
        )
