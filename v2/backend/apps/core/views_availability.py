"""
Availability ViewSets (views ativas)
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false

from __future__ import annotations

from typing import Any

from django.db.models import QuerySet
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema

from .api_schemas import AVAILABILITY_CONFLICT_EXAMPLE, AVAILABILITY_OK_EXAMPLE, COMMON_ERROR_RESPONSES
from .models import AvailabilityBlock, EquipeGerencia, Municipio, Usuario
from .permissions import IsControleOrSuper
from .serializers import AvailabilityBlockSerializer
from .services.availability_service import check_conflicts


def is_privileged_user(user):
    """
    Verifica se o usuário tem permissão para acessar dados de outros usuários.

    Epic 3.2 RBAC Refactor (2026-04-23): hardcoded
    `groups.filter(name__in=["Superintendência", "Controle"])` trocado por
    capability `pode_ver_todas_disponibilidades`. Expansão deliberada para
    Gerência+Diretoria (documentada no PR #1183).
    """
    from apps.core.rbac_helpers import user_has_any_perm

    return user_has_any_perm(user, "pode_ver_todas_disponibilidades")


def get_user_gerencias_ids(user) -> list[int]:
    """Retorna IDs de todas as gerências do usuário (via EquipeGerencia)."""
    return list(EquipeGerencia.objects.filter(usuario=user).values_list("gerencia_id", flat=True))


class AvailabilityBlockViewSet(viewsets.ModelViewSet):
    """
    ViewSet para Bloqueios de Disponibilidade.

    Formadores podem criar bloqueios para si mesmos.
    Usuario é preenchido automaticamente com request.user.
    Status é auto-aprovado (bloqueios são informações factuais).

    Permissões (conforme PLAN_multi_sector_availability.md):
        - Privilegiados (superuser, Superintendência, Controle): veem todos
        - Outros: bloqueios de usuários da mesma gerência
    """

    queryset = AvailabilityBlock.objects.select_related("usuario").all()
    serializer_class = AvailabilityBlockSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self) -> QuerySet:
        user = self.request.user

        # Privilegiados (superuser, Superintendência, Controle) veem todos
        if is_privileged_user(user):
            return AvailabilityBlock.objects.select_related("usuario").all()

        # Segurança (C-03): para update/delete, usuários comuns só veem seus próprios bloqueios
        if self.action in {"update", "partial_update", "destroy"}:
            return AvailabilityBlock.objects.select_related("usuario").filter(usuario=user)

        # Outros: bloqueios de usuários das suas gerências
        gerencias_ids = get_user_gerencias_ids(user)
        if not gerencias_ids:
            # Sem gerência, vê apenas os próprios
            return AvailabilityBlock.objects.select_related("usuario").filter(usuario=user)

        # Usuários na mesma gerência
        usuarios_na_gerencia = EquipeGerencia.objects.filter(gerencia_id__in=gerencias_ids).values_list(
            "usuario_id", flat=True
        )

        return AvailabilityBlock.objects.select_related("usuario").filter(usuario_id__in=usuarios_na_gerencia)

    def perform_create(self, serializer):
        """
        Cria bloqueio e auto-aprova.

        Bloqueios são informações factuais (formador sabe quando está indisponível)
        e não requerem aprovação de terceiros. O status é definido como 'aprovado'
        automaticamente para que o bloqueio seja considerado imediatamente nas
        verificações de conflito (RD-02, RD-03).
        """
        serializer.save(usuario=self.request.user, status="aprovado")


class AvailabilityCheckView(APIView):
    """
    Endpoint de checagem de disponibilidade (RD-01 a RD-08).

    Ferramenta consultiva restrita a perfis Controle/Superintendência.
    Não é usada em tempo real na UX; decisões de disponibilidade são
    feitas manualmente pela Superintendência via Grade Mensal.

    GET /api/availability/check/
    Query params:
        - usuario_id (obrigatório)
        - inicio (obrigatório): ISO8601 datetime
        - fim (obrigatório): ISO8601 datetime
        - municipio_id (opcional)
    """

    permission_classes = [IsControleOrSuper]
    throttle_scope = "availability_check"

    @extend_schema(
        summary="Verificar disponibilidade",
        description="Verifica conflitos de agenda para um formador (RD-01 a RD-08). Retorna se o período está disponível e lista de conflitos.",
        parameters=[
            OpenApiParameter("usuario_id", OpenApiTypes.INT, required=True, description="ID do formador"),
            OpenApiParameter("inicio", OpenApiTypes.DATETIME, required=True, description="Data/hora início (ISO8601)"),
            OpenApiParameter("fim", OpenApiTypes.DATETIME, required=True, description="Data/hora fim (ISO8601)"),
            OpenApiParameter(
                "municipio_id",
                OpenApiTypes.INT,
                required=False,
                description="ID do município (para verificar deslocamento)",
            ),
        ],
        responses={
            200: OpenApiExample(
                "Resposta",
                value={"available": True, "conflicts": []},
            ),
            400: COMMON_ERROR_RESPONSES[400],
            403: COMMON_ERROR_RESPONSES[403],
        },
        examples=[AVAILABILITY_OK_EXAMPLE, AVAILABILITY_CONFLICT_EXAMPLE],
        tags=["availability"],
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        # Validar usuario_id
        usuario_id_raw = request.query_params.get("usuario_id")
        if not usuario_id_raw:
            return Response(
                {"detail": "usuario_id é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            usuario_id = int(usuario_id_raw)
        except (TypeError, ValueError):
            return Response(
                {"detail": "usuario_id inválido."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            usuario = Usuario.objects.get(pk=usuario_id)
        except Usuario.DoesNotExist:
            return Response(
                {"detail": "Usuário não encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Verificar permissão: só pode consultar próprio ou se for privilegiado
        if usuario_id != request.user.id and not is_privileged_user(request.user):
            return Response(
                {"detail": "Você não tem permissão para consultar a disponibilidade de outros usuários."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # municipio_id é opcional
        municipio_id_raw = request.query_params.get("municipio_id")
        municipio = None
        if municipio_id_raw:
            try:
                municipio_id = int(municipio_id_raw)
            except (TypeError, ValueError):
                return Response(
                    {"detail": "municipio_id inválido."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            municipio = Municipio.objects.filter(pk=municipio_id).first()

        # datas
        inicio_raw = request.query_params.get("inicio")
        fim_raw = request.query_params.get("fim")
        if not inicio_raw or not fim_raw:
            return Response(
                {"detail": "inicio e fim são obrigatórios."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        inicio = parse_datetime(inicio_raw)
        fim = parse_datetime(fim_raw)
        if not inicio or not fim:
            return Response(
                {"detail": "Datas inválidas. Use ISO8601."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if fim <= inicio:
            return Response(
                {"detail": "fim deve ser posterior a inicio."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Garantir timezone-aware (RD-06)
        if timezone.is_naive(inicio):
            inicio = timezone.make_aware(inicio, timezone.utc)
        if timezone.is_naive(fim):
            fim = timezone.make_aware(fim, timezone.utc)

        # Executar checagem
        result = check_conflicts(usuario=usuario, inicio=inicio, fim=fim, municipio=municipio)

        return Response(
            {
                "ok": result.ok,
                "conflicts": [c.__dict__ for c in result.conflicts],
            },
            status=status.HTTP_200_OK,
        )


class AvailabilityCheckManyView(APIView):
    """
    Endpoint de checagem de disponibilidade em lote.

    Ferramenta consultiva restrita a perfis Controle/Superintendência.
    Não é usada em tempo real na UX; decisões de disponibilidade são
    feitas manualmente pela Superintendência via Grade Mensal.

    POST /api/availability/check-many/
    Body: {"usuarios_ids": [1, 2], "inicio": "...", "fim": "...", "municipio_id": ...}
    """

    permission_classes = [IsControleOrSuper]
    throttle_scope = "availability_check"

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        usuarios_ids = request.data.get("usuarios_ids", [])
        if not usuarios_ids or not isinstance(usuarios_ids, list):
            return Response(
                {"detail": "usuarios_ids deve ser uma lista não-vazia."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Verificar permissão: filtrar IDs para apenas os permitidos
        privileged = is_privileged_user(request.user)
        if not privileged:
            # Usuário não-privilegiado só pode consultar ele mesmo
            unauthorized_ids = [uid for uid in usuarios_ids if uid != request.user.id]
            if unauthorized_ids:
                return Response(
                    {"detail": "Você não tem permissão para consultar a disponibilidade de outros usuários."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        inicio_raw = request.data.get("inicio")
        fim_raw = request.data.get("fim")
        if not inicio_raw or not fim_raw:
            return Response(
                {"detail": "inicio e fim são obrigatórios."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        inicio = parse_datetime(inicio_raw)
        fim = parse_datetime(fim_raw)
        if not inicio or not fim:
            return Response(
                {"detail": "Datas inválidas. Use ISO8601."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if fim <= inicio:
            return Response(
                {"detail": "fim deve ser posterior a inicio."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if timezone.is_naive(inicio):
            inicio = timezone.make_aware(inicio, timezone.utc)
        if timezone.is_naive(fim):
            fim = timezone.make_aware(fim, timezone.utc)

        municipio_id = request.data.get("municipio_id")
        municipio = None
        if municipio_id:
            try:
                municipio = Municipio.objects.get(pk=municipio_id)
            except Municipio.DoesNotExist:
                return Response(
                    {"detail": f"Município {municipio_id} não encontrado."},
                    status=status.HTTP_404_NOT_FOUND,
                )

        results = []
        all_ok = True

        for usuario_id in usuarios_ids:
            try:
                usuario = Usuario.objects.get(pk=usuario_id)
            except Usuario.DoesNotExist:
                results.append(
                    {
                        "usuario_id": usuario_id,
                        "ok": False,
                        "conflicts": [
                            {
                                "code": "X",
                                "title": "Usuário não encontrado",
                                "detail": f"Usuário {usuario_id} não existe.",
                                "ref_id": None,
                            }
                        ],
                    }
                )
                all_ok = False
                continue

            result = check_conflicts(usuario=usuario, inicio=inicio, fim=fim, municipio=municipio)

            results.append(
                {
                    "usuario_id": usuario_id,
                    "ok": result.ok,
                    "conflicts": [c.__dict__ for c in result.conflicts],
                }
            )

            if not result.ok:
                all_ok = False

        return Response(
            {
                "ok": all_ok,
                "results": results,
            },
            status=status.HTTP_200_OK,
        )
