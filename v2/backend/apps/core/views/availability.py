"""
AS v2 — Availability Views

ViewSets and APIViews for availability blocks and conflict checking.
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

from apps.core.models import AvailabilityBlock, Municipio, Usuario
from apps.core.serializers import AvailabilityBlockSerializer
from apps.core.services.availability_service import check_conflicts


class AvailabilityBlockViewSet(viewsets.ModelViewSet):
    """
    ViewSet para Bloqueios de Disponibilidade.

    Formadores podem criar bloqueios para si mesmos.
    Usuario é preenchido automaticamente com request.user.

    Security (Issue #560 C-03):
    - Users can only update/delete their own blocks
    - Controle, Superintendência, and superusers can manage any block
    """

    queryset = AvailabilityBlock.objects.select_related("usuario").all()
    serializer_class = AvailabilityBlockSerializer
    permission_classes = [IsAuthenticated]

    def _is_privileged_user(self) -> bool:
        """
        Check if current user has privileged access (can manage any block).

        Security (C-03): Define who can edit/delete blocks of other users.

        Epic 3.2 RBAC Refactor (2026-04-23): substitui hardcoded
        `groups.filter(name__in=["Superintendência", "Controle"])` por
        capability-based check. O codename `pode_ver_todas_disponibilidades`
        é concedido aos mesmos 4 grupos (Super, Controle, Gerência,
        Diretoria) via seed; expansão deliberada para Gerência+Diretoria
        documentada no PR #1183.
        """
        from apps.core.rbac_helpers import user_has_any_perm

        return user_has_any_perm(self.request.user, "view_all_availability")

    def get_queryset(self) -> QuerySet:
        """
        Filtrar bloqueios por usuário (exceto Superintendência/Controle/superuser que vê todos).
        """
        base_qs = AvailabilityBlock.objects.select_related("usuario")
        owner = self.request.query_params.get("owner")
        if owner == "me":
            return base_qs.filter(usuario=self.request.user)
        if self._is_privileged_user():
            return base_qs.all()
        return base_qs.filter(usuario=self.request.user)

    def perform_create(self, serializer):
        """
        Preenche usuario automaticamente com request.user ao criar bloqueio.
        """
        serializer.save(usuario=self.request.user)

    def update(self, request, *args, **kwargs):
        """
        Security (C-03): Only allow update if user owns the block or is privileged.
        """
        instance = self.get_object()
        if not self._is_privileged_user() and instance.usuario_id != request.user.id:
            return Response(
                {"detail": "Você não tem permissão para editar este bloqueio."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        """
        Security (C-03): Only allow partial update if user owns the block or is privileged.
        """
        instance = self.get_object()
        if not self._is_privileged_user() and instance.usuario_id != request.user.id:
            return Response(
                {"detail": "Você não tem permissão para editar este bloqueio."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """
        Security (C-03): Only allow delete if user owns the block or is privileged.
        """
        instance = self.get_object()
        if not self._is_privileged_user() and instance.usuario_id != request.user.id:
            return Response(
                {"detail": "Você não tem permissão para excluir este bloqueio."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().destroy(request, *args, **kwargs)


class AvailabilityCheckView(APIView):
    """
    Endpoint de checagem de disponibilidade (RD-01 a RD-08).

    GET /api/availability/check/
    Query params:
        - usuario_id (obrigatório): ID do usuário
        - inicio (obrigatório): ISO8601 datetime
        - fim (obrigatório): ISO8601 datetime
        - municipio_id (opcional): ID do município

    Retorna:
        {
            "ok": bool,
            "conflicts": [
                {"code": "X"|"T"|"P"|"D"|"M", "title": str, "detail": str, "ref_id": int|null}
            ]
        }

    Nota: Checagem consultiva. NÃO altera estado, NÃO aprova nada.

    Rate Limit: 60 requisições por minuto (ScopedRateThrottle)
    """

    permission_classes = [IsAuthenticated]
    throttle_scope = "availability_check"

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        # Extrair e validar usuario_id
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

        # Retornar resultado
        return Response(
            {
                "ok": result.ok,
                "conflicts": [c.__dict__ for c in result.conflicts],
            },
            status=status.HTTP_200_OK,
        )


class AvailabilityCheckManyView(APIView):
    """
    Endpoint de checagem de disponibilidade em lote (PR 8/N).

    POST /api/availability/check-many/
    Body:
        {
            "usuarios_ids": [1, 2, 3],
            "inicio": "2025-10-15T08:00:00Z",
            "fim": "2025-10-15T12:00:00Z",
            "municipio_id": 1
        }

    Retorna:
        {
            "ok": bool,  # true se TODOS usuários estão disponíveis
            "results": [
                {
                    "usuario_id": int,
                    "ok": bool,
                    "conflicts": [
                        {"code": "X"|"T"|"P"|"D"|"M", "title": str, "detail": str, "ref_id": int|null}
                    ]
                }
            ]
        }

    Nota: Checagem consultiva. NÃO altera estado, NÃO aprova nada.
    """

    permission_classes = [IsAuthenticated]
    throttle_scope = "availability_check"

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        # Validar payload
        usuarios_ids = request.data.get("usuarios_ids", [])
        if not usuarios_ids or not isinstance(usuarios_ids, list):
            return Response(
                {"detail": "usuarios_ids deve ser uma lista não-vazia."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validar datas
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

        # Garantir timezone-aware (RD-06)
        if timezone.is_naive(inicio):
            inicio = timezone.make_aware(inicio, timezone.utc)
        if timezone.is_naive(fim):
            fim = timezone.make_aware(fim, timezone.utc)

        # Validar municipio_id (opcional)
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

        # Batch fetch de usuários (evita N+1)
        usuarios_map = {u.id: u for u in Usuario.objects.filter(pk__in=usuarios_ids)}

        # Executar checagem para cada usuário
        results = []
        all_ok = True

        for usuario_id in usuarios_ids:
            usuario = usuarios_map.get(usuario_id)
            if not usuario:
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

            # Executar checagem
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

        # Retornar resultado agregado
        return Response(
            {
                "ok": all_ok,
                "results": results,
            },
            status=status.HTTP_200_OK,
        )
