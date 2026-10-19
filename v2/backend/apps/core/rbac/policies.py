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

from collections.abc import Set as AbstractSet
from typing import Any, Final, Literal

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from django.db.models import Q
from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.core.models import EquipeGerencia

# Side-effect import: garante o monkey-patch de OR/AND/NOT.__call__ aplicado
# em apps.core.rbac.permissions (necessário para `CanA() | CanB()` funcionar
# em `permission_classes`). Não usamos HasPerm aqui, mas precisamos que o
# patch esteja ativo antes do primeiro uso de composition.
from apps.core.rbac import permissions as _rbac_permissions  # noqa: F401
from apps.core.rbac.helpers import (
    GERENCIA_APROVADORA_NOME,
    fluxo_super_fora_da_superintendencia,
    user_has_any_perm,
    user_is_gerente_superintendencia,
)

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
# (ex: vínculo GERENTE em g1 ou capacidade). A lógica vive em helpers dedicados despachados por
# `user_has_policy`. `access_solicitation_approvals` tem frozenset() vazio como
# sentinela; as telas de escopo (`TELAS_DE_ESCOPO`) listam a capacidade que também abre.
# Tests que assumem "frozenset não-vazio" devem excluir essas keys.
COMPOSITE_POLICY_KEYS: Final[frozenset[str]] = frozenset(
    {
        "access_solicitation_approvals",
        "access_monthly_availability",
        "access_availability_blocks",
        "access_travel",
    }
)

# Telas de escopo (PR 7 das permissões, 15/10/2026): Grade Mensal, Bloqueios e Deslocamentos.
# Abre a tela: a capacidade em ACCESS_POLICIES (view_all_availability) OU um dos grupos de setor
# abaixo OU um dos papéis abaixo, vigente em gerência ativa (`EquipeGerencia.gerencias_com_papel`).
# PR 8: o papel substitui o grupo de função e o antigo "vínculo de gestão" (G/C/A). PR 9: Grade e
# Deslocamentos usam os mesmos papéis do alcance da API (`EquipeGerencia.PAPEIS_DE_ATUACAO`).
TELAS_DE_ESCOPO: Final[dict[str, tuple[frozenset[str], frozenset[str]]]] = {
    # chave: (setores, papéis)
    "access_monthly_availability": (
        frozenset({"Controle", "DAT"}),
        EquipeGerencia.PAPEIS_DE_ATUACAO,
    ),
    "access_availability_blocks": (
        frozenset({"Controle", "DAT"}),
        EquipeGerencia.PAPEIS_DE_ATUACAO | {"FORMADOR"},
    ),
    "access_travel": (
        frozenset({"Controle", "DAT"}),
        EquipeGerencia.PAPEIS_DE_ATUACAO,
    ),
}


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
    # Criação de solicitação (motivo legítimo: operar) — Coordenador / Apoio de
    # Coordenação / Gerente (seed). Single-cap elevada a policy pública para o
    # frontend consumir o mesmo gate de HasPerm("create_solicitation") (#1262).
    "create_solicitation": frozenset({"create_solicitation"}),
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
    # Publish/preview/resync/cancel GCal ESCOPADO por setor (#1656 Feature 2) —
    # Apoio de Coordenação. Cap dedicada de propósito: NÃO estende `use_gcal`
    # (que porteia views_gcal/* batch, sem escopo por id). O alcance de objeto
    # vem do tier aditivo em `scope_solicitacoes`; a edição continua barrada por
    # `user_can_access_solicitacao` (inalterado).
    "publish_setor_solicitacao": frozenset({"publish_setor_solicitacao"}),
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
    # CRUD de ações internas / notificações (motivo legítimo: operar). Seed = 0
    # grupos (só superuser bypassa); elevada a policy pública para #1263
    # (canAcoesInternas consome manage_internal_actions em vez do organograma).
    "manage_internal_actions": frozenset({"manage_internal_actions"}),
    # --- Aprovação de solicitações (PR 3 hardening RBAC, 2026-04-29) ---
    # Policy COMPOSITE: a semântica não cabe em "OR de capabilities" porque
    # soma o vínculo GERENTE em g1 (com escopo) à capacidade `approve_solicitation`
    # (DAT e Controle pelo pacote, PR 11). Frozenset vazio é sentinela —
    # `user_has_policy` trata a key via `_user_has_solicitation_approvals`.
    "access_solicitation_approvals": frozenset(),
    # Menu policy-only (#1589, destrava #1270). Paridade com gates legacy do
    # frontend (usePermissions.ts): as capabilities-âncora abaixo são exclusivas
    # de um setor no seed (functional_permissions_seed.py), então o OR reproduz
    # exatamente os setores dos gates `can*`.
    #   canControle        = Controle          -> operate_preagenda|run_daily_operations
    #   canDashboardEquipe = Diretoria|DAT      -> supervise_operations|manage_admin_registries
    #   canDashboardGcal   = Diretoria|DAT|Controle
    "access_controle_section": frozenset({"operate_preagenda", "run_daily_operations"}),
    "view_team_dashboard": frozenset({"supervise_operations", "manage_admin_registries"}),
    # PR 10 (decisão do dono de 02/10, nº 13): a Diretoria (`supervise_operations`) sai do painel do Google.
    "view_gcal_dashboard": frozenset({"manage_admin_registries", "operate_preagenda", "run_daily_operations"}),
    # --- Telas de escopo (PR 7, 15/10/2026): composite, ver TELAS_DE_ESCOPO ---
    "access_monthly_availability": frozenset({"view_all_availability"}),
    "access_availability_blocks": frozenset({"view_all_availability"}),
    "access_travel": frozenset({"view_all_availability"}),
    # --- Botões (PR 7): a capacidade de mesmo nome, exposta para o front ---
    # Excluir plano de formações (o destroy exige HasPerm("execute_restricted_operations")).
    "execute_restricted_operations": frozenset({"execute_restricted_operations"}),
    # Nova Solicitação sem compra (regra da compra, 14/10/2026; 0 grupos no seed).
    "create_solicitation_without_purchase": frozenset({"create_solicitation_without_purchase"}),
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


