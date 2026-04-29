"""
DRF permissions para RBAC funcional (database-driven).

SSOT das classes DRF do RBAC. Re-exportado por `apps.core.rbac`.

Idioma canônico:
    permission_classes = [IsAuthenticated, HasPerm("approve_solicitation")]

Para composition:
    permission_classes = [HasPerm("a") | HasPerm("b")]

3 classes "não-reduzíveis" mantidas (ver RBAC_NAMING.md §3):
- `IsGerenteSuperintendencia` (composite: funcperm + grupo Django)
- `IsOwnerOrPrivileged` (object-level: checa obj.usuario)
- `HasSectorAccess` (dynamic scope via gerencia_id query param)

Ver v2/docs/RBAC_NAMING.md para convenção completa.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportCallIssue=false, reportIncompatibleMethodOverride=false, reportMissingTypeStubs=false, reportArgumentType=false
from __future__ import annotations

from rest_framework import permissions  # type: ignore[attr-defined]
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.core.services.rbac_permissions import get_user_functional_permissions

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

    Checa um único functional permission codename via
    `get_user_functional_permissions`. Preferido sobre subclassing para
    endpoints novos. Decisão de design: classes DRF devem ser parametrizadas,
    não 1 classe por capability (NIST RBAC §5.3).

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

    Preferir `HasPerm(codename)` inline em `permission_classes` para endpoints
    novos. Esta classe continua servindo de base para as 2 classes compostas
    mantidas (`IsGerenteSuperintendencia`, `IsOwnerOrPrivileged`).
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


# ============================================================================
# 3 classes mantidas pós-Epic 5.3 — expressam lógica que `HasPerm(codename)`
# não cobre:
# - Composite rule (funcperm + grupo Django)
# - Object-level check (obj.usuario)
# - Dynamic scope via query param
# ============================================================================


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
        # `IsGerenteSuperintendencia` é composite (funcperm + grupo Django):
        # valida que o usuário tem a função "Gerente" além da funcperm.
        # Uso aqui é whitelist natural — a classe é uma das 3 mantidas por design (RBAC_NAMING §3).
        return bool(user and user.groups.filter(name="Gerente").exists())  # noqa: RBAC-composite-allowed


class IsAssistenteAdministrativoControle(permissions.BasePermission):  # type: ignore[misc]
    """
    Regra composta fixa (PR 3 hardening RBAC, 2026-04-29):
    - Setor Django "Controle"
    - Função Django "Assistente Administrativo"

    Combinada via OR com `IsGerenteSuperintendencia` em
    `CanAccessSolicitacaoApprovals` para autorizar aprovação/reprovação de
    solicitações (individual e lote).

    Por design não usa `HasFunctionalPermission` como base: a regra é
    estritamente composite role (Setor × Função). Cap funcional permanece
    `approve_solicitation` no Setor `Superintendência` — composite garante
    que apenas Setor `Controle` + Função `Assistente Administrativo` passe
    por esta classe (Assistente fora do Controle ou Controle puro → 403).

    Whitelist natural — composite documentado em RBAC_NAMING §3.
    """

    message = "Apenas Assistente Administrativo do Controle pode realizar esta ação."

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if getattr(user, "is_superuser", False):
            return True
        return bool(
            user.groups.filter(name="Controle").exists()  # noqa: RBAC-composite-allowed
            and user.groups.filter(name="Assistente Administrativo").exists()  # noqa: RBAC-composite-allowed
        )


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
    Permissão de scope por gerência para a grade mensal de disponibilidade.

    Regras (D8 — 2026-04-28):
    - Superusers: acesso a todos os setores.
    - Sem `gerencia_id` na query: exige pelo menos 1 vínculo de
      `EquipeGerencia` ativa. Antes era "comportamento SUPER" (permitido a
      todos autenticados), mas isso permitia que Formador/DAT/Diretoria
      sem cap global e sem vínculo entrassem na Grade Mensal indevidamente.
      A composition `CanViewAllAvailability | HasSectorAccess` em
      `MonthlyAvailabilityView` ainda permite que Controle/Gerente passem
      pela cap, sem precisar de vínculo de gerência.
    - Com `gerencia_id`: verifica se usuário pertence à gerência específica
      via `EquipeGerencia`.

    Block antigo de "grupo Controle" foi REMOVIDO em 2026-04-27 (Bug 1 fix
    pós RBAC Access Policy Realignment). Razão: o seed 0077 atribui a
    capability `view_all_availability` ao grupo Controle por design da
    intent matrix (memória `reference_rbac_intent_matrix.md`). O block por
    nome de grupo contradizia a capability declarada.

    Composição idiomática:

        permission_classes = [IsAuthenticated, CanViewAllAvailability | HasSectorAccess]

    Quem tem `view_all_availability` bypassa o scope; quem não tem cai no
    check de gerência via `HasSectorAccess`.

    Usado em: MonthlyAvailabilityView
    """

    message = "Você não tem acesso a este setor."

    def has_permission(self, request: Request, view: APIView) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False

        # Superusers sempre podem acessar tudo
        if getattr(request.user, "is_superuser", False):
            return True

        # Obter gerencia_id da URL (via kwargs) ou query params
        gerencia_id_raw = view.kwargs.get("gerencia_id")  # type: ignore[attr-defined]
        if gerencia_id_raw is None:
            gerencia_id_raw = request.query_params.get("gerencia_id")

        # Importação local para evitar circular import na inicialização do módulo.
        from apps.core.models import EquipeGerencia

        # D8 (2026-04-28): sem `gerencia_id` exige vínculo organizacional.
        # Quem precisa de visão ampla (Controle/Gerente) bate antes em
        # `CanViewAllAvailability` na composition; quem cai aqui sem vínculo
        # é Formador/DAT/Diretoria/sem-vínculo → 403.
        if gerencia_id_raw is None:
            has_any_vinculo = EquipeGerencia.objects.filter(
                usuario=request.user,
                ativo=True,
            ).exists()
            if not has_any_vinculo:
                self.message = "Você não tem acesso à grade mensal de disponibilidade."
            return has_any_vinculo

        # Hardening: evitar ValueError em query params inválidos
        try:
            gerencia_id = int(gerencia_id_raw)
        except (TypeError, ValueError):
            self.message = "gerencia_id deve ser um número inteiro."
            return False

        # Com gerencia_id = verificar se usuário pertence à gerência
        has_access = EquipeGerencia.objects.filter(
            usuario=request.user,
            gerencia_id=gerencia_id,
        ).exists()

        if not has_access:
            self.message = "Você não tem acesso a este setor."

        return has_access
