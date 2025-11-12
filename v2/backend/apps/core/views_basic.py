"""
Basic Views (api_root, CurrentUser)
"""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false

from __future__ import annotations

from typing import Any

from django.http import HttpRequest, JsonResponse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


def api_root(request: HttpRequest) -> JsonResponse:
    """API root endpoint"""
    return JsonResponse(
        {
            "message": "AS v2 API",
            "version": "2.0.0",
            "endpoints": {
                "admin": "/admin/",
                "healthz": "/healthz/",
                "api": "/api/",
            },
        }
    )


class CurrentUserView(APIView):
    """
    Endpoint que retorna informações do usuário autenticado.

    GET /api/me/
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        user = request.user
        groups: list[str] = list(user.groups.values_list("name", flat=True))
        is_superintendencia: bool = user.is_superuser or ("Superintendência" in groups)

        # Compute display name
        name: str = f"{user.first_name or ''} {user.last_name or ''}".strip()
        if not name:
            name = user.email or f"#{user.id}"

        return Response(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "name": name,
                "groups": groups,
                "is_superuser": user.is_superuser,
                "is_superintendencia": is_superintendencia,
            },
            status=status.HTTP_200_OK,
        )
