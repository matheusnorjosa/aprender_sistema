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

describe('computeAccess.canAccessApprovals — policy-only (PR 10 hardening RBAC, 2026-04-30)', () => {
  test('sem policy → false', () => {
    const access = computeAccess([]);
    expect(access.canAccessApprovals).toBe(false);
  });

  test('policy access_solicitation_approvals presente → true', () => {
    const access = computeAccess(['access_solicitation_approvals']);
    expect(access.canAccessApprovals).toBe(true);
  });

  test('policy unrelated → false', () => {
    const access = computeAccess(['view_compras_dashboard']);
    expect(access.canAccessApprovals).toBe(false);
  });

  test('canAccessApprovals não depende de legacy can_approve_super', () => {
    // Backend continua expondo `can_approve_super` no payload de /api/me/,
    // mas o hook não consulta mais essa flag. Decisão é exclusivamente da
    // policy pública — `LegacyAccessFlags` removeu o campo.
    const access = computeAccess([], { canBloqueios: true, canCoordenador: true });
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
