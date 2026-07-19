"""
Sentinela meta de resolução de permissão por action do SolicitacaoViewSet (#1261).

Por que existe (memória `feedback_drf_get_permissions_override.md`):
`SolicitacaoViewSet.get_permissions()` tem override com uma LISTA HARDCODED de
actions que delegam ao decorator (`actions_with_custom_permissions`). A segurança
de cada `@action` custom depende de DUAS coisas simultâneas:
  1. o decorator declarar `permission_classes=[...]`; E
  2. o nome da action estar na lista hardcoded de delegação.

Se alguém adiciona uma `@action` nova com `permission_classes` mas ESQUECE de
incluí-la na lista, `get_permissions()` cai no fallback `[IsAuthenticated()]` e
**engole silenciosamente** o decorator — abrindo o endpoint para qualquer usuário
autenticado. Provado empiricamente: numa instância sem dispatch, `get_permissions()`
de uma action custom fora da lista retorna `IsAuthenticated`, não a classe declarada.

Este sentinela trava a regra: TODA action tem uma permission esperada explícita
aqui, e o resolver espelha o binding do DRF (aplica o `permission_classes` do
decorator, depois chama `get_permissions()`) para medir a permissão EFETIVA — a
mesma que o DRF enforça no dispatch real. Assim o teste pega:
  - action nova sem entrada em EXPECTED (drift de cobertura);
  - `@action` custom fora da lista de delegação (buraco de IsAuthenticated);
  - mudança de permission de uma action existente.

Regra para quem mexer: adicionou/alterou action → atualize EXPECTED_PERMISSIONS
conscientemente. O CI vai falhar com mensagem clara até você fazê-lo.

NÃO testa autorização real (quem passa/não passa) — isso é coberto por
test_approval_policy_PA.py e afins. Aqui é meta: qual CLASSE gateia cada action.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportUnknownVariableType=false

from __future__ import annotations

from rest_framework.permissions import IsAuthenticated

import pytest

from apps.core.rbac import (
    CanAccessSolicitationApprovals,
    CanUseGcal,
    HasPerm,
    IsOwnerOrPrivileged,
)
from apps.core.views_solicitacao import SolicitacaoViewSet

# Actions padrão de um ModelViewSet (não-@action).
_STANDARD_ACTIONS = ("create", "update", "partial_update", "destroy", "list", "retrieve")

# Verdade esperada, verificada contra o CÓDIGO (não contra o texto da issue, que
# estava desatualizado: dizia approve->IsGerenteSuperintendencia, batch->HasPerm,
# quando o código real usa a policy composta CanAccessSolicitationApprovals).
#
# Valor: (kind, spec)
#   ("class", Cls)          -> get_permissions() retorna instância de Cls
#   ("has_perm", codename)  -> retorna HasPerm com self.codename == codename
EXPECTED_PERMISSIONS: dict[str, tuple[str, object]] = {
    # override-path (get_permissions retorna a instância diretamente)
    "create": ("has_perm", "create_solicitation"),
    "update": ("class", IsOwnerOrPrivileged),
    "partial_update": ("class", IsOwnerOrPrivileged),
    "destroy": ("class", IsOwnerOrPrivileged),
    "list": ("class", IsAuthenticated),
    "retrieve": ("class", IsAuthenticated),
    # @action custom (decorator + delegação via lista hardcoded)
    "approve": ("class", CanAccessSolicitationApprovals),
    "reject": ("class", CanAccessSolicitationApprovals),
    "batch_approve": ("class", CanAccessSolicitationApprovals),
    "batch_reject": ("class", CanAccessSolicitationApprovals),
    "preview_gcal": ("class", CanUseGcal),
    "publish": ("class", CanUseGcal),
    "resync_gcal": ("class", CanUseGcal),
    "cancel_gcal": ("class", CanUseGcal),
}


def _effective_permissions(action: str) -> list[object]:
    """
    Resolve as permission instances EFETIVAS de uma action, espelhando o binding
    que o DRF faz no dispatch: aplica o `permission_classes` do decorator `@action`
    à instância (como `as_view` faz) e então chama `get_permissions()` — que decide
    entre delegar (super) ou cair no fallback. É a mesma permissão que roda em prod.
    """
    viewset = SolicitacaoViewSet()
    viewset.action = action
    handler = getattr(SolicitacaoViewSet, action, None)
    if handler is not None and hasattr(handler, "kwargs") and "permission_classes" in handler.kwargs:
        viewset.permission_classes = handler.kwargs["permission_classes"]
    return list(viewset.get_permissions())


class TestSolicitacaoActionPermissionSentinel:
    @pytest.mark.parametrize("action", sorted(EXPECTED_PERMISSIONS))
    def test_action_resolves_to_expected_permission(self, action: str):
        kind, spec = EXPECTED_PERMISSIONS[action]
        perms = _effective_permissions(action)

        assert len(perms) == 1, f"action '{action}' deveria resolver 1 permission, got {len(perms)}: {perms}"
        perm = perms[0]

        if kind == "class":
            assert isinstance(perm, spec), (
                f"action '{action}' deveria ser gateada por {spec.__name__}, "
                f"mas resolveu {type(perm).__name__}. "
                "Se for @action custom resolvendo IsAuthenticated, a action provavelmente "
                "não está na lista de delegação de get_permissions() — buraco de segurança."
            )
        else:  # has_perm
            assert (
                type(perm).__name__ == "HasPerm"
            ), f"action '{action}' deveria ser HasPerm({spec!r}), got {type(perm).__name__}"
            assert perm.codename == spec, f"action '{action}' HasPerm codename esperado {spec!r}, got {perm.codename!r}"

    def test_no_custom_action_falls_through_to_isauthenticated_by_mistake(self):
        """
        Guarda direto do buraco: nenhuma @action custom pode resolver IsAuthenticated.
        Toda action de escrita/aprovação/gcal tem gate estrito. Se uma cair em
        IsAuthenticated, foi esquecida na lista de delegação de get_permissions().
        """
        custom = {a.__name__ for a in SolicitacaoViewSet.get_extra_actions()}
        for action in sorted(custom):
            perms = _effective_permissions(action)
            assert not (len(perms) == 1 and isinstance(perms[0], IsAuthenticated)), (
                f"@action custom '{action}' resolveu IsAuthenticated — endpoint aberto a "
                "qualquer autenticado. Adicione-a à lista de delegação em "
                "SolicitacaoViewSet.get_permissions() (e a EXPECTED_PERMISSIONS aqui)."
            )

    def test_every_actual_action_is_covered_by_sentinel(self):
        """
        Drift de cobertura: toda action real (padrão + @action) tem entrada em
        EXPECTED_PERMISSIONS. Falha imediata se alguém adicionar action sem declarar
        a permission esperada aqui — forçando decisão consciente no PR.
        """
        custom = {a.__name__ for a in SolicitacaoViewSet.get_extra_actions()}
        actual = custom | set(_STANDARD_ACTIONS)
        missing = actual - set(EXPECTED_PERMISSIONS)
        assert not missing, (
            f"Actions sem sentinela em EXPECTED_PERMISSIONS: {sorted(missing)}. "
            "Toda action nova exige uma entrada aqui declarando sua permission."
        )

    def test_sentinel_has_no_stale_entries(self):
        """Anti-drift reverso: EXPECTED não pode listar action que não existe mais."""
        custom = {a.__name__ for a in SolicitacaoViewSet.get_extra_actions()}
        actual = custom | set(_STANDARD_ACTIONS)
        stale = set(EXPECTED_PERMISSIONS) - actual
        assert not stale, f"EXPECTED_PERMISSIONS tem entradas órfãs (action removida): {sorted(stale)}."