class CanPublishSetorSolicitacao(_PolicyPermission):
    policy = "publish_setor_solicitacao"


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


class CanCreateSolicitation(_PolicyPermission):
    policy = "create_solicitation"


class CanAccessControleSection(_PolicyPermission):
    policy = "access_controle_section"


class CanViewTeamDashboard(_PolicyPermission):
    policy = "view_team_dashboard"


class CanViewGcalDashboard(_PolicyPermission):
    policy = "view_gcal_dashboard"


class CanManageInternalActions(_PolicyPermission):
    policy = "manage_internal_actions"


class CanAccessMonthlyAvailability(_PolicyPermission):
    policy = "access_monthly_availability"


class CanAccessAvailabilityBlocks(_PolicyPermission):
    policy = "access_availability_blocks"


class CanAccessTravel(_PolicyPermission):
    policy = "access_travel"


class CanExecuteRestrictedOperations(_PolicyPermission):
    policy = "execute_restricted_operations"


class CanCreateSolicitationWithoutPurchase(_PolicyPermission):
    policy = "create_solicitation_without_purchase"


class CanAccessSolicitationApprovals(_PolicyPermission):
    """
    Policy composta de aprovação de solicitações (PR 3, 2026-04-29; PR B1, 2026-09-29; PR 11, 2026-10-17).

    Habilitada para (SSOT `solicitation_approval_basis`, 3 bases):
    - superuser
    - Gerente da Superintendência por VÍNCULO: EquipeGerencia vigente com papel
      GERENTE na gerência `GERENCIA_APROVADORA_NOME` (sem depender de grupo)
    - a capacidade `approve_solicitation`: o DAT (pacote ADMIN_OPERACIONAL, PR 10) e o Controle
      (pacote CONTROLE, PR 11), pelo vínculo EQUIPE/GERENTE. Nenhum grupo a tem.

    Implementação composite (não OR de capabilities): a semântica vive em
    `_user_has_solicitation_approvals` e é compartilhada com
    `user_has_policy` para que `/api/me/policies/` exponha o mesmo gate
    consumido pelos 4 endpoints de aprovação.
    """

    policy = "access_solicitation_approvals"
    message = "Apenas a gerência da Superintendência, o DAT ou o Controle podem aprovar solicitações."

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
        "create_solicitation",
        "manage_solicitacao_status",
        "view_compras_dashboard",
        "view_compras_pendencias",
        "view_compras_stats",
        "view_overview_dashboard",
        "view_map_metrics",
        "view_reports",
        "use_gcal",
        "publish_setor_solicitacao",
        "view_all_availability",
        "import_availability_blocks",
        "import_compras",
        "import_generic_spreadsheet",
        "manage_admin_registries",
        "manage_internal_actions",
        "manage_purchases_and_materials",
        "access_controle_section",
        "view_team_dashboard",
        "view_gcal_dashboard",
        # PR 7 das permissões (15/10/2026): o front decide menu, rotas e botões só por policy.
        # Chave nova aparece no rbac_diff do deploy como `+ policies` (DEPLOY_CHECKLIST §8, D22).
        "access_monthly_availability",
        "access_availability_blocks",
        "access_travel",
        "execute_restricted_operations",
        "create_solicitation_without_purchase",
    }
)


