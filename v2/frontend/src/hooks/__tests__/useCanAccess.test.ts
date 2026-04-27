/**
 * Tests: useCanAccess + computeAccess (Epic 3, Issue #1228)
 *
 * Camada de tradução semântica entre `PUBLIC_POLICY_KEYS` (Epic 4.4 backend)
 * e os componentes do frontend. Componentes consomem derived flags (ex:
 * `canAccessApprovals`); a origem (policy pública vs legacy flag) é detalhe
 * interno deste hook — pode migrar sem ripple.
 */

import { describe, test, expect } from 'vitest';
import { computeAccess } from '../useCanAccess';

describe('computeAccess.can()', () => {
  test('empty policies → can(anything) is false', () => {
    const access = computeAccess([]);
    expect(access.can('view_compras_dashboard')).toBe(false);
    expect(access.can('use_gcal')).toBe(false);
  });

  test('policy in list → can(policy) is true', () => {
    const access = computeAccess(['view_compras_dashboard', 'use_gcal']);
    expect(access.can('view_compras_dashboard')).toBe(true);
    expect(access.can('use_gcal')).toBe(true);
  });

  test('policy NOT in list → can(policy) is false', () => {
    const access = computeAccess(['view_compras_dashboard']);
    expect(access.can('use_gcal')).toBe(false);
    expect(access.can('access_audit_logs')).toBe(false);
  });

  test('policies array exposed via .policies (readonly contract)', () => {
    const input = ['view_compras_dashboard'];
    const access = computeAccess(input);
    expect(access.policies).toEqual(['view_compras_dashboard']);
  });
});

describe('computeAccess.canAccessApprovals — semantic translation layer', () => {
  test('no policy + no legacy → false', () => {
    const access = computeAccess([], {});
    expect(access.canAccessApprovals).toBe(false);
  });

  test('legacy canApproveSuper=true → true (current path)', () => {
    const access = computeAccess([], { canApproveSuper: true });
    expect(access.canAccessApprovals).toBe(true);
  });

  test('future public policy approve_solicitation present → true (Epic 4.6 ready)', () => {
    // Reservado para quando Epic 4.6 introduzir policy pública. Hoje a key
    // não existe em PUBLIC_POLICY_KEYS, mas o hook está pronto.
    const access = computeAccess(['approve_solicitation'], {});
    expect(access.canAccessApprovals).toBe(true);
  });

  test('future public policy approve_solicitation_batch present → true', () => {
    const access = computeAccess(['approve_solicitation_batch'], {});
    expect(access.canAccessApprovals).toBe(true);
  });

  test('legacy false + unrelated policy → false', () => {
    const access = computeAccess(['view_compras_dashboard'], { canApproveSuper: false });
    expect(access.canAccessApprovals).toBe(false);
  });
});

describe('computeAccess.canAccessBlocks — semantic translation', () => {
  test('view_all_availability policy → true', () => {
    const access = computeAccess(['view_all_availability'], {});
    expect(access.canAccessBlocks).toBe(true);
  });

  test('legacy canBloqueios=true → true (Formador owns own RD-02/03)', () => {
    const access = computeAccess([], { canBloqueios: true });
    expect(access.canAccessBlocks).toBe(true);
  });

  test('no policy + no legacy → false', () => {
    const access = computeAccess([], {});
    expect(access.canAccessBlocks).toBe(false);
  });
});

describe('computeAccess.canViewComprasDashboard — Onda 2 A2 consome policy', () => {
  test('public policy view_compras_dashboard → true', () => {
    const access = computeAccess(['view_compras_dashboard'], {});
    expect(access.canViewComprasDashboard).toBe(true);
  });

  test('legacy canDashboardCompras=true → true (fallback durante transição)', () => {
    const access = computeAccess([], { canDashboardCompras: true });
    expect(access.canViewComprasDashboard).toBe(true);
  });

  test('sem policy + sem legacy → false', () => {
    const access = computeAccess([], {});
    expect(access.canViewComprasDashboard).toBe(false);
  });

  test('legacy false + policy ausente → false', () => {
    const access = computeAccess(['use_gcal'], { canDashboardCompras: false });
    expect(access.canViewComprasDashboard).toBe(false);
  });
});

describe('computeAccess.canCreateSolicitation — legacy-only today', () => {
  test('legacy canCoordenador=true → true', () => {
    const access = computeAccess([], { canCoordenador: true });
    expect(access.canCreateSolicitation).toBe(true);
  });

  test('no legacy → false (no public policy maps to this today)', () => {
    const access = computeAccess(['view_compras_dashboard'], {});
    expect(access.canCreateSolicitation).toBe(false);
  });
});
