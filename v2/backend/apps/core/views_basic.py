"""
Basic Views (api_root, CurrentUser)
"""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false

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


# Definição dos grupos de SETOR e FUNÇÃO para RBAC
# Setores baseados no mapeamento de gerências (docs/MAPEAMENTO_COMPLETO_SETORES_GERENCIAS.md)
SETOR_GROUPS = [
    # Gerências de projeto
    'Superintendência',  # SUPERINTENDENCIA - Fluxo SUPER
    'Vidas',             # GERENCIA 2 - Fluxo NAO_SUPER
    'Fluir',             # GERENCIA 3 - Fluxo NAO_SUPER
    'ACerta',            # GERENCIA 4 - Fluxo NAO_SUPER
    'Brincando',         # GERENCIA 5 - Fluxo NAO_SUPER
    'Sou da Paz',        # GERENCIA 6 - Fluxo NAO_SUPER
    # Setores administrativos/operacionais
    'DAT',               # Departamento de Apoio Técnico
    'Controle',          # Setor de Controle
    'Gerência',          # Gerência genérica
]
FUNCAO_GROUPS = ['Formador', 'Coordenador', 'Apoio de Coordenação', 'Gerente']


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
            "name": str,
            "groups": list[str],        # Todos os grupos (compatibilidade)
            "setores": list[str],       # Grupos de SETOR (onde trabalha)
            "funcoes": list[str],       # Grupos de FUNÇÃO (o que pode fazer)
            "is_superuser": bool,
            "is_superintendencia": bool,
            "can_approve_super": bool   # Pode aprovar solicitações SUPER
        }
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        user = request.user
        groups: list[str] = list(user.groups.values_list("name", flat=True))

        # Separar grupos em setores e funções
        setores = [g for g in groups if g in SETOR_GROUPS]
        funcoes = [g for g in groups if g in FUNCAO_GROUPS]

        # Superusers sempre têm acesso completo
        is_superintendencia: bool = user.is_superuser or ("Superintendência" in setores)

        # Pode aprovar solicitações SUPER?
        # Regra: Gerente + Superintendência (ou superuser)
        can_approve_super = user.is_superuser or (
            "Gerente" in funcoes and "Superintendência" in setores
        )

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
                "setores": setores,
                "funcoes": funcoes,
                "is_superuser": user.is_superuser,
                "is_superintendencia": is_superintendencia,
                "can_approve_super": can_approve_super,
            },
            status=status.HTTP_200_OK,
        )