# ============================================================================
# Helpers (SSOT da semântica de Policy — usado por View, tests, admin futuro)
# ============================================================================


# PR 11 (17/10/2026): 3 bases. Os rótulos `asst_admin_controle` e `grupo_superintendencia_gerente`
# (bases por grupo, até o PR 11) seguem nos AuditLogs já gravados; nenhum leitor depende do valor.
SolicitationApprovalBasis = Literal[
    "superuser",
    "gerente_superintendencia",
    "capacidade_aprovar",
]


def solicitation_approval_basis(
    user: AbstractBaseUser | AnonymousUser | None,
    *,
    capacidades: AbstractSet[str] | None = None,
) -> SolicitationApprovalBasis | None:
    """
    SSOT de QUEM aprova/reprova solicitações e POR QUÊ (PR B1, 2026-09-29; PR 11, 2026-10-17).

    Retorna a base da autoridade (gravada em `AuditLog.details.autoridade`) ou
    None quando o usuário não aprova. Ordem de precedência:

    1. `superuser`
    2. `gerente_superintendencia` — vínculo EquipeGerencia VIGENTE com papel GERENTE
       na gerência `GERENCIA_APROVADORA_NOME` (sem depender de grupo Django). Com escopo
    3. `capacidade_aprovar` — a capacidade `approve_solicitation`. Nenhum grupo a tem (seed e
       migration 0126): vem do pacote do perfil da gerência, pelo vínculo EQUIPE/GERENTE vigente:
       ADMIN_OPERACIONAL (DAT, PR 10) e CONTROLE (D1 de 06/10, PR 11). Sem escopo: decide qualquer
       gerência e fluxo

    Nenhum grupo dá o poder de aprovar: as bases por grupo (par Controle + Assistente Administrativo e
    par Superintendência + Gerente) saíram no PR 11.

    `capacidades`: só para o simulador `rbac_diff` (a base 3 lê esse conjunto em vez do cache).
    """
    if not user or not getattr(user, "is_authenticated", False):
        return None
    if getattr(user, "is_superuser", False):
        return "superuser"
    if user_is_gerente_superintendencia(user):
        return "gerente_superintendencia"
    return _base_de_aprovacao_fora_do_vinculo(user, capacidades=capacidades)


def _base_de_aprovacao_fora_do_vinculo(
    user: AbstractBaseUser | AnonymousUser | None,
    *,
    capacidades: AbstractSet[str] | None = None,
) -> SolicitationApprovalBasis | None:
    """Base 3 de `solicitation_approval_basis` (sem superuser nem o vínculo GERENTE em g1): a capacidade."""
    if capacidades is not None:
        tem_capacidade = "approve_solicitation" in capacidades
    else:
        tem_capacidade = user_has_any_perm(user, "approve_solicitation")
    return "capacidade_aprovar" if tem_capacidade else None


