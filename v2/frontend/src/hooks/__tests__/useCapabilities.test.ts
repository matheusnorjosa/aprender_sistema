/**
 * Tests: useCapabilities + computeCapabilities (Issue #1269, RBAC 3.1).
 *
 * `useCapabilities` responde "o que o usuário pode fazer", derivado
 * EXCLUSIVAMENTE de `policies` (subset das PUBLIC_POLICY_KEYS do backend). Sem
 * fallback legacy, sem organograma. É a fonte de verdade de autorização no
 * frontend (o backend continua autoritativo).
 */
import { describe, test, expect } from 'vitest';
import { computeCapabilities } from '../useCapabilities';

describe('computeCapabilities — can() genérico', () => {
  test('policies vazias → can(qualquer) é false', () => {
    const caps = computeCapabilities([]);
    expect(caps.can('access_solicitation_approvals')).toBe(false);
    expect(caps.can('create_solicitation')).toBe(false);
  });

  test('policy presente → can(policy) true; ausente → false', () => {
    const caps = computeCapabilities(['use_gcal']);
    expect(caps.can('use_gcal')).toBe(true);
    expect(caps.can('view_reports')).toBe(false);
  });

  test('policies expostas via .policies', () => {
    expect(computeCapabilities(['use_gcal']).policies).toEqual(['use_gcal']);
  });
});

describe('computeCapabilities — flags nomeadas por ator', () => {
  test('anônimo (sem policies) → todas as capabilities false', () => {
    const caps = computeCapabilities([]);
    expect(caps.canAccessApprovals).toBe(false);
    expect(caps.canCreateSolicitation).toBe(false);
    expect(caps.canManageInternalActions).toBe(false);
    expect(caps.canViewOverviewDashboard).toBe(false);
    expect(caps.canViewComprasDashboard).toBe(false);
    expect(caps.canUseGcal).toBe(false);
  });

  test('Coordenador → canCreateSolicitation', () => {
    const caps = computeCapabilities(['create_solicitation']);
    expect(caps.canCreateSolicitation).toBe(true);
    expect(caps.canAccessApprovals).toBe(false);
  });

  test('Aprovador → canAccessApprovals', () => {
    const caps = computeCapabilities(['access_solicitation_approvals']);
    expect(caps.canAccessApprovals).toBe(true);
    expect(caps.canCreateSolicitation).toBe(false);
  });

  test('DAT → imports + registries + compras dashboard', () => {
    const caps = computeCapabilities([
      'import_availability_blocks',
      'import_compras',
      'import_generic_spreadsheet',
      'manage_admin_registries',
      'view_compras_dashboard',
    ]);
    expect(caps.canImportAvailabilityBlocks).toBe(true);
    expect(caps.canImportCompras).toBe(true);
    expect(caps.canImportGenericSpreadsheet).toBe(true);
    expect(caps.canManageAdminRegistries).toBe(true);
    expect(caps.canViewComprasDashboard).toBe(true);
    expect(caps.canViewOverviewDashboard).toBe(false);
  });

  test('Diretoria → dashboards de visão geral/compras/mapa', () => {
    const caps = computeCapabilities([
      'view_overview_dashboard',
      'view_compras_dashboard',
      'view_map_metrics',
    ]);
    expect(caps.canViewOverviewDashboard).toBe(true);
    expect(caps.canViewComprasDashboard).toBe(true);
    expect(caps.canViewMapMetrics).toBe(true);
    expect(caps.canManageInternalActions).toBe(false);
  });

  test('cada uma das 18 flags reflete exatamente sua policy', () => {
    const CASES: ReadonlyArray<readonly [keyof ReturnType<typeof computeCapabilities>, string]> = [
      ['canAccessAuditLogs', 'access_audit_logs'],
      ['canAccessApprovals', 'access_solicitation_approvals'],
      ['canCreateSolicitation', 'create_solicitation'],
      ['canManageSolicitacaoStatus', 'manage_solicitacao_status'],
      ['canViewComprasDashboard', 'view_compras_dashboard'],
      ['canViewComprasPendencias', 'view_compras_pendencias'],
      ['canViewComprasStats', 'view_compras_stats'],
      ['canViewOverviewDashboard', 'view_overview_dashboard'],
      ['canViewMapMetrics', 'view_map_metrics'],
      ['canViewReports', 'view_reports'],
      ['canUseGcal', 'use_gcal'],
      ['canViewAllAvailability', 'view_all_availability'],
      ['canImportAvailabilityBlocks', 'import_availability_blocks'],
      ['canImportCompras', 'import_compras'],
      ['canImportGenericSpreadsheet', 'import_generic_spreadsheet'],
      ['canManageAdminRegistries', 'manage_admin_registries'],
      ['canManageInternalActions', 'manage_internal_actions'],
      ['canManagePurchasesAndMaterials', 'manage_purchases_and_materials'],
    ];
    for (const [flag, policy] of CASES) {
      const caps = computeCapabilities([policy]);
      expect(caps[flag], `${String(flag)} deve refletir ${policy}`).toBe(true);
    }
  });
});
