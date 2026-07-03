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

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalSubscript=false, reportIndexIssue=false

from __future__ import annotations

from typing import cast

from django.contrib.auth import update_session_auth_hash
from django.db.models import QuerySet
from rest_framework import generics, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema, extend_schema_view, inline_serializer

from apps.core.api_schemas import COMMON_ERROR_RESPONSES
from apps.core.models import AuditLog, Solicitacao, Usuario
from apps.core.rbac.policies import resolve_public_policies
from apps.core.serializers.me import MeEventSerializer
from apps.core.serializers.usuario import ChangePasswordSerializer


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


class ChangePasswordView(APIView):
    """Troca self-service da propria senha.

    POST /api/me/change-password/

    Login e por CPF + senha (SessionAuthentication). Qualquer usuario autenticado troca
    a propria senha: valida a senha atual + a nova (validadores do Django), atualiza o
    hash da sessao (mantem a atual viva; invalida as OUTRAS) e audita (PA-05,
    CHANGE_PASSWORD). Nunca loga a senha.
    """

    permission_classes = [IsAuthenticated]
    throttle_scope = "change_password"

    @extend_schema(
        summary="Trocar a propria senha",
        request=ChangePasswordSerializer,
        responses={
            200: inline_serializer(
                name="ChangePasswordResponse",
                fields={"detail": serializers.CharField()},
            ),
            401: COMMON_ERROR_RESPONSES[401],
        },
        tags=["me"],
    )
    def post(self, request: Request) -> Response:
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = cast(Usuario, request.user)
        new_password = cast(str, serializer.validated_data["new_password"])
        user.set_password(new_password)
        user.save(update_fields=["password"])
        # SessionAuthentication: mantem a sessao atual valida e invalida as demais.
        update_session_auth_hash(request, user)
        AuditLog.objects.create(
            usuario=user,
            action=AuditLog.Action.CHANGE_PASSWORD,
            model_name="Usuario",
            details={
                "ip_address": (
                    request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
                    or request.META.get("REMOTE_ADDR", "")
                ),
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:200],
            },
        )
        return Response({"detail": "Senha alterada com sucesso."})