# ----------------------------------------------------------------------------
# Regra do dono (30/09): escopo da aprovadora por vínculo
# ----------------------------------------------------------------------------
# A base `gerente_superintendencia` só aprova/reprova, edita, exclui e cria solicitação de projeto
# do fluxo SUPER da gerência Superintendência (g1). Ver não muda. A capacidade de aprovar (DAT e
# Controle) e o superuser não têm escopo. O predicado é um só (`projeto_no_escopo_da_superintendencia`); os Q abaixo são a
# mesma regra em SQL, para o lote e a Home (paridade coberta por teste).

ESCOPO_SUPERINTENDENCIA_PROJETO_Q: Final = Q(fluxo="SUPER", gerencia__nome=GERENCIA_APROVADORA_NOME)
ESCOPO_SUPERINTENDENCIA_Q: Final = Q(projeto__fluxo="SUPER", projeto__gerencia__nome=GERENCIA_APROVADORA_NOME)


def projeto_no_escopo_da_superintendencia(projeto: Any) -> bool:
    """SSOT: projeto do fluxo SUPER da gerência Superintendência (g1)?

    Fail-closed: projeto None, fluxo ≠ SUPER, sem gerência ou gerência de nome parecido → False.
    `Gerencia.ativo` NÃO entra, pela mesma razão do vínculo (`user_is_gerente_superintendencia`).
    """
    fluxo = getattr(projeto, "fluxo", None)
    return fluxo == "SUPER" and not fluxo_super_fora_da_superintendencia(fluxo, getattr(projeto, "gerencia", None))


def aprovadora_restrita_a_superintendencia(user: AbstractBaseUser | AnonymousUser | None) -> bool:
    """A única base de aprovação do usuário é o vínculo GERENTE em g1?

    Então ela só decide solicitação no escopo (`projeto_no_escopo_da_superintendencia`). Superuser e a
    capacidade de aprovar (DAT e Controle) não são restringidos.
    """
    if not user or not getattr(user, "is_authenticated", False) or getattr(user, "is_superuser", False):
        return False
    return user_is_gerente_superintendencia(user) and _base_de_aprovacao_fora_do_vinculo(user) is None


def solicitation_approval_basis_for(
    user: AbstractBaseUser | AnonymousUser | None,
    solicitacao: Any,
) -> SolicitationApprovalBasis | None:
    """Base de aprovação do usuário para ESTA solicitação (vai para `AuditLog.details.autoridade`).

    Mesma precedência de `solicitation_approval_basis`, mas o vínculo GERENTE em g1 só vale no escopo
    da Superintendência. Fora dele vale a próxima base (a capacidade) ou None, e None com
    base global não nula = fora do escopo. `solicitacao=None` responde pelo "fora do escopo".
    """
    basis = solicitation_approval_basis(user)
    if basis != "gerente_superintendencia":
        return basis
    if projeto_no_escopo_da_superintendencia(getattr(solicitacao, "projeto", None)):
        return basis
    return _base_de_aprovacao_fora_do_vinculo(user)


def _user_has_solicitation_approvals(
    user: AbstractBaseUser | AnonymousUser | None,
    capacidades: AbstractSet[str] | None = None,
) -> bool:
    """
    Tem autoridade de aprovação? (`solicitation_approval_basis(user) is not None`).

    SSOT chamado tanto pela Policy class `CanAccessSolicitationApprovals`
    quanto por `user_has_policy("access_solicitation_approvals")`. Mudar
    a regra = mudar `solicitation_approval_basis` e atualizar tests da matriz.
    """
    return solicitation_approval_basis(user, capacidades=capacidades) is not None


def _abre_tela_de_escopo(
    user: AbstractBaseUser | AnonymousUser,
    key: str,
    capacidades: AbstractSet[str] | None,
) -> bool:
    """Grade, Bloqueios ou Deslocamentos (`TELAS_DE_ESCOPO`): capacidade OU grupo de setor OU papel vigente.

    Sem bypass de superuser (`user_has_policy` decide antes). `capacidades` vale só para a parte da
    capacidade (simulador `rbac_diff`); grupos e vínculos são os de hoje.
    """
    codenames = ACCESS_POLICIES[key]
    if capacidades is not None:
        if not codenames.isdisjoint(capacidades):
            return True
    elif user_has_any_perm(user, *codenames):
        return True
    setores_da_tela, papeis_da_tela = TELAS_DE_ESCOPO[key]
    if user.groups.filter(name__in=setores_da_tela).exists():
        return True
    return bool(EquipeGerencia.gerencias_com_papel(user, papeis_da_tela))


