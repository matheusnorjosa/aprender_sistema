"""
AS v2 — User Views

Current user information endpoint.
"""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false

from __future__ import annotations

from typing import Any

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


class CurrentUserView(APIView):
    """
    Endpoint que retorna informações do usuário autenticado.

    GET /api/me/
    Retorna:
        {
            "id": int,
            "username": str,
            "email": str,
            "first_name": str,
            "last_name": str,
            "groups": list[str],
            "is_superintendencia": bool
        }
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        user = request.user
        groups = list(user.groups.values_list("name", flat=True))
        # Superusers sempre têm acesso completo
        is_superintendencia = user.is_superuser or ("Superintendência" in groups)

        return Response(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "groups": groups,
                "is_superuser": user.is_superuser,
                "is_superintendencia": is_superintendencia,
            },
            status=status.HTTP_200_OK,
        )
