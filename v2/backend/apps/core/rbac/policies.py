"""
Capability Policy Layer (Epic 4.1, Issue #1232).

Implementa a 3ª camada NIST RBAC do projeto:

    User → Roles (Groups) → Capabilities (PermissaoFuncional) ← Policies ← Views

Views referenciam `permission_classes = [CanXxx]` em vez de empilhar
`HasPerm("a") | HasPerm("b") | HasPerm("c")`. Cada Policy é mapeada para
um conjunto de capabilities elegíveis em `ACCESS_POLICIES` — a matriz é
a SSOT, e mudanças nela são compatíveis (não quebram contrato API).

Decisões fixadas com stakeholder em 2026-04-26 (memórias
`feedback_capability_policy_layer_pattern.md` + `feedback_motivo_legitimo_acesso.md`):

1. **Hybrid arquitetura** (não full admin-driven): matriz hardcoded;
   admin gerencia apenas Group × Capability via UI.
2. **Naming**: `<verb>_<resource>` snake_case para keys, `Can<CamelCase>`
   para classes. 1 nome canonical, 3 derivações mecânicas.
3. **Vocabulário verbos**: `access_X`, `use_X`, `import_X`, `manage_X`, `view_X`.
4. **NÃO usar sufixo `_policy`** em keys públicas.
5. **NÃO misturar roles e capabilities** na matriz — só capabilities.
6. **Motivo legítimo de acesso > cargo**: AuditLog tem 4 motivos
   (auditar/operar/suportar/aprovar); Dashboard Compras tem 2 (decidir +
   suportar com DAT). Ver memória.
7. **Stability rules**: keys imutáveis após exposição via
   `/api/me/policies/` (Issue 4.4 — não nesse PR); matriz interna mutável.

Ver `v2/docs/RBAC_NAMING.md §9` (Policy Resolution Rules).
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false, reportUnusedImport=false

from __future__ import annotations

from typing import Final

from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import APIView

# Side-effect import: garante o monkey-patch de OR/AND/NOT.__call__ aplicado
# em apps.core.rbac.permissions (necessário para `CanA() | CanB()` funcionar
# em `permission_classes`). Não usamos HasPerm aqui, mas precisamos que o
# patch esteja ativo antes do primeiro uso de composition.
from apps.core.rbac import permissions as _rbac_permissions  # noqa: F401
from apps.core.rbac.helpers import user_has_any_perm

# ============================================================================
# SSOT: matriz declarativa Policy → capabilities elegíveis (OR semantics)
# ============================================================================
#
# Cada entry: `"<canonical_key>": frozenset({"<cap1>", "<cap2>", ...})`
#
# Adicionar nova policy:
#   1. Registrar key + capabilities aqui (siga vocabulário canônico)
#   2. Criar classe `Can<CamelCase>` abaixo com `policy = "<key>"`
#   3. Re-exportar em `apps/core/rbac/__init__.py`
#   4. Atualizar `ACCESS_POLICIES` snapshot test (Issue 4.5)
#
# Mudar capabilities elegíveis de uma policy existente:
#   - Compatível com contrato API público (frontend não depende)
#   - Atualize comentário de motivo legítimo de acesso
#
# Renomear key:
#   - BREAKING após exposição via `/api/me/policies/` (deprecation period)


ACCESS_POLICIES: Final[dict[str, frozenset[str]]] = {
    # --- Solicitação / Audit ---
    # AuditLog tem 4 motivos legítimos: auditar (Super/Gerente próprias e
    # batch), operar (Controle), suportar (DAT). Confirmado Epic 1.6.
    "access_audit_logs": frozenset(
        {
            "manage_admin_registries",
            "operate_preagenda",
            "approve_solicitation",
            "approve_solicitation_batch",
        }
    ),
    # Transições GCal (publish/cancel/resync) — Controle (operação) +
    # Superintendência (decisão pós-aprovação).
    "manage_solicitacao_status": frozenset({"operate_preagenda", "approve_solicitation"}),
    # --- Dashboards executivos ---
    # Dashboard Compras: Diretoria (decidir) + DAT (suportar/validar).
    # Confirmado Epic 1.6 — DAT é ator transversal.
    "view_compras_dashboard": frozenset({"view_compras_dashboard", "manage_admin_registries"}),
    # Painel de pendências cross-funcional: gestão (DAT/Compras) + operação
    # (Controle) + decisão (Diretoria com view_compras_dashboard).
    "view_compras_pendencias": frozenset(
        {
            "manage_admin_registries",
            "manage_purchases_and_materials",
            "run_daily_operations",
            "view_compras_dashboard",
        }
    ),
    # Stats agregadas: gestão + operação (Diretoria fora — usa dashboard).
    "view_compras_stats": frozenset(
        {
            "manage_admin_registries",
            "manage_purchases_and_materials",
            "run_daily_operations",
        }
    ),
    # Dashboard executivo geral — Diretoria (decisão).
    "view_overview_dashboard": frozenset({"view_overview_dashboard"}),
    # Mapa do Brasil — métricas geográficas (Diretoria).
    "view_map_metrics": frozenset({"view_map_metrics"}),
    # --- Reports ---
    # Relatórios gerenciais: Controle (operar) + Super (auditar) + DAT (suportar).
    "view_reports": frozenset({"operate_preagenda", "approve_solicitation", "manage_admin_registries"}),
    # --- GCal ---
    # Endpoints GCal (preview, lista, dashboards de erro): operar + aprovar.
    "use_gcal": frozenset({"operate_preagenda", "approve_solicitation"}),
    # --- Availability ---
    # Visualização ampla de disponibilidades — Controle/Gerente/Coord/Apoio.
    "view_all_availability": frozenset({"view_all_availability"}),
    # --- Imports operacionais ---
    # Import de bloqueios: DAT importa, Controle/Gerente/Coord operam.
    "import_availability_blocks": frozenset({"import_spreadsheet", "view_all_availability"}),
    # Import de compras: DAT importa, Compras/Controle operam.
    "import_compras": frozenset(
        {
            "import_spreadsheet",
            "manage_purchases_and_materials",
            "run_daily_operations",
        }
    ),
    # Imports operacionais genéricos (eventos, produtos, deslocamentos): DAT + Controle.
    "import_generic_spreadsheet": frozenset({"import_spreadsheet", "run_daily_operations"}),
    # --- Admin registries (single-cap, mas vira policy pra estabilizar contrato) ---
    "manage_admin_registries": frozenset({"manage_admin_registries"}),
    "manage_purchases_and_materials": frozenset({"manage_purchases_and_materials"}),
}


# ============================================================================
# Base class
# ============================================================================


class _PolicyPermission(permissions.BasePermission):  # type: ignore[misc]
    """
    Base abstrata para Policy classes.

    Subclasses declaram `policy: ClassVar[str]` apontando para uma key da
    matriz `ACCESS_POLICIES`. A semântica é OR: usuário com QUALQUER UMA
    das capabilities elegíveis passa.

    Regras (idênticas a `HasPerm` para garantir paridade comportamental
    quando Issue 4.2 migrar views):
      1. Não autenticado → False
      2. Superuser → True (bypass)
      3. Policy key ausente / matriz vazia → False (fail-secure)
      4. Caso geral → `user_has_any_perm(user, *capabilities)`

    Composition `CanA() | CanB()` funciona via DRF OR (monkey-patch de
    `permissions.OR.__call__` aplicado em `apps.core.rbac.permissions`).
    """

    policy: str = ""  # subclasses override

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if getattr(user, "is_superuser", False):
            return True
        codenames = ACCESS_POLICIES.get(self.policy)
        if not codenames:
            return False
        return user_has_any_perm(user, *codenames)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(policy={self.policy!r})"

    # Composition em instances (DRF 3.9+ funciona em classes; instâncias
    # exigem o monkey-patch já aplicado em rbac.permissions). Repetimos
    # aqui pra deixar explícito que Policy também é composable.
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


# ============================================================================
# Concrete classes (ordem espelha a matriz para facilitar review)
# ============================================================================


class CanAccessAuditLogs(_PolicyPermission):
    policy = "access_audit_logs"


class CanManageSolicitacaoStatus(_PolicyPermission):
    policy = "manage_solicitacao_status"


class CanViewComprasDashboard(_PolicyPermission):
    policy = "view_compras_dashboard"


class CanViewComprasPendencias(_PolicyPermission):
    policy = "view_compras_pendencias"


class CanViewComprasStats(_PolicyPermission):
    policy = "view_compras_stats"


class CanViewOverviewDashboard(_PolicyPermission):
    policy = "view_overview_dashboard"


class CanViewMapMetrics(_PolicyPermission):
    policy = "view_map_metrics"


class CanViewReports(_PolicyPermission):
    policy = "view_reports"


class CanUseGcal(_PolicyPermission):
    policy = "use_gcal"


class CanViewAllAvailability(_PolicyPermission):
    policy = "view_all_availability"


class CanImportAvailabilityBlocks(_PolicyPermission):
    policy = "import_availability_blocks"


class CanImportCompras(_PolicyPermission):
    policy = "import_compras"


class CanImportGenericSpreadsheet(_PolicyPermission):
    policy = "import_generic_spreadsheet"


class CanManageAdminRegistries(_PolicyPermission):
    policy = "manage_admin_registries"


class CanManagePurchasesAndMaterials(_PolicyPermission):
    policy = "manage_purchases_and_materials"


__all__ = [
    "ACCESS_POLICIES",
    "_PolicyPermission",
    "CanAccessAuditLogs",
    "CanManageSolicitacaoStatus",
    "CanViewComprasDashboard",
    "CanViewComprasPendencias",
    "CanViewComprasStats",
    "CanViewOverviewDashboard",
    "CanViewMapMetrics",
    "CanViewReports",
    "CanUseGcal",
    "CanViewAllAvailability",
    "CanImportAvailabilityBlocks",
    "CanImportCompras",
    "CanImportGenericSpreadsheet",
    "CanManageAdminRegistries",
    "CanManagePurchasesAndMaterials",
]