def user_can_delegate_availability_block(user: AbstractBaseUser | AnonymousUser | None) -> bool:
    """
    Autoriza criar bloqueio em nome de outro Formador e editar ou apagar bloqueio alheio
    (PR 13 hardening RBAC, 2026-05-04; base nova no PR 8 das permissões, 15/10/2026).

    Habilitado para:
    - Superuser (bypass)
    - `operate_preagenda` (Controle, pelo grupo ou pelo pacote do perfil CONTROLE)
    - `manage_admin_registries` (DAT, pelo grupo ou pelo pacote do ADMIN_OPERACIONAL)

    Antes do PR 8 a base era o par Controle × Assistente Administrativo: a função saiu da regra
    (o cargo não dá poder) e o Controle puro passou a delegar (O8-7). Demais → False.
    """
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    return user_has_any_perm(user, "operate_preagenda", "manage_admin_registries")


# P16 (PR 8 das permissões; decisão do dono O8-5, 15/10/2026): papéis que registram o deslocamento
# do formador da própria gerência.
PAPEIS_QUE_DELEGAM_DESLOCAMENTO: Final[frozenset[str]] = frozenset({"GERENTE", "COORDENADOR"})


def user_delega_deslocamento_de_qualquer_um(user: AbstractBaseUser | AnonymousUser | None) -> bool:
    """Delegação sem alvo fixo (#1454): superuser, `operate_preagenda` (Controle) ou `view_all_availability`."""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    return user_has_any_perm(user, "operate_preagenda", "view_all_availability")


def gerencias_que_delegam_deslocamento(user: AbstractBaseUser | AnonymousUser | None) -> set[int]:
    """P16: gerências onde `user` é GERENTE ou COORDENADOR vigente (registra o deslocamento dos formadores)."""
    if not user or not getattr(user, "is_authenticated", False):
        return set()
    return EquipeGerencia.gerencias_com_papel(user, PAPEIS_QUE_DELEGAM_DESLOCAMENTO)


def user_can_delegate_deslocamento(
    user: AbstractBaseUser | AnonymousUser | None,
    alvo: Any = None,
) -> bool:
    """
    Autoriza registrar, editar ou apagar deslocamento em nome de outro usuário (#1454, 2026-07-09).

    Habilitado para:
    - qualquer alvo: `user_delega_deslocamento_de_qualquer_um` (superuser, Controle, DAT);
    - P16 (PR 8): GERENTE ou COORDENADOR vigente, para `alvo` com vínculo FORMADOR vigente numa
      gerência onde ela tem um desses papéis (`gerencias_que_delegam_deslocamento`). Sem `alvo` → False.

    Demais (Apoio, Diretoria, Formador) → False; cada um registra a própria viagem.
    """
    if user_delega_deslocamento_de_qualquer_um(user):
        return True
    if alvo is None:
        return False
    gerencias = gerencias_que_delegam_deslocamento(user)
    return bool(gerencias & EquipeGerencia.gerencias_com_papel(alvo, {"FORMADOR"}))


