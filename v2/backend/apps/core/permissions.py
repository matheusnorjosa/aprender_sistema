"""
DRF permissions para RBAC funcional (database-driven).

Epic 2 RBAC Refactor (2026-04-23): introduz `HasPerm(codename)`
parametrizado como padrão canônico + marca as 12 classes factory legacy
com `warnings.warn(DeprecationWarning)` no `__init__`. Classes legacy
continuam funcionais — remoção efetiva é Epic 5 (libcst codemod).
PEP 702 `@typing.deprecated` será readicionado quando subirmos para Python 3.13.

Ver v2/docs/RBAC_NAMING.md para convenção completa.

Backwards compatible:
- nomes das classes publicas preservados;
- imports existentes continuam funcionando;
- comportamento das legacy idêntico (só emite DeprecationWarning).
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportCallIssue=false
from __future__ import annotations

import warnings
from typing import cast

from rest_framework import permissions  # type: ignore[attr-defined]
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.core.services.rbac_permissions import get_user_functional_permissions

# PEP 702 `@typing.deprecated` exige Python 3.13+. Em 3.12 nos baseamos
# em runtime warnings via `warnings.warn(DeprecationWarning)` no __init__
# de cada classe legacy. Quando subirmos para 3.13, podemos readicionar
# o decorator para sinalização em static type-checkers.

# Epic 5 (2026-04-24): permitir composition de permission INSTANCES em
# `permission_classes`. DRF espera callables (classes) em permission_classes
# e faz `p()` para instanciar. Como HasPerm é parametrizada e a composition
# retorna `permissions.OR`/`AND`/`NOT` instances, essas classes precisam de
# `__call__` retornando self para DRF não falhar com "OR object is not callable".
permissions.OR.__call__ = lambda self: self  # type: ignore[method-assign]
permissions.AND.__call__ = lambda self: self  # type: ignore[method-assign]
permissions.NOT.__call__ = lambda self: self  # type: ignore[method-assign]


class HasPerm(permissions.BasePermission):  # type: ignore[misc]
    """
    Capability-oriented parametric permission class (DRF).

    Checa uma único functional permission codename via
    `get_user_functional_permissions`. Preferido sobre subclassing para
    endpoints novos. Emite a decisão de design do master-plan §3.3
    (RBAC Refactor): classes DRF devem ser parametrizadas, não 1 classe
    por capability.

    Composition (DRF 3.9+):
        HasPerm("a") | HasPerm("b")  # OR — grant se qualquer um
        HasPerm("a") & HasPerm("b")  # AND — grant só se ambos
        ~HasPerm("a")                # NOT — grant se não tem a perm

    Usage:
        class MyView(APIView):
            permission_classes = [IsAuthenticated, HasPerm("approve_solicitation")]

    Nota sobre app_label:
        O prefixo "core." é opcional — o sistema funcional usa codename
        bare. Aceitamos ambas as formas para familiaridade com
        `user.has_perm()` nativo do Django.
    """

    def __init__(self, codename: str, *, message: str | None = None) -> None:
        # Strip "app_label." prefix se presente
        self.codename = codename.split(".", 1)[-1] if "." in codename else codename
        if message:
            self.message = message

    def __call__(self) -> "HasPerm":
        """DRF composition resolve para uma callable; já somos uma instance."""
        return self

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if getattr(user, "is_superuser", False):
            return True
        return self.codename in get_user_functional_permissions(user)

    def __repr__(self) -> str:
        return f"HasPerm({self.codename!r})"

    # Composition sobre instances (DRF OperandHolder só opera em classes).
    # Permite o idioma canônico `HasPerm("a") | HasPerm("b")` em
    # `permission_classes`. Delegamos para as classes `OR`/`AND`/`NOT` do
    # próprio DRF. Retornamos Any para evitar strict-type mismatch — DRF
    # OR/AND/NOT implementam o protocolo BasePermission mas não herdam dele.
    def __or__(self, other):  # type: ignore[no-untyped-def]
        return permissions.OR(self, other)

    def __and__(self, other):  # type: ignore[no-untyped-def]
        return permissions.AND(self, other)

    def __invert__(self):  # type: ignore[no-untyped-def]
        return permissions.NOT(self)

    def __ror__(self, other):  # type: ignore[no-untyped-def]
        return permissions.OR(other, self)

    def __rand__(self, other):  # type: ignore[no-untyped-def]
        return permissions.AND(other, self)


class HasFunctionalPermission(permissions.BasePermission):  # type: ignore[misc]
    """
    Base class para checagem por codename funcional.

    NOTA (Epic 2): preferir `HasPerm(codename)` inline em permission_classes
    para endpoints novos. Esta classe continua servindo de base para as 12
    factory classes legacy + 2 compostas (`IsGerenteSuperintendencia`,
    `IsOwnerOrPrivileged`). Remoção das legacy é Epic 5.
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


def _warn_legacy(class_name: str, new_codename: str) -> None:
    """Helper: emite DeprecationWarning padronizado apontando para HasPerm equivalente."""
    warnings.warn(
        f"{class_name} is deprecated; use HasPerm({new_codename!r}). "
        "This class will be removed in Epic 5 of the RBAC refactor. "
        "See v2/docs/RBAC_NAMING.md.",
        DeprecationWarning,
        stacklevel=3,
    )


# ============================================================================
# Epic 2 Legacy factory classes (12) — deprecated em favor de HasPerm(codename)
#
# Cada uma emite DeprecationWarning no __init__ apontando para HasPerm
# equivalente. Remoção efetiva no Epic 5 (libcst codemod). Ver master-plan
# §3.3 e v2/docs/RBAC_NAMING.md.
# ============================================================================


