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

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false, reportUnusedImport=false

from __future__ import annotations

from typing import Final

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import APIView

# Side-effect import: garante o monkey-patch de OR/AND/NOT.__call__ aplicado
# em apps.core.rbac.permissions (necessário para `CanA() | CanB()` funcionar
# em `permission_classes`). Não usamos HasPerm aqui, mas precisamos que o
# patch esteja ativo antes do primeiro uso de composition.
from apps.core.rbac import permissions as _rbac_permissions  # noqa: F401
from apps.core.rbac.helpers import user_has_any_perm, user_is_assistente_administrativo_controle

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


# Composite policies: keys cuja semântica não cabe em "OR de capabilities"
# (ex: composite Setor × Função). `ACCESS_POLICIES[k]` é frozenset() vazio
# como sentinela; a lógica vive em helpers dedicados despachados por
# `user_has_policy`. Tests que assumem "frozenset não-vazio" devem
# excluir essas keys.
COMPOSITE_POLICY_KEYS: Final[frozenset[str]] = frozenset({"access_solicitation_approvals"})


ACCESS_POLICIES: Final[dict[str, frozenset[str]]] = {
    # --- Solicitação / Audit ---
    # PR 6 hardening RBAC (2026-04-30): policy reduzida a DAT (admin) +
    # Controle (operação). Antes incluía `approve_solicitation` e
    # `approve_solicitation_batch` (Sup, Gerente) — removidos para evitar
    # liberação indevida a Gerente pedagógico e Sup pura. Auditoria por
    # aprovador volta a ser escopo isolado se necessário em onda futura.
    "access_audit_logs": frozenset(
        {
            "manage_admin_registries",
            "operate_preagenda",
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
    # Nota: as 6 views síncronas migram para `HasPerm("import_spreadsheet")` direto
    # em PR-A1 DAT-Imports (2026-04-29). Esta policy continua usada por views
    # async (ASQ-005, /api/imports/*) e pelo contrato `/api/me/policies/` —
    # PR-D do plano DAT-Imports limpa botões antigos no frontend.
    "import_generic_spreadsheet": frozenset({"import_spreadsheet", "run_daily_operations"}),
    # --- Admin registries (single-cap, mas vira policy pra estabilizar contrato) ---
    "manage_admin_registries": frozenset({"manage_admin_registries"}),
    "manage_purchases_and_materials": frozenset({"manage_purchases_and_materials"}),
    # --- Aprovação de solicitações (PR 3 hardening RBAC, 2026-04-29) ---
    # Policy COMPOSITE: a semântica não cabe em "OR de capabilities" porque
    # exige composite Setor × Função (Gerente da Superintendência OU
    # Assistente Administrativo do Controle). Frozenset vazio é sentinela —
    # `user_has_policy` trata a key via `_user_has_solicitation_approvals`.
    "access_solicitation_approvals": frozenset(),
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

    DRY (Epic 4.4): a semântica vive em `user_has_policy`. Esta classe
    apenas delega — view, tests e helpers compartilham a mesma fonte de
    verdade. Mudar política de avaliação = mudar `user_has_policy`.

    Composition `CanA() | CanB()` funciona via DRF OR (monkey-patch de
    `permissions.OR.__call__` aplicado em `apps.core.rbac.permissions`).
    """

    policy: str = ""  # subclasses override

    def has_permission(self, request: Request, view: APIView) -> bool:
        return user_has_policy(request.user, self.policy)

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


class CanAccessSolicitationApprovals(_PolicyPermission):
    """
    Policy composta de aprovação de solicitações (PR 3, 2026-04-29).

    Habilitada para:
    - Gerente da Superintendência (Setor `Superintendência` + Função `Gerente`)
    - Assistente Administrativo do Controle (Setor `Controle` + Função
      `Assistente Administrativo`)

    Implementação composite (não OR de capabilities): a semântica vive em
    `_user_has_solicitation_approvals` e é compartilhada com
    `user_has_policy` para que `/api/me/policies/` exponha o mesmo gate
    consumido pelos 4 endpoints de aprovação.
    """

    policy = "access_solicitation_approvals"
    message = "Apenas Gerentes da Superintendência ou Assistente Administrativo do Controle podem aprovar solicitações."

    def has_permission(self, request: Request, view: APIView) -> bool:
        return _user_has_solicitation_approvals(request.user)


# ============================================================================
# Public surface (Epic 4.4, Issue #1235): contrato externo `/api/me/policies/`
# ============================================================================
#
# `PUBLIC_POLICY_KEYS` é o conjunto de policy keys EXPOSTAS via
# `GET /api/me/policies/`. Subset de `ACCESS_POLICIES` — futuras policies
# internas (não públicas) ficariam fora deste registro.
#
# Stability rules (memória `feedback_capability_policy_layer_pattern.md §6`):
#   - Adicionar key aqui = compatível (frontend opt-in via `policies.includes`)
#   - Renomear key = BREAKING (deprecation period de 2 releases)
#   - Remover key = BREAKING (deprecation period)
#   - Mudar capabilities elegíveis (ACCESS_POLICIES[k]) = compatível
#
# Procedure para nova policy pública:
#   1. Adicionar entrada em ACCESS_POLICIES
#   2. Criar classe Can<CamelCase>(_PolicyPermission)
#   3. Adicionar key aqui em PUBLIC_POLICY_KEYS
#   4. Atualizar snapshot test (Epic 4.5)
#   5. Re-export classe em apps/core/rbac/__init__.py
#
# Test de paridade em test_me_policies.py garante que dev não esqueça step 3.

PUBLIC_POLICY_KEYS: Final[frozenset[str]] = frozenset(
    {
        "access_audit_logs",
        "access_solicitation_approvals",
        "manage_solicitacao_status",
        "view_compras_dashboard",
        "view_compras_pendencias",
        "view_compras_stats",
        "view_overview_dashboard",
        "view_map_metrics",
        "view_reports",
        "use_gcal",
        "view_all_availability",
        "import_availability_blocks",
        "import_compras",
        "import_generic_spreadsheet",
        "manage_admin_registries",
        "manage_purchases_and_materials",
    }
)


# ============================================================================
# Helpers (SSOT da semântica de Policy — usado por View, tests, admin futuro)
# ============================================================================


def _user_has_solicitation_approvals(user: AbstractBaseUser | AnonymousUser | None) -> bool:
    """
    Composite check (PR 3 hardening RBAC, 2026-04-29):
    - Gerente da Superintendência (Setor "Superintendência" + Função "Gerente")
    - Assistente Administrativo do Controle (Setor "Controle" + Função
      "Assistente Administrativo")

    SSOT chamado tanto pela Policy class `CanAccessSolicitationApprovals`
    quanto por `user_has_policy("access_solicitation_approvals")`. Mudar
    a regra = mudar aqui e atualizar tests da matriz.

    PR 13 (2026-05-04): a checagem do composite Asst Admin Controle migrou
    para `helpers.user_is_assistente_administrativo_controle` (SSOT
    compartilhado com o gate de delegação de bloqueios).
    """
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    groups = user.groups  # type: ignore[attr-defined]
    is_gerente_super = (
        groups.filter(name="Gerente").exists()  # noqa: RBAC-composite-allowed
        and groups.filter(name="Superintendência").exists()  # noqa: RBAC-composite-allowed
    )
    if is_gerente_super:
        return True
    return user_is_assistente_administrativo_controle(user)


def user_can_delegate_availability_block(user: AbstractBaseUser | AnonymousUser | None) -> bool:
    """
    Composite check (PR 13 hardening RBAC, 2026-05-04): autoriza criar
    bloqueio em nome de outro Formador.

    Habilitado para:
    - Superuser (bypass)
    - Assistente Administrativo do Controle (composite Setor × Função)
    - DAT (via capability `manage_admin_registries` — exclusiva de DAT
      e superuser no seed atual)

    Outros perfis (Coord, Apoio, Gerente Sup, Gerente pedagógico,
    Diretoria, Controle puro, Formador) → False.

    Não cria capability nova: composição de helpers SSOT existentes.
    """
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    if user_is_assistente_administrativo_controle(user):
        return True
    return user_has_any_perm(user, "manage_admin_registries")


def user_can_delegate_deslocamento(user: AbstractBaseUser | AnonymousUser | None) -> bool:
    """
    Composite check (#1454, 2026-07-09): autoriza registrar deslocamento em
    nome de outro usuário.

    Habilitado para:
    - Superuser (bypass)
    - Perfis operacionais / suporte transversal:
      `operate_preagenda` (Controle) OU `view_all_availability` (Controle, DAT).

    Demais (Coordenador, Apoio, Gerente, Diretoria, Formador) → False; cada um
    registra apenas a própria viagem (self-service).

    Não cria capability nova: composição de capabilities SSOT existentes.
    """
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    return user_has_any_perm(user, "operate_preagenda", "view_all_availability")


def user_has_policy(user: AbstractBaseUser | AnonymousUser | None, key: str) -> bool:
    """
    True sse o usuário possui a policy identificada por `key`.

    Semântica (idêntica a `_PolicyPermission.has_permission` — esta função
    é a fonte única de verdade; `_PolicyPermission` delega para cá):

        anonymous / None         → False
        superuser                → True
        composite policy         → delega para helper específico (ex:
                                   `_user_has_solicitation_approvals`)
        key não na matriz        → False (fail-secure)
        caso geral               → user_has_any_perm(user, *capabilities) (OR)

    Aceita keys de ACCESS_POLICIES inteiro (públicas OU internas), porque
    a função é o universal "user holds this policy?" — exposição pública
    é responsabilidade de `resolve_public_policies` / endpoint, não da
    semântica subjacente.
    """
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    # Composite policies — semântica não cabe em "OR de capabilities".
    if key == "access_solicitation_approvals":
        return _user_has_solicitation_approvals(user)
    codenames = ACCESS_POLICIES.get(key)
    if not codenames:
        return False
    return user_has_any_perm(user, *codenames)


def resolve_public_policies(user: AbstractBaseUser | AnonymousUser | None) -> list[str]:
    """
    Retorna lista ordenada (alfabética) das `PUBLIC_POLICY_KEYS` que o
    usuário possui. Backend de `GET /api/me/policies/`.

    - Anonymous → [] (endpoint trata 401 antes via IsAuthenticated)
    - Superuser → todas as PUBLIC_POLICY_KEYS sorted
    - User regular → subset baseado em capabilities (OR semantics)

    Não vaza capability codenames — só keys do registro público.
    """
    return sorted(k for k in PUBLIC_POLICY_KEYS if user_has_policy(user, k))


__all__ = [
    "ACCESS_POLICIES",
    "PUBLIC_POLICY_KEYS",
    "_PolicyPermission",
    "user_can_delegate_availability_block",
    "user_has_policy",
    "resolve_public_policies",
    "CanAccessAuditLogs",
    "CanAccessSolicitationApprovals",
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