def user_has_policy(
    user: AbstractBaseUser | AnonymousUser | None,
    key: str,
    *,
    capacidades: AbstractSet[str] | None = None,
) -> bool:
    """
    True sse o usuário possui a policy identificada por `key`.

    `capacidades`: só para o simulador `rbac_diff` (somente leitura). Quando vem, o caso geral
    usa esse conjunto no lugar das capacidades de hoje (que passam pelo cache). None = hoje.

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
        return _user_has_solicitation_approvals(user, capacidades)
    if key in TELAS_DE_ESCOPO:
        return _abre_tela_de_escopo(user, key, capacidades)
    codenames = ACCESS_POLICIES.get(key)
    if not codenames:
        return False
    if capacidades is not None:
        return not codenames.isdisjoint(capacidades)
    return user_has_any_perm(user, *codenames)


def resolve_public_policies(
    user: AbstractBaseUser | AnonymousUser | None,
    *,
    capacidades: AbstractSet[str] | None = None,
) -> list[str]:
    """
    Retorna lista ordenada (alfabética) das `PUBLIC_POLICY_KEYS` que o
    usuário possui. Backend de `GET /api/me/policies/`.

    - Anonymous → [] (endpoint trata 401 antes via IsAuthenticated)
    - Superuser → todas as PUBLIC_POLICY_KEYS sorted
    - User regular → subset baseado em capabilities (OR semantics)

    Não vaza capability codenames — só keys do registro público.
    `capacidades`: ver `user_has_policy` (simulador `rbac_diff`).
    """
    return sorted(k for k in PUBLIC_POLICY_KEYS if user_has_policy(user, k, capacidades=capacidades))


def can_admin_mutate_target(
    actor: AbstractBaseUser | AnonymousUser | None,
    target: AbstractBaseUser | AnonymousUser | None,
    action: str | None = None,
) -> bool:
    """
    SSOT ator×alvo (M07-01/M07-02, #1616/#1617; S4 do PR 10): um admin não-superuser pode
    mutar `target` (senha, cadastro, is_active, delete/anonimizar)?

    Regra (decisão do dono de 16/10/2026, que substitui a de 14/10 e a proteção da aprovadora do M07):
    - superuser-ator   → True  (bypass total; mantém P0-0/P0-1)
    - target superuser → False (Tier-0; a queryset da view já dá 404 antes)
    - demais           → True  (o DAT administra todas as contas: outro DAT, Apoio, Controle e as
                                aprovadoras)

    O que segura a segregação (CP-02) sem a proteção por alvo: toda alteração de conta grava AuditLog
    na mesma transação, a senha dada por outra pessoa liga `deve_trocar_senha`, e por 30 dias quem
    alterou a conta do autor não decide as solicitações dele, nem quem teve a conta alterada pelo autor
    (PA-02, segregação por histórico, nos dois sentidos).

    A contrapartida para a dona da conta (F1 do scan de segurança de 16/10/2026): a senha redefinida
    por outra pessoa grava quem e quando, e o próximo acesso dela mostra "Sua senha foi redefinida por
    <rótulo> em dd/mm/aaaa" (`/api/me/` → `aviso_senha_redefinida`). O aviso NÃO protege contra quem
    entra na conta antes da dona: quem redefiniu e entrou primeiro vê o aviso e o apaga ao trocar a
    senha, e a redefinição seguinte grava por cima. Para esse caso o `/api/me/` traz também
    `redefinicoes_senha`, as redefinições por outra pessoa dos últimos 30 dias lidas do AuditLog
    (`auditar_reset_senha`), que a troca de senha não apaga; a tela de troca e o Perfil as listam.
    Nada disso impede a tomada: a dona só fica sabendo quando recupera o acesso.

    `action` fica reservado para o épico #1656 (escopo por operação).
    """
    if getattr(actor, "is_superuser", False):
        return True
    return not getattr(target, "is_superuser", False)


__all__ = [
    "ACCESS_POLICIES",
    "ESCOPO_SUPERINTENDENCIA_PROJETO_Q",
    "ESCOPO_SUPERINTENDENCIA_Q",
    "PUBLIC_POLICY_KEYS",
    "TELAS_DE_ESCOPO",
    "_PolicyPermission",
    "aprovadora_restrita_a_superintendencia",
    "can_admin_mutate_target",
    "projeto_no_escopo_da_superintendencia",
    "solicitation_approval_basis",
    "solicitation_approval_basis_for",
    "user_can_delegate_availability_block",
    "user_can_delegate_deslocamento",
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
    "CanPublishSetorSolicitacao",
    "CanViewAllAvailability",
    "CanImportAvailabilityBlocks",
    "CanImportCompras",
    "CanImportGenericSpreadsheet",
    "CanManageAdminRegistries",
    "CanManagePurchasesAndMaterials",
    "CanAccessMonthlyAvailability",
    "CanAccessAvailabilityBlocks",
    "CanAccessTravel",
    "CanExecuteRestrictedOperations",
    "CanCreateSolicitationWithoutPurchase",
]
