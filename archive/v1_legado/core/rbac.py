"""
RBAC (Role-Based Access Control) Module
========================================

Defines canonical groups, permission classes, and helper utilities
for Django 5.2 + Django REST Framework.

Groups:
- coordenador: Can create requests
- formador: Can view own events and block availability
- controle: Can manage pre-agenda queue
- gerente_super: Can approve/reject requests (Superintendência only)
- dat: Can ingest data and view QA
- admin_ops: Full administrative access

Permissions Mapping:
- pode_ver_preagenda → controle, gerente_super, admin_ops
- pode_exportar_preagenda → controle, admin_ops
- pode_aprovar_super → gerente_super, admin_ops
- pode_ver_qa → controle, dat, admin_ops
- pode_ingest → dat, admin_ops
"""

from functools import wraps

from django.contrib.auth.models import Group
from django.http import HttpResponseForbidden

from rest_framework.permissions import BasePermission

# ========================================
# GROUP CONSTANTS
# ========================================

COORDENADOR = "coordenador"
FORMADOR = "formador"
CONTROLE = "controle"
GERENTE_SUPER = "gerente_super"
DAT = "dat"
ADMIN_OPS = "admin_ops"

ALL_GROUPS = [COORDENADOR, FORMADOR, CONTROLE, GERENTE_SUPER, DAT, ADMIN_OPS]


# ========================================
# HELPER FUNCTIONS
# ========================================


def user_in_groups(user, *group_names):
    """
    Check if user belongs to any of the specified groups.

    Args:
        user: Django User instance
        *group_names: Variable number of group names to check

    Returns:
        bool: True if user is in any of the groups, False otherwise

    Example:
        >>> user_in_groups(request.user, CONTROLE, ADMIN_OPS)
        True
    """
    if not user or not user.is_authenticated:
        return False

    # Superusers bypass group checks
    if user.is_superuser:
        return True

    # Check if user belongs to any of the specified groups
    return user.groups.filter(name__in=group_names).exists()


# ========================================
# DRF PERMISSION CLASSES
# ========================================


class IsCoordenador(BasePermission):
    """
    Permission class for Coordenador role.
    Allows: Creating event requests.
    """

    message = "Você precisa ser Coordenador para acessar este recurso."

    def has_permission(self, request, view):
        return user_in_groups(request.user, COORDENADOR)


class IsFormador(BasePermission):
    """
    Permission class for Formador role.
    Allows: Viewing own events, blocking availability.
    """

    message = "Você precisa ser Formador para acessar este recurso."

    def has_permission(self, request, view):
        return user_in_groups(request.user, FORMADOR)


class IsControle(BasePermission):
    """
    Permission class for Controle role.
    Allows: Managing pre-agenda queue, viewing QA.
    """

    message = "Você precisa ser do Controle para acessar este recurso."

    def has_permission(self, request, view):
        return user_in_groups(request.user, CONTROLE)


class IsGerenteSuper(BasePermission):
    """
    Permission class for Gerente Superintendência role.
    Allows: Approving/rejecting requests, viewing pre-agenda.
    """

    message = "Você precisa ser Gerente da Superintendência para acessar este recurso."

    def has_permission(self, request, view):
        return user_in_groups(request.user, GERENTE_SUPER)


class IsDat(BasePermission):
    """
    Permission class for DAT (Data Analytics Team) role.
    Allows: Ingesting data, viewing QA dashboards.
    """

    message = "Você precisa ser do time DAT para acessar este recurso."

    def has_permission(self, request, view):
        return user_in_groups(request.user, DAT)


class IsAdminOps(BasePermission):
    """
    Permission class for Admin Operations role.
    Full administrative access to all system operations.
    """

    message = "Você precisa ser Admin Ops para acessar este recurso."

    def has_permission(self, request, view):
        return user_in_groups(request.user, ADMIN_OPS)


# ========================================
# COMBINER PERMISSION CLASSES
# ========================================


class IsControleOrGerenteSuper(BasePermission):
    """
    Allows access for Controle OR Gerente Superintendência.
    Use case: Pre-agenda management.
    """

    message = "Você precisa ser do Controle ou Gerente Super para acessar este recurso."

    def has_permission(self, request, view):
        return user_in_groups(request.user, CONTROLE, GERENTE_SUPER)


