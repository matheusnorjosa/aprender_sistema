"""
DRF permissions para RBAC funcional (database-driven).

Backwards compatible:
- nomes das classes publicas preservados;
- imports existentes continuam funcionando.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

from typing import cast

from rest_framework import permissions  # type: ignore[attr-defined]
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.core.services.rbac_permissions import get_user_functional_permissions


class HasFunctionalPermission(permissions.BasePermission):  # type: ignore[misc]
    """
    Base class para checagem por codename funcional.
    """

    functional_codename = ""
    message = "Você não tem permissão para realizar esta ação."

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if getattr(user, "is_superuser", False):
            return True
        if not self.functional_codename:
            return False
        return self.functional_codename in get_user_functional_permissions(user)


def funcperm_factory(
    class_name: str,
    functional_codename: str,
    message: str,
) -> type[HasFunctionalPermission]:
    attrs = {
        "functional_codename": functional_codename,
        "message": message,
    }
    return cast(type[HasFunctionalPermission], type(class_name, (HasFunctionalPermission,), attrs))


class IsSuperintendencia(
    funcperm_factory(
        "IsSuperintendencia",
        "pode_aprovar_superintendencia",
        "Apenas usuários da Superintendência, DAT ou Superusuários podem realizar esta ação.",
    )
):
    pass


class IsSuperintendenciaOnly(
    funcperm_factory(
        "IsSuperintendenciaOnly",
        "pode_gerenciar_superintendencia_only",
        "Apenas usuários da Superintendência podem realizar esta ação.",
    )
):
    pass


class IsCoordenadorOrDAT(
    funcperm_factory(
        "IsCoordenadorOrDAT",
        "pode_criar_solicitacao_coord_dat",
        "Apenas Coordenadores, Apoio de Coordenação ou DAT podem criar solicitações.",
    )
):
    pass


class IsControleOrSuper(
    funcperm_factory(
        "IsControleOrSuper",
        "pode_importar_controle_super",
        "Apenas Controle ou Superintendência podem realizar esta ação.",
    )
):
    pass


class IsDATOrSuper(
    funcperm_factory(
        "IsDATOrSuper",
        "pode_operar_dat",
        "Apenas usuários do grupo DAT ou superusers podem realizar esta ação.",
    )
):
    pass


class IsComprasDashboardAccess(
    funcperm_factory(
        "IsComprasDashboardAccess",
        "pode_acessar_dashboard_compras",
        "Apenas usuários dos grupos DAT ou Diretoria podem acessar o dashboard de compras.",
    )
):
    pass


class IsDAT(
    funcperm_factory(
        "IsDAT",
        "pode_operar_dat_exclusivo",
        "Apenas usuários do grupo DAT podem realizar esta ação.",
    )
):
    pass


class IsControleOrDAT(
    funcperm_factory(
        "IsControleOrDAT",
        "pode_operar_controle_dat",
        "Apenas Controle ou DAT podem realizar esta ação.",
    )
):
    pass


class IsControle(
    funcperm_factory(
        "IsControle",
        "pode_operar_controle",
        "Apenas usuários do grupo Controle podem realizar esta ação.",
    )
):
    pass


class IsGerencia(
    funcperm_factory(
        "IsGerencia",
        "pode_operar_gerencia",
        "Apenas usuários de Gerência, Superintendência ou Diretoria podem realizar esta ação.",
    )
):
    pass


class IsDashboardOverview(
    funcperm_factory(
        "IsDashboardOverview",
        "pode_acessar_dashboard_overview",
        "Apenas usuários de Superintendência, Gerência ou Diretoria podem acessar o dashboard geral.",
    )
):
    pass


class IsMapMetrics(
    funcperm_factory(
        "IsMapMetrics",
        "pode_acessar_map_metrics",
        "Apenas usuários autorizados podem acessar métricas do mapa.",
    )
):
    pass


class IsGerenteSuperintendencia(HasFunctionalPermission):  # type: ignore[misc]
    """
    Regra composta fixa:
    - permissão funcional "pode_aprovar_gerente_superintendencia"
    - grupo de função "Gerente"
    """

    functional_codename = "pode_aprovar_gerente_superintendencia"
    message = "Apenas Gerentes da Superintendência podem realizar esta ação."

    def has_permission(self, request: Request, view: APIView) -> bool:
        if not super().has_permission(request, view):
            return False
        user = request.user
        return bool(user and user.groups.filter(name="Gerente").exists())


class IsOwnerOrPrivileged(HasFunctionalPermission):  # type: ignore[misc]
    """
    Permissão para edição de solicitações.

    - superuser: acesso total
    - usuário com permissão funcional privilegiada: acesso total
    - owner do objeto: acesso ao próprio objeto
    """

    functional_codename = "pode_editar_como_owner_ou_privilegiado"
    message = "Você só pode editar suas próprias solicitações ou possuir privilégio de gestão."

    def has_permission(self, request: Request, view: APIView) -> bool:
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request: Request, view: APIView, obj: object) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if getattr(user, "is_superuser", False):
            return True
        if self.functional_codename in get_user_functional_permissions(user):
            return True

        obj_usuario = getattr(obj, "usuario", None)
        return obj_usuario == user


class HasSectorAccess(permissions.BasePermission):  # type: ignore[misc]
    """
    Permissão para acesso à grade mensal de disponibilidade por setor.

    Regras (conforme PLAN_multi_sector_availability.md):
    - Superusers: acesso a todos os setores
    - Grupo "Controle": BLOQUEADO (não tem acesso à grade mensal)
    - Sem gerencia_id: permite (assume SUPER - comportamento atual)
    - Com gerencia_id: verifica se usuário pertence à gerência via EquipeGerencia

    Usado em: MonthlyAvailabilityView
    """

    message = "Você não tem acesso a este setor."

    def has_permission(self, request: Request, view: APIView) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False

        # Superusers sempre podem acessar tudo
        if getattr(request.user, "is_superuser", False):
            return True

        # Grupo "Controle" não tem acesso à grade mensal
        if request.user.groups.filter(name="Controle").exists():  # type: ignore[attr-defined]
            self.message = "O grupo Controle não tem acesso à grade mensal de disponibilidade."
            return False

        # Obter gerencia_id da URL (via kwargs) ou query params
        gerencia_id_raw = view.kwargs.get("gerencia_id")  # type: ignore[attr-defined]
        if gerencia_id_raw is None:
            gerencia_id_raw = request.query_params.get("gerencia_id")

        # Sem gerencia_id = comportamento SUPER (permitido para todos autenticados)
        if gerencia_id_raw is None:
            return True

        # Hardening: evitar ValueError em query params inválidos
        try:
            gerencia_id = int(gerencia_id_raw)
        except (TypeError, ValueError):
            # Deixar o view validar e retornar 400 quando aplicável
            return True

        # Com gerencia_id = verificar se usuário pertence à gerência
        from apps.core.models import EquipeGerencia

        has_access = EquipeGerencia.objects.filter(
            usuario=request.user,
            gerencia_id=gerencia_id,
        ).exists()

        if not has_access:
            self.message = "Você não tem acesso a este setor."

        return has_access
