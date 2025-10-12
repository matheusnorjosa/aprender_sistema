"""
DRF Permissions for RBAC

PA-02: Apenas Superintendência pode aprovar/reprovar solicitações.
"""

from rest_framework import permissions


class IsSuperintendencia(permissions.BasePermission):
    """
    Permissão: apenas usuários do grupo 'Superintendência' podem executar.
    PA-02: Aprovação/reprovação restrita à Superintendência.
    """

    message = "Apenas usuários da Superintendência podem realizar esta ação."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.groups.filter(name="Superintendência").exists()
        )