class IsControleOrAdminOps(BasePermission):
    """
    Allows access for Controle OR Admin Ops.
    Use case: Exporting pre-agenda data.
    """

    message = "Você precisa ser do Controle ou Admin Ops para acessar este recurso."

    def has_permission(self, request, view):
        return user_in_groups(request.user, CONTROLE, ADMIN_OPS)


class IsDatOrControleOrAdminOps(BasePermission):
    """
    Allows access for DAT OR Controle OR Admin Ops.
    Use case: Viewing QA dashboards and health checks.
    """

    message = (
        "Você precisa ser do DAT, Controle ou Admin Ops para acessar este recurso."
    )

    def has_permission(self, request, view):
        return user_in_groups(request.user, DAT, CONTROLE, ADMIN_OPS)


class IsDatOrAdminOps(BasePermission):
    """
    Allows access for DAT OR Admin Ops.
    Use case: Data ingestion endpoints.
    """

    message = "Você precisa ser do DAT ou Admin Ops para acessar este recurso."

    def has_permission(self, request, view):
        return user_in_groups(request.user, DAT, ADMIN_OPS)


class IsGerenteOrAdminOps(BasePermission):
    """
    Allows access for Gerente Super OR Admin Ops.
    Use case: Approval workflows.
    """

    message = "Você precisa ser Gerente Super ou Admin Ops para acessar este recurso."

    def has_permission(self, request, view):
        return user_in_groups(request.user, GERENTE_SUPER, ADMIN_OPS)


# ========================================
# DJANGO VIEW DECORATOR
# ========================================


def require_groups(*group_names):
    """
    Decorator for Django function-based views to require specific groups.

    Args:
        *group_names: Variable number of group names required

    Returns:
        Decorated view function that checks group membership

    Example:
        @require_groups(CONTROLE, ADMIN_OPS)
        def controle_dashboard(request):
            return render(request, 'dashboard.html')
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return HttpResponseForbidden(
                    "Você precisa estar autenticado para acessar este recurso."
                )

            if not user_in_groups(request.user, *group_names):
                groups_display = ", ".join(group_names)
                return HttpResponseForbidden(
                    f"Você precisa pertencer a um dos grupos: {groups_display}"
                )

            return view_func(request, *args, **kwargs)

        return wrapped_view

    return decorator


# ========================================
# PERMISSION UTILITIES
# ========================================


def get_user_groups(user):
    """
    Get list of group names for a user.

    Args:
        user: Django User instance

    Returns:
        list: List of group name strings

    Example:
        >>> get_user_groups(request.user)
        ['controle', 'dat']
    """
    if not user or not user.is_authenticated:
        return []

    return list(user.groups.values_list("name", flat=True))


def ensure_group_exists(group_name):
    """
    Ensure a group exists in the database.

    Args:
        group_name: Name of the group to create

    Returns:
        Group: The group instance (created or existing)

    Example:
        >>> ensure_group_exists(CONTROLE)
        <Group: controle>
    """
    group, created = Group.objects.get_or_create(name=group_name)
    return group


def assign_user_to_group(user, group_name):
    """
    Assign a user to a group (idempotent).

    Args:
        user: Django User instance
        group_name: Name of the group

    Returns:
        bool: True if added, False if already in group

    Example:
        >>> assign_user_to_group(user, CONTROLE)
        True
    """
    group = ensure_group_exists(group_name)
    if not user.groups.filter(pk=group.pk).exists():
        user.groups.add(group)
        return True
    return False


def remove_user_from_group(user, group_name):
    """
    Remove a user from a group (idempotent).

    Args:
        user: Django User instance
        group_name: Name of the group

    Returns:
        bool: True if removed, False if not in group

    Example:
        >>> remove_user_from_group(user, FORMADOR)
        True
    """
    try:
        group = Group.objects.get(name=group_name)
        if user.groups.filter(pk=group.pk).exists():
            user.groups.remove(group)
            return True
    except Group.DoesNotExist:
        pass
    return False
