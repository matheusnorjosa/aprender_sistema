"""
Stats API — Estatísticas para HomePage.

GET /api/stats/home/ retorna métricas personalizadas por perfil:
- pending_approvals: para quem pode aprovar (capability `approve_solicitation` ou bypass DAT)
- upcoming_events: scope explícito por capability + ownership + EquipeGerencia (fail-safe)
- my_requests: solicitações do próprio usuário (owner-based)

Onda 2A — refactor coeso (#1284 + #1260, 2026-04-27):

1. **#1284 (P0)** — `upcoming_events` ganha fail-safe explícito. Antes, o `else`
   implícito permitia que user sem capability global, não-Formador-puro e sem
   `EquipeGerencia` (Apoio/Gerente/Coord recém-criado) visse TODOS os eventos
   aprovados nacionais. Agora `else: upcoming_qs.none()` zera fail-safe.

2. **#1260** — detecção de papel migrada de strings de grupo (`"DAT" in user_groups`)
   para capabilities (`user_has_any_perm(user, "manage_admin_registries")`).
   Único hardcode remanescente: detecção de Formador puro (papel sem capability;
   data-scope, não autorização — whitelisted no rbac_lint).

Capability mapping aplicado:
- `manage_admin_registries` → DAT (validar/suportar — ator transversal)
- `approve_solicitation`     → Superintendência (decisão cross-org de aprovação)
- `create_solicitation`      → Coordenador / Apoio de Coordenação / Gerente
"""

# pyright: reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportUnknownVariableType=false, reportUnknownArgumentType=false

from __future__ import annotations

from django.db.models import Q
from django.utils import timezone
from rest_framework import status as http_status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema

from apps.core.models import EquipeGerencia, Solicitacao
from apps.core.rbac.constants import FORMADOR_ROLE_GROUPS
from apps.core.rbac.helpers import user_has_any_perm
from apps.core.serializers.openapi_critical_contract import HomeStatsResponseSerializer


class HomeStatsView(APIView):
    """
    GET /api/stats/home/

    Retorna estatísticas personalizadas para a HomePage baseado em capabilities
    do usuário (capability-driven; sem nome de grupo hardcoded).

    Response (shape estável — contrato com frontend):
    {
        "pending_approvals": int | null,  // null se não pode aprovar
        "upcoming_events": int,
        "my_requests": int | null,        // null se não pode criar
    }
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: HomeStatsResponseSerializer},
        tags=["stats"],
        summary="Estatísticas da home por perfil",
    )
    def get(self, request: Request) -> Response:
        user = request.user
        now = timezone.now()

        # Capability-driven role detection. Superuser bypass é embutido em
        # `user_has_any_perm` (retorna True quando is_superuser).
        can_approve = user_has_any_perm(
            user,
            "approve_solicitation",  # Superintendência
            "manage_admin_registries",  # DAT (suporte/validação)
        )
        can_create = user_has_any_perm(
            user,
            "create_solicitation",  # Coordenador / Apoio / Gerente
            "manage_admin_registries",  # DAT (mantém paridade comportamental anterior)
        )

        # "Vê eventos cross-organização" — capabilities transversais.
        can_view_global_events = user_has_any_perm(
            user,
            "manage_admin_registries",  # DAT
            "approve_solicitation",  # Superintendência
        )

        # DAT bypassa o filtro de fluxo SUPER em `pending_approvals` (mantém
        # paridade: Super-only filtra fluxo, DAT/Superuser veem todos).
        can_approve_all_flows = user_has_any_perm(user, "manage_admin_registries")

        # Formador é a única função sem capability própria (acessa /meus-eventos
        # via IsAuthenticated). Aqui é data-scope de queryset, não autorização —
        # whitelisted no rbac_lint guard.
        has_formador_group = user.groups.filter(name__in=FORMADOR_ROLE_GROUPS).exists()  # noqa: RBAC-data-scope-allowed
        is_formador_only = has_formador_group and not user_has_any_perm(
            user,
            "create_solicitation",
            "approve_solicitation",
            "approve_solicitation_batch",
            "manage_admin_registries",
        )

        user_gerencias = list(EquipeGerencia.objects.filter(usuario=user).values_list("gerencia_id", flat=True))

        # === APROVAÇÕES PENDENTES ===
        pending_approvals = None
        if can_approve:
            pending_qs = Solicitacao.objects.filter(status="pendente")
            if not can_approve_all_flows:
                # Super sem bypass DAT: só conta pendentes em projetos SUPER.
                pending_qs = pending_qs.filter(projeto__fluxo="SUPER")
            pending_approvals = pending_qs.count()

        # === EVENTOS FUTUROS (com fail-safe explícito — fix #1284) ===
        upcoming_qs = Solicitacao.objects.filter(status="aprovado", inicio__gte=now)

        if can_view_global_events:
            # Superuser, DAT, Superintendência: cross-org por capability legítima.
            pass
        elif is_formador_only:
            # Formador: ownership (organizador OU participante).
            upcoming_qs = upcoming_qs.filter(Q(usuario=user) | Q(participations__usuario=user)).distinct()
        elif user_gerencias:
            # Coordenador / Apoio / Gerente: eventos da(s) gerência(s) vinculada(s).
            upcoming_qs = upcoming_qs.filter(projeto__gerencia_id__in=user_gerencias)
        else:
            # FAIL-SAFE: user sem capability global, sem Formador puro e sem
            # EquipeGerencia → 0 eventos. Fix #1284 — antes vazava globalmente.
            upcoming_qs = upcoming_qs.none()

        upcoming_events = upcoming_qs.count()

        # === MINHAS SOLICITAÇÕES === (sempre owner-based; filtro de gerência
        # legacy era redundante e podia zerar indevidamente — removido).
        my_requests = None
        if can_create:
            my_requests = Solicitacao.objects.filter(usuario=user).count()

        return Response(
            {
                "pending_approvals": pending_approvals,
                "upcoming_events": upcoming_events,
                "my_requests": my_requests,
            },
            status=http_status.HTTP_200_OK,
        )
