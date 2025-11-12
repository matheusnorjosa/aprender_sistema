"""
DRF Permissions for RBAC

PA-02: Apenas Superintendência pode aprovar/reprovar solicitações.
"""

from __future__ import annotations

from rest_framework import permissions  # type: ignore[attr-defined]
from rest_framework.request import Request
from rest_framework.views import APIView


class IsSuperintendencia(permissions.BasePermission):  # type: ignore[misc]
    """
    Permissão: apenas usuários do grupo 'Superintendência' ou superusers podem executar.
    PA-02: Aprovação/reprovação restrita à Superintendência.

    Nota: Superusers sempre têm acesso completo.
    """

    message = "Apenas usuários da Superintendência podem realizar esta ação."

    def has_permission(self, request: Request, view: APIView) -> bool:
        return (
            request.user
            and request.user.is_authenticated
            and (
                getattr(request.user, 'is_superuser', False)
                or request.user.groups.filter(name="Superintendência").exists()  # type: ignore[attr-defined]
            )
        )


class IsCoordenadorOrDAT(permissions.BasePermission):  # type: ignore[misc]
    """
    Permissão: apenas Coordenadores ou DAT podem criar solicitações.

    Nota: Superusers sempre têm acesso completo.
    """

    message = "Apenas Coordenadores ou DAT podem criar solicitações."

    def has_permission(self, request: Request, view: APIView) -> bool:
        return (
            request.user
            and request.user.is_authenticated
            and (
                getattr(request.user, 'is_superuser', False)
                or request.user.groups.filter(name__in=["Coordenador", "DAT"]).exists()  # type: ignore[attr-defined]
            )
        )


class IsControleOrSuper(permissions.BasePermission):  # type: ignore[misc]
    """
    Permissão: apenas usuários do grupo 'Controle' ou 'Superintendência' podem executar.

    Usado para operações de importação e controle de dados.
    Nota: Superusers sempre têm acesso completo.
    """

    message = "Apenas Controle ou Superintendência podem realizar esta ação."

    def has_permission(self, request: Request, view: APIView) -> bool:
        return (
            request.user
            and request.user.is_authenticated
            and (
                getattr(request.user, 'is_superuser', False)
                or request.user.groups.filter(name__in=["Controle", "Superintendência"]).exists()  # type: ignore[attr-defined]
            )
        )


class IsDATOrSuper(permissions.BasePermission):  # type: ignore[misc]
    """
    Permissão: apenas usuários do grupo 'DAT' ou superusers podem executar.

    Usado para operações de cadastro e gerenciamento de dados do DAT.
    Nota: Superusers sempre têm acesso completo.
    """

    message = "Apenas usuários do grupo DAT ou superusers podem realizar esta ação."

    def has_permission(self, request: Request, view: APIView) -> bool:
        return (
            request.user
            and request.user.is_authenticated
            and (
                getattr(request.user, 'is_superuser', False)
                or request.user.groups.filter(name="DAT").exists()  # type: ignore[attr-defined]
            )
        )


class IsDAT(permissions.BasePermission):  # type: ignore[misc]
    """
    Permissão: apenas usuários do grupo 'DAT' (sem incluir Super).

    Usado para operações específicas do DAT.
    Nota: Superusers sempre têm acesso completo.
    """

    message = "Apenas usuários do grupo DAT podem realizar esta ação."

    def has_permission(self, request: Request, view: APIView) -> bool:
        return (
            request.user
            and request.user.is_authenticated
            and (
                getattr(request.user, 'is_superuser', False)
                or request.user.groups.filter(name="DAT").exists()  # type: ignore[attr-defined]
            )
        )


class IsControleOrDAT(permissions.BasePermission):  # type: ignore[misc]
    """
    Permissão: apenas usuários dos grupos 'Controle' ou 'DAT' podem executar.

    Usado para operações de visualização e relatórios compartilhados.
    Nota: Superusers sempre têm acesso completo.
    """

    message = "Apenas Controle ou DAT podem realizar esta ação."

    def has_permission(self, request: Request, view: APIView) -> bool:
        return (
            request.user
            and request.user.is_authenticated
            and (
                getattr(request.user, 'is_superuser', False)
                or request.user.groups.filter(name__in=["Controle", "DAT", "Superintendência"]).exists()  # type: ignore[attr-defined]
            )
        )
