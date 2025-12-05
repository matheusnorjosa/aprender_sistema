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


# Definição dos grupos de SETOR e FUNÇÃO para RBAC
SETOR_GROUPS = ['Superintendência', 'DAT', 'Controle', 'Gerência']
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
        groups = list(user.groups.values_list("name", flat=True))

        # Separar grupos em setores e funções
        setores = [g for g in groups if g in SETOR_GROUPS]
        funcoes = [g for g in groups if g in FUNCAO_GROUPS]

        # Superusers sempre têm acesso completo
        is_superintendencia = user.is_superuser or ("Superintendência" in setores)

        # Pode aprovar solicitações SUPER?
        # Regra: Gerente + Superintendência (ou superuser)
        can_approve_super = user.is_superuser or (
            "Gerente" in funcoes and "Superintendência" in setores
        )

        return Response(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "groups": groups,
                "setores": setores,
                "funcoes": funcoes,
                "is_superuser": user.is_superuser,
                "is_superintendencia": is_superintendencia,
                "can_approve_super": can_approve_super,
            },
            status=status.HTTP_200_OK,
        )
