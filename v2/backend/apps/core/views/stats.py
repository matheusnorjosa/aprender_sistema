"""
Stats API — Estatísticas para HomePage.

GET /api/stats/home/ retorna métricas personalizadas por perfil:
- pending_approvals: Só para quem pode aprovar (PA-02)
- upcoming_events: Formador=seus eventos, Coord=setor
- my_requests: Só para quem pode criar solicitações, filtrado por setor
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
from apps.core.serializers.openapi_critical_contract import HomeStatsResponseSerializer


class HomeStatsView(APIView):
    """
    GET /api/stats/home/

    Retorna estatísticas personalizadas para a HomePage baseado no perfil do usuário.

    Response:
    {
        "pending_approvals": int | null,  // null se não tem permissão
        "upcoming_events": int,
        "my_requests": int | null,        // null se não tem permissão
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

        # Identificar perfil do usuário
        user_groups = set(user.groups.values_list("name", flat=True))

        is_superuser = user.is_superuser
        is_superintendencia = "Superintendência" in user_groups
        is_dat = "DAT" in user_groups
        is_coordenador = "Coordenador" in user_groups
        is_apoio = "Apoio de Coordenação" in user_groups
        is_formador = "Formador" in user_groups

        # Pode aprovar? (PA-02: Superintendência, DAT ou superuser)
        can_approve = is_superuser or is_dat or is_superintendencia

        # Pode criar solicitações? (Coordenador, Apoio de Coordenação, DAT)
        can_create = is_superuser or is_dat or is_coordenador or is_apoio

        # Obter setores do usuário via EquipeGerencia
        user_gerencias = list(EquipeGerencia.objects.filter(usuario=user).values_list("gerencia_id", flat=True))

        # === APROVAÇÕES PENDENTES ===
        pending_approvals = None
        if can_approve:
            pending_qs = Solicitacao.objects.filter(status="pendente")

            # Se não for superuser/DAT, filtrar por fluxo que pode aprovar
            if not is_superuser and not is_dat:
                # Superintendência/Gerente só aprova SUPER
                pending_qs = pending_qs.filter(projeto__fluxo="SUPER")

            pending_approvals = pending_qs.count()

        # === EVENTOS FUTUROS ===
        upcoming_qs = Solicitacao.objects.filter(
            status="aprovado",
            inicio__gte=now,
        )

        if is_formador and not (is_coordenador or is_apoio or is_dat or is_superuser):
            # Formador: apenas eventos onde é participante ou é o usuário principal
            upcoming_qs = upcoming_qs.filter(Q(usuario=user) | Q(participations__usuario=user)).distinct()
        elif user_gerencias and not is_superuser:
            # Coordenador/Apoio: eventos do seu setor
            upcoming_qs = upcoming_qs.filter(projeto__gerencia_id__in=user_gerencias)
        # Superuser/DAT: vê todos

        upcoming_events = upcoming_qs.count()

        # === MINHAS SOLICITAÇÕES ===
        my_requests = None
        if can_create:
            my_qs = Solicitacao.objects.filter(usuario=user)

            # Filtrar por setor se não for superuser
            if user_gerencias and not is_superuser:
                my_qs = my_qs.filter(projeto__gerencia_id__in=user_gerencias)

            my_requests = my_qs.count()

        return Response(
            {
                "pending_approvals": pending_approvals,
                "upcoming_events": upcoming_events,
                "my_requests": my_requests,
            },
            status=http_status.HTTP_200_OK,
        )