class IsSuperintendencia(
    funcperm_factory(
        "IsSuperintendencia",
        "approve_solicitation",
        "Apenas usuários da Superintendência, DAT ou Superusuários podem realizar esta ação.",
    )
):
    def __init__(self) -> None:
        super().__init__()
        _warn_legacy("IsSuperintendencia", "approve_solicitation")


class IsSuperintendenciaOnly(
    funcperm_factory(
        "IsSuperintendenciaOnly",
        "execute_restricted_operations",
        "Apenas usuários da Superintendência podem realizar esta ação.",
    )
):
    def __init__(self) -> None:
        super().__init__()
        _warn_legacy("IsSuperintendenciaOnly", "execute_restricted_operations")


class IsCoordenadorOrDAT(
    funcperm_factory(
        "IsCoordenadorOrDAT",
        "create_solicitation",
        "Apenas Coordenadores, Apoio de Coordenação ou DAT podem criar solicitações.",
    )
):
    def __init__(self) -> None:
        super().__init__()
        _warn_legacy("IsCoordenadorOrDAT", "create_solicitation")


class IsControleOrSuper(
    funcperm_factory(
        "IsControleOrSuper",
        "import_spreadsheet",
        "Apenas Controle ou Superintendência podem realizar esta ação.",
    )
):
    def __init__(self) -> None:
        super().__init__()
        _warn_legacy("IsControleOrSuper", "import_spreadsheet")


class IsDATOrSuper(
    funcperm_factory(
        "IsDATOrSuper",
        "manage_admin_registries",
        "Apenas usuários do grupo DAT ou superusers podem realizar esta ação.",
    )
):
    def __init__(self) -> None:
        super().__init__()
        _warn_legacy("IsDATOrSuper", "manage_admin_registries")


class IsComprasDashboardAccess(
    funcperm_factory(
        "IsComprasDashboardAccess",
        "view_compras_dashboard",
        "Apenas usuários dos grupos DAT ou Diretoria podem acessar o dashboard de compras.",
    )
):
    def __init__(self) -> None:
        super().__init__()
        _warn_legacy("IsComprasDashboardAccess", "view_compras_dashboard")


class IsDAT(
    funcperm_factory(
        "IsDAT",
        "manage_purchases_and_materials",
        "Apenas usuários do grupo DAT podem realizar esta ação.",
    )
):
    def __init__(self) -> None:
        super().__init__()
        _warn_legacy("IsDAT", "manage_purchases_and_materials")


class IsControleOrDAT(
    funcperm_factory(
        "IsControleOrDAT",
        "operate_preagenda",
        "Apenas Controle ou DAT podem realizar esta ação.",
    )
):
    def __init__(self) -> None:
        super().__init__()
        _warn_legacy("IsControleOrDAT", "operate_preagenda")


class IsControle(
    funcperm_factory(
        "IsControle",
        "run_daily_operations",
        "Apenas usuários do grupo Controle podem realizar esta ação.",
    )
):
    def __init__(self) -> None:
        super().__init__()
        _warn_legacy("IsControle", "run_daily_operations")


class IsGerencia(
    funcperm_factory(
        "IsGerencia",
        "supervise_operations",
        "Apenas usuários com permissão gerencial (Gerência, Superintendência ou Diretoria) podem realizar esta ação.",
    )
):
    def __init__(self) -> None:
        super().__init__()
        _warn_legacy("IsGerencia", "supervise_operations")


class IsDashboardOverview(
    funcperm_factory(
        "IsDashboardOverview",
        "view_overview_dashboard",
        "Apenas usuários com permissão de dashboard (Superintendência, Gerência ou Diretoria) podem acessar o dashboard geral.",
    )
):
    def __init__(self) -> None:
        super().__init__()
        _warn_legacy("IsDashboardOverview", "view_overview_dashboard")


class IsMapMetrics(
    funcperm_factory(
        "IsMapMetrics",
        "view_map_metrics",
        "Apenas usuários autorizados podem acessar métricas do mapa.",
    )
):
    def __init__(self) -> None:
        super().__init__()
        _warn_legacy("IsMapMetrics", "view_map_metrics")


class IsGerenteSuperintendencia(HasFunctionalPermission):  # type: ignore[misc]
    """
    Regra composta fixa:
    - permissão funcional "approve_solicitation_batch"
    - grupo de função "Gerente"
    """

    functional_codename = "approve_solicitation_batch"
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

    functional_codename = "edit_solicitation_as_owner_or_privileged"
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

        # Epic 3.2 RBAC Refactor (2026-04-23): `HasSectorAccess` bloqueia
        # explicitamente "Controle" por design documentado em
        # PLAN_multi_sector_availability.md (Controle não faz gestão
        # de setor — opera pré-agenda). Mantemos o block inline porque:
        # (1) é BLOCK específico, não authz positiva padrão;
        # (2) o rationale é ancorado em design doc;
        # (3) Epic 6 lint whitelist permite este caso específico
        #     (arquivo `permissions.py` é whitelist natural da classe base).
        if request.user.groups.filter(name="Controle").exists():  # type: ignore[attr-defined]  # noqa: RBAC-block-allowed
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
            self.message = "gerencia_id deve ser um número inteiro."
            return False

        # Com gerencia_id = verificar se usuário pertence à gerência
        from apps.core.models import EquipeGerencia

        has_access = EquipeGerencia.objects.filter(
            usuario=request.user,
            gerencia_id=gerencia_id,
        ).exists()

        if not has_access:
            self.message = "Você não tem acesso a este setor."

        return has_access
