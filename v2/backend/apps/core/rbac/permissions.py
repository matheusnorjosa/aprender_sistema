"""
DRF permissions para RBAC funcional (database-driven).

SSOT das classes DRF do RBAC. Re-exportado por `apps.core.rbac`.

Idioma canônico:
    permission_classes = [IsAuthenticated, HasPerm("approve_solicitation")]

Para composition:
    permission_classes = [HasPerm("a") | HasPerm("b")]

2 classes "não-reduzíveis" mantidas (ver RBAC_NAMING.md §3):
- `IsOwnerOrPrivileged` (object-level: checa obj.usuario) e a filha `PodeExcluirSolicitacao`
- `HasSectorAccess` (dynamic scope via gerencia_id query param)

Ver v2/docs/RBAC_NAMING.md para convenção completa.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportCallIssue=false, reportIncompatibleMethodOverride=false, reportMissingTypeStubs=false, reportArgumentType=false
from __future__ import annotations

from typing import TYPE_CHECKING

from rest_framework import permissions  # type: ignore[attr-defined]
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.core.services.rbac_permissions import get_user_functional_permissions

if TYPE_CHECKING:
    from apps.core.services.solicitacao_scope import EscritaEmSolicitacao

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
    novos. Esta classe continua servindo de base para `IsOwnerOrPrivileged`.
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


class SuperuserOnly(permissions.BasePermission):  # type: ignore[misc]
    """
    Tier-0: apenas superusuários (P0-1, auditoria 2026-07-17).

    Usada nos endpoints de administração de privilégio/identidade — CRUD de
    grupo, matriz Grupo×Capability e membership — onde NENHUMA capability
    operacional deve conceder acesso. Fecha o vetor de escalada onde um DAT
    editava a matriz / cunhava aprovadores.

    NÃO usar `rest_framework.permissions.IsAdminUser`: ele checa `is_staff`,
    não `is_superuser`.
    """

    message = "Apenas superusuários podem realizar esta ação."

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and getattr(user, "is_superuser", False))


# ============================================================================
# Classes mantidas pós-Epic 5.3 — expressam lógica que `HasPerm(codename)`
# não cobre:
# - Object-level check (obj.usuario)
# - Dynamic scope via query param
# (`IsGerenteSuperintendencia` saiu no PR 8 das permissões, junto com `approve_solicitation_batch`;
# `IsAssistenteAdministrativoControle` saiu no PR 11, com as bases de aprovação por grupo.)
# ============================================================================


class IsOwnerOrPrivileged(HasFunctionalPermission):  # type: ignore[misc]
    """
    Permissão para edição de solicitações.

    - superuser: acesso total
    - usuário com permissão funcional privilegiada: acesso no escopo dele (`user_can_access_solicitacao`);
      a aprovadora por vínculo (GERENTE em g1) só no fluxo SUPER da Superintendência e nas gerências de um
      2º vínculo de GERENTE dela (regra do dono, 30/09)
    - owner do objeto: acesso ao próprio objeto
    """

    functional_codename = "edit_solicitation_as_owner_or_privileged"
    message = "Você só pode editar suas próprias solicitações ou possuir privilégio de gestão."
    message_escopo_superintendencia = (
        "A gerência da Superintendência só edita ou exclui solicitações do fluxo SUPER da Superintendência."
    )

    def has_permission(self, request: Request, view: APIView) -> bool:
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request: Request, view: APIView, obj: object) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        from apps.core.services.solicitacao_scope import EscritaEmSolicitacao

        escrita = EscritaEmSolicitacao(user)
        if self.permite(user, obj, escrita):
            return True
        # Regra do dono (30/09): o 403 diz por que a aprovadora (que VÊ a solicitação) não edita.
        if self.functional_codename in escrita.capacidades and escrita.restrita:
            self.message = self.message_escopo_superintendencia
        return False

    def permite(self, user: object, obj: object, escrita: EscritaEmSolicitacao) -> bool:
        """A regra sem efeito colateral, com os fatos do usuário de `escrita` (`EscritaEmSolicitacao`).

        A lista chama com a mesma `escrita` para a página inteira (`SolicitacaoSerializer.pode_excluir`).
        """
        if getattr(user, "is_superuser", False):
            return True
        # M10-01 (#1623): o privilégio de edição de solicitação só vale DENTRO
        # do escopo do ator (global OU própria gerência OU dono) — não mais
        # nacional. SSOT: `user_can_access_solicitacao` (`EscritaEmSolicitacao.no_escopo`).
        if self.functional_codename in escrita.capacidades and escrita.no_escopo(obj):
            return True
        obj_usuario = getattr(obj, "usuario", None)
        return obj_usuario == user


class PodeExcluirSolicitacao(IsOwnerOrPrivileged):  # type: ignore[misc]
    """
    Permissão para excluir solicitações: quem edita (`IsOwnerOrPrivileged`) e, desde 27/10/2026, a Apoio
    de Coordenação no evento de outra pessoa que já está no Google, na gerência onde ela é APOIO
    (`EscritaEmSolicitacao.apoio_pode_excluir_do_google`). As recusas do `perform_destroy` valem por cima.
    """

    message = (
        "Você só pode excluir suas próprias solicitações, as do seu escopo de gestão ou, como Apoio de "
        "Coordenação, o evento aprovado de outra pessoa que já está no Google Agenda da sua gerência."
    )

    def permite(self, user: object, obj: object, escrita: EscritaEmSolicitacao) -> bool:
        return super().permite(user, obj, escrita) or escrita.apoio_pode_excluir_do_google(obj)


class HasSectorAccess(permissions.BasePermission):  # type: ignore[misc]
    """
    Permissão de scope por gerência para a grade mensal de disponibilidade.

    Regras (D8 — 2026-04-28):
    - Superusers: acesso a todos os setores.
    - PR 9 (P9-3): só conta papel G/C/A vigente em gerência ativa
      (`EquipeGerencia.gerencias_de_atuacao`), o mesmo da tela. O papel FORMADOR sozinho não abre.
    - Sem `gerencia_id` na query: exige pelo menos 1 gerência de atuação.
      Antes era "comportamento SUPER" (permitido a
      todos autenticados), mas isso permitia que Formador/DAT/Diretoria
      sem cap global e sem vínculo entrassem na Grade Mensal indevidamente.
      A composition `CanViewAllAvailability | HasSectorAccess` em
      `MonthlyAvailabilityView` ainda permite que Controle/Gerente passem
      pela cap, sem precisar de vínculo de gerência.
    - Com `gerencia_id`: verifica se a gerência é uma das de atuação do usuário.

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
        gerencias = EquipeGerencia.gerencias_de_atuacao(request.user)
        if gerencia_id_raw is None:
            has_any_vinculo = bool(gerencias)
            if not has_any_vinculo:
                self.message = "Você não tem acesso à grade mensal de disponibilidade."
            return has_any_vinculo

        # Hardening: evitar ValueError em query params inválidos
        try:
            gerencia_id = int(gerencia_id_raw)
        except (TypeError, ValueError):
            self.message = "gerencia_id deve ser um número inteiro."
            return False

        # Com gerencia_id = verificar se o usuário atua na gerência (G/C/A)
        has_access = gerencia_id in gerencias

        if not has_access:
            self.message = "Você não tem acesso a este setor."

        return has_access
