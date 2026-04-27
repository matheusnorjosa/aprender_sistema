"""
AS v2 — Me Views

Endpoints `/api/me/*` para o usuário autenticado.

Issue #1224 (Epic 2 RBAC Access Policy Realignment): novo endpoint
`GET /api/me/events/` lista eventos onde o user é participante. Formador é
o caso primário (única página acessível por intent matrix); qualquer user
autenticado pode chamar.

Issue #1235 (Epic 4.4): `GET /api/me/policies/` expõe a lista ordenada de
PUBLIC_POLICY_KEYS que o usuário possui — contrato externo consumido pelo
frontend para menu condicional, redirects, mensagens de erro genéricas.

Type-checked with Pyright (strict mode).
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false

from __future__ import annotations

from django.db.models import QuerySet
from rest_framework import generics, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema, extend_schema_view, inline_serializer

from apps.core.api_schemas import COMMON_ERROR_RESPONSES
from apps.core.models import Solicitacao
from apps.core.rbac.policies import resolve_public_policies
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


@extend_schema_view(
    get=extend_schema(
        summary="Listar policies do usuário autenticado",
        description=(
            "Retorna a lista ordenada das policy keys públicas que o usuário "
            "autenticado possui (subset de `PUBLIC_POLICY_KEYS`). Frontend usa "
            "esta lista para menu condicional, redirects e mensagens de erro "
            "genéricas (ex: `policies.includes('view_compras_dashboard')`).\n\n"
            "Semântica:\n"
            "- Anonymous → 401\n"
            "- Authenticated sem capabilities → []\n"
            "- Superuser → todas as PUBLIC_POLICY_KEYS\n"
            "- User regular → subset baseado em capabilities (OR semantics)\n\n"
            "Contrato: response NUNCA contém capability codenames brutos — "
            "expõe apenas policy keys do registro público. Keys são imutáveis "
            "após release (renomear = breaking; ver `feedback_capability_policy_layer_pattern.md` §6)."
        ),
        responses={
            200: inline_serializer(
                name="MePoliciesResponse",
                fields={"policies": serializers.ListField(child=serializers.CharField())},
            ),
            401: COMMON_ERROR_RESPONSES[401],
        },
        tags=["me"],
    )
)
class MePoliciesView(APIView):
    """
    Lista policy keys públicas que o user autenticado possui.

    GET /api/me/policies/

    Response: JSON array de strings, ordenado alfabeticamente.
    Exemplo: `["access_audit_logs", "use_gcal", "view_compras_dashboard"]`

    Permission: `IsAuthenticated`. Anonymous → 401. Superuser bypass.

    Implementação delega para `apps.core.rbac.policies.resolve_public_policies`
    (SSOT). Cache-aware via `user_has_any_perm` — ~15 lookups O(1) por request
    após primeiro hit.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        return Response(resolve_public_policies(request.user))
