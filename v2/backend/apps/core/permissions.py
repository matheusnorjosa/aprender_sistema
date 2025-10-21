"""
DRF Permissions for RBAC

PA-02: Apenas Superintendência pode aprovar/reprovar solicitações.
"""

from rest_framework import permissions


class IsSuperintendencia(permissions.BasePermission):
    """
    Permissão: apenas usuários do grupo 'Superintendência' ou superusers podem executar.
    PA-02: Aprovação/reprovação restrita à Superintendência.

    Nota: Superusers sempre têm acesso completo.
    """

    message = "Apenas usuários da Superintendência podem realizar esta ação."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and (
                request.user.is_superuser
                or request.user.groups.filter(name="Superintendência").exists()
            )
        )


class IsCoordenadorOrDAT(permissions.BasePermission):
    """
    Permissão: apenas Coordenadores ou DAT podem criar solicitações.

    Nota: Superusers sempre têm acesso completo.
    """

    message = "Apenas Coordenadores ou DAT podem criar solicitações."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and (
                request.user.is_superuser
                or request.user.groups.filter(name__in=["Coordenador", "DAT"]).exists()
            )
        )


class IsControleOrSuper(permissions.BasePermission):
    """
    Permissão: apenas usuários do grupo 'Controle' ou 'Superintendência' podem executar.

    Usado para operações de importação e controle de dados.
    Nota: Superusers sempre têm acesso completo.
    """

    message = "Apenas Controle ou Superintendência podem realizar esta ação."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and (
                request.user.is_superuser
                or request.user.groups.filter(name__in=["Controle", "Superintendência"]).exists()
            )
        )


class IsDATOrSuper(permissions.BasePermission):
    """
    Permissão: apenas usuários do grupo 'DAT' ou superusers podem executar.

    Usado para operações de cadastro e gerenciamento de dados do DAT.
    Nota: Superusers sempre têm acesso completo.
    """

    message = "Apenas usuários do grupo DAT ou superusers podem realizar esta ação."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and (
                request.user.is_superuser
                or request.user.groups.filter(name="DAT").exists()
            )
        )
