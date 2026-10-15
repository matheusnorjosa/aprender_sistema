/**
 * useCapabilities — "o que o usuário pode fazer" (Issue #1269, RBAC 3.1).
 *
 * Deriva capabilities EXCLUSIVAMENTE de `policies` (subset das PUBLIC_POLICY_KEYS
 * do backend, via `GET /api/me/policies/`). Sem organograma. É a fonte de verdade de
 * autorização no frontend (PR 7 das permissões: `usePermissions`/`useCanAccess` saíram);
 * o backend permanece autoritativo. Os componentes leem via `useAcesso().caps`.
 *
 * Para "quem é o usuário" (setor/função, display) use `useIdentity`.
 *
 * Cada flag `can*` espelha 1:1 uma policy key. Ao adicionar uma policy pública nova
 * no backend, adicione a flag correspondente aqui + um caso no teste de completude.
 */
import { useMemo } from 'react';

export interface Capabilities {
  /** Subset das PUBLIC_POLICY_KEYS que o usuário possui. */
  readonly policies: readonly string[];
  /** Match exato contra uma policy key (escape hatch p/ keys sem flag nomeada). */
  can: (key: string) => boolean;

  canAccessAuditLogs: boolean;
  canAccessApprovals: boolean;
  canCreateSolicitation: boolean;
  canManageSolicitacaoStatus: boolean;
  canViewComprasDashboard: boolean;
  canViewComprasPendencias: boolean;
  canViewComprasStats: boolean;
  canViewOverviewDashboard: boolean;
  canViewMapMetrics: boolean;
  canViewReports: boolean;
  canUseGcal: boolean;
  canViewAllAvailability: boolean;
  canImportAvailabilityBlocks: boolean;
  canImportCompras: boolean;
  canImportGenericSpreadsheet: boolean;
  canManageAdminRegistries: boolean;
  canManageInternalActions: boolean;
  canManagePurchasesAndMaterials: boolean;
  // Policies de seção de menu (#1589). Consumidas pelo AppSidebar desde #1270.
  canAccessControleSection: boolean;
  canViewTeamDashboard: boolean;
  canViewGcalDashboard: boolean;
  // Apoio de Coordenação publica no Google Agenda os eventos aprovados do PRÓPRIO
  // setor (#1656) — distinto de `canUseGcal` (operação global da Pré-agenda).
  canPublishSetorSolicitacao: boolean;
  // PR 7 das permissões (15/10/2026). Telas de escopo: o servidor soma view_all_availability,
  // o grupo e o vínculo de gestão vigente (a fórmula que o front aplicava).
  canAccessMonthlyAvailability: boolean;
  canAccessAvailabilityBlocks: boolean;
  canAccessTravel: boolean;
  // Botões: excluir plano de formações e Nova Solicitação sem compra.
  canExecuteRestrictedOperations: boolean;
  canCreateSolicitationWithoutPurchase: boolean;
}

/** Versão pura (sem React) — usada em tests e call sites sem render. */
export function computeCapabilities(policies: readonly string[]): Capabilities {
  const policySet = new Set(policies);
  const can = (key: string): boolean => policySet.has(key);

  return {
    policies,
    can,
    canAccessAuditLogs: can('access_audit_logs'),
    canAccessApprovals: can('access_solicitation_approvals'),
    canCreateSolicitation: can('create_solicitation'),
    canManageSolicitacaoStatus: can('manage_solicitacao_status'),
    canViewComprasDashboard: can('view_compras_dashboard'),
    canViewComprasPendencias: can('view_compras_pendencias'),
    canViewComprasStats: can('view_compras_stats'),
    canViewOverviewDashboard: can('view_overview_dashboard'),
    canViewMapMetrics: can('view_map_metrics'),
    canViewReports: can('view_reports'),
    canUseGcal: can('use_gcal'),
    canViewAllAvailability: can('view_all_availability'),
    canImportAvailabilityBlocks: can('import_availability_blocks'),
    canImportCompras: can('import_compras'),
    canImportGenericSpreadsheet: can('import_generic_spreadsheet'),
    canManageAdminRegistries: can('manage_admin_registries'),
    canManageInternalActions: can('manage_internal_actions'),
    canManagePurchasesAndMaterials: can('manage_purchases_and_materials'),
    canAccessControleSection: can('access_controle_section'),
    canViewTeamDashboard: can('view_team_dashboard'),
    canViewGcalDashboard: can('view_gcal_dashboard'),
    canPublishSetorSolicitacao: can('publish_setor_solicitacao'),
    canAccessMonthlyAvailability: can('access_monthly_availability'),
    canAccessAvailabilityBlocks: can('access_availability_blocks'),
    canAccessTravel: can('access_travel'),
    canExecuteRestrictedOperations: can('execute_restricted_operations'),
    canCreateSolicitationWithoutPurchase: can('create_solicitation_without_purchase'),
  };
}

/** Hook React memoizado por `policies`. */
export function useCapabilities(policies: readonly string[]): Capabilities {
  return useMemo(() => computeCapabilities(policies), [policies]);
}
