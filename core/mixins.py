# core/mixins.py
"""
Security mixins using Django Groups and Permissions
Replaces papel-based authorization with Django's built-in system
"""

from django.contrib.auth.mixins import PermissionRequiredMixin, UserPassesTestMixin


class GroupRequiredMixin(UserPassesTestMixin):
    """
    Base mixin for group-based access control
    Replaces papel-based mixins with Django Groups
    """

    required_groups = []  # List of group names that can access

    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False

        # Superuser always has access
        if user.is_superuser:
            return True

        # Check if user is in any of the required groups
        user_groups = user.groups.values_list("name", flat=True)
        return any(group in user_groups for group in self.required_groups)


# === Role-based mixins using Groups ===


class IsCoordenadorMixin(GroupRequiredMixin):
    """Access for Coordenador role"""

    required_groups = ["coordenador"]


class IsSuperintendenciaMixin(GroupRequiredMixin):
    """Access for Superintendência role"""

    required_groups = ["superintendencia"]


class IsFormadorMixin(GroupRequiredMixin):
    """Access for Formador role"""

    required_groups = ["formador"]


class IsControleMixin(GroupRequiredMixin):
    """Access for Controle role"""

    required_groups = ["controle"]


class IsDiretoriaMixin(GroupRequiredMixin):
    """Access for Diretoria role"""

    required_groups = ["diretoria"]


class IsAdminMixin(GroupRequiredMixin):
    """Access for Admin role"""

    required_groups = ["admin"]


# === Multi-role mixins ===


class IsFormadorOrAdminMixin(GroupRequiredMixin):
    """Access for Formador and Admin roles"""

    required_groups = ["formador", "admin"]


class CanViewCalendarMixin(GroupRequiredMixin):
    """Access for roles that can view calendar: superintendencia, diretoria, controle, admin"""

    required_groups = ["superintendencia", "diretoria", "controle", "admin"]


class CanApproveEventsMixin(GroupRequiredMixin):
    """Access for roles that can approve events: superintendencia, admin"""

    required_groups = ["superintendencia", "admin"]


class CanCreateEventsMixin(GroupRequiredMixin):
    """Access for roles that can create events: coordenador, superintendencia, admin"""

    required_groups = ["coordenador", "superintendencia", "admin"]


class CanViewReportsMixin(GroupRequiredMixin):
    """Access for roles that can view reports: superintendencia, diretoria, controle, admin"""

    required_groups = ["superintendencia", "diretoria", "controle", "admin"]


# === Permission-based mixins (recommended approach) ===


class CanCreateSolicitacaoMixin(PermissionRequiredMixin):
    """Permission-based access for creating solicitações"""

    permission_required = "core.add_solicitacao"


class CanViewSolicitacaoMixin(PermissionRequiredMixin):
    """Permission-based access for viewing solicitações"""

    permission_required = "core.view_solicitacao"


class CanApproveSolicitacaoMixin(PermissionRequiredMixin):
    """Permission-based access for approving solicitações"""

    permission_required = "core.add_aprovacao"


class CanViewCalendarPermissionMixin(PermissionRequiredMixin):
    """Permission-based access for calendar view"""

    permission_required = "core.view_calendar"


class CanSyncCalendarMixin(PermissionRequiredMixin):
    """Permission-based access for calendar sync"""

    permission_required = "core.sync_calendar"


class CanViewReportsPermissionMixin(PermissionRequiredMixin):
    """Permission-based access for reports"""

    permission_required = "core.view_relatorios"


class CanViewAuditLogsMixin(PermissionRequiredMixin):
    """Permission-based access for audit logs"""

    permission_required = "core.view_logauditoria"


# === Backward compatibility mixins ===


class BackwardCompatibleCoordenadorMixin(UserPassesTestMixin):
    """
    Backward compatible mixin that checks both papel field and groups
    Used during transition period
    """

    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        # Check new group-based permission
        if user.groups.filter(name="coordenador").exists():
            return True

        # Fallback to old papel field for backward compatibility
        return getattr(user, "papel", "") == "coordenador"


class BackwardCompatibleSuperintendenciaMixin(UserPassesTestMixin):
    """
    Backward compatible mixin for superintendencia role
    """

    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        # Check new group-based permission
        if user.groups.filter(name="superintendencia").exists():
            return True

        # Fallback to old papel field
        return getattr(user, "papel", "") == "superintendencia"


class BackwardCompatibleFormadorMixin(UserPassesTestMixin):
    """
    Backward compatible mixin for formador role
    """

    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        # Check new group-based permission
        if user.groups.filter(name="formador").exists():
            return True

        # Fallback to old papel field
        return getattr(user, "papel", "") == "formador"


# === Setor-based mixins ===


class SuperintendenciaSetorRequiredMixin(UserPassesTestMixin):
    """
    Mixin para restringir acesso apenas a usuários cujo setor é vinculado à superintendência
    Usado para mapa de disponibilidade, aprovações pendentes, pré-agenda, deslocamentos
    """

    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False

        # Superuser sempre tem acesso
        if user.is_superuser:
            return True

        # Verificar se o usuário tem setor vinculado à superintendência
        return (
            hasattr(user, 'setor') 
            and user.setor 
            and getattr(user.setor, 'vinculado_superintendencia', False)
        )


class FormadorOwnerMixin(UserPassesTestMixin):
    """
    Mixin para restringir acesso a formadores apenas aos seus próprios dados
    Usado para bloqueios de agenda própria
    """

    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False

        # Superuser sempre tem acesso
        if user.is_superuser:
            return True

        # Superintendência tem acesso a tudo
        if (
            hasattr(user, 'setor') 
            and user.setor 
            and getattr(user.setor, 'vinculado_superintendencia', False)
        ):
            return True

        # Formador só pode acessar seus próprios dados
        if user.groups.filter(name="formador").exists():
            # Verificar se o objeto sendo acessado pertence ao formador
            # Será implementado nas views específicas
            return True

        return False


# === Utility functions ===


def user_has_role(user, role_name):
    """
    Utility function to check if user has a specific role

    Args:
        user: Django User instance
        role_name: String name of the role/group

    Returns:
        bool: True if user has the role
    """
    if not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    return user.groups.filter(name=role_name).exists()


def user_has_any_role(user, role_names):
    """
    Utility function to check if user has any of the specified roles

    Args:
        user: Django User instance
        role_names: List of role/group names

    Returns:
        bool: True if user has any of the roles
    """
    if not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    user_groups = user.groups.values_list("name", flat=True)
    return any(role in user_groups for role in role_names)


def get_user_roles(user):
    """
    Get all roles/groups for a user

    Args:
        user: Django User instance

    Returns:
        QuerySet: User's groups
    """
    if not user.is_authenticated:
        return []

    return user.groups.all()


def get_user_role_names(user):
    """
    Get all role names for a user

    Args:
        user: Django User instance

    Returns:
        list: List of group names
    """
    if not user.is_authenticated:
        return []

    return list(user.groups.values_list("name", flat=True))
