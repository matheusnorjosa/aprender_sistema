/**
 * RBAC Living Matrix — frontend tests parametrizados (Onda 3, 2026-04-27).
 *
 * Espelha `apps/core/rbac/matrix.py` no domínio frontend: para cada ator,
 * declara quais policies ele recebe via `GET /api/me/policies/` e quais
 * derived flags do `useCanAccess` ele deve obter.
 *
 * Não renderiza componente (evita render gigante de AppSidebar). Foca em
 * `computeAccess` puro — match exato com a fonte do `useCanAccess` (mesma
 * função usada por hook + tests).
 *
 * Falha indica:
 * - Mudança em derived flag sem atualizar matriz
 * - Quebra de simetria com backend (ex: DAT recebe view_compras_dashboard
 *   no /api/me/policies/ mas frontend não reflete)
 * - Drift entre seed/policies e UI
 */

import { describe, test, expect } from 'vitest';

import { computeAccess, type LegacyAccessFlags, type AccessState } from '../useCanAccess';

// ============================================================================
// Snapshot por ator: quais policies vêm do backend e quais legacy flags
// resultam dos setores/funções do user. Espelha doc §3 e ACCESS_MATRIX backend.
// ============================================================================

interface ActorSnapshot {
  actor: string;
  /** Policies que o backend retorna em /api/me/policies/ (subset de PUBLIC_POLICY_KEYS) */
  policies: string[];
  /** Legacy flags computadas por usePermissions(user) para esse ator */
  legacy: LegacyAccessFlags;
  /** Derived flags esperadas em useCanAccess(policies, legacy) */
  expected: Pick<
    AccessState,
    'canAccessApprovals' | 'canAccessBlocks' | 'canCreateSolicitation' | 'canViewComprasDashboard'
  >;
}

const ACTORS: ActorSnapshot[] = [
  {
    actor: 'Superuser',
    // Superuser recebe TODAS as PUBLIC_POLICY_KEYS via /api/me/policies/.
    policies: [
      'access_audit_logs',
      'access_solicitation_approvals',
      'import_availability_blocks',
      'import_compras',
      'import_generic_spreadsheet',
      'manage_admin_registries',
      'manage_purchases_and_materials',
      'manage_solicitacao_status',
      'use_gcal',
      'view_all_availability',
      'view_compras_dashboard',
      'view_compras_pendencias',
      'view_compras_stats',
      'view_map_metrics',
      'view_overview_dashboard',
      'view_reports',
    ],
    legacy: {
      canBloqueios: true,
      canCoordenador: true,
      canDashboardCompras: true,
    },
    expected: {
      canAccessApprovals: true,
      canAccessBlocks: true,
      canCreateSolicitation: true,
      canViewComprasDashboard: true,
    },
  },
  {
    actor: 'DAT',
    // DAT tem manage_admin_registries, import_*, manage_purchases_and_materials
    policies: [
      'access_audit_logs',
      'import_availability_blocks',
      'import_compras',
      'import_generic_spreadsheet',
      'manage_admin_registries',
      'manage_purchases_and_materials',
      'view_compras_dashboard', // DAT está em view_compras_dashboard (suportar/validar)
      'view_compras_pendencias',
      'view_compras_stats',
    ],
    legacy: {
      // canDashboardCompras vem do usePermissions: inDAT → true
      canDashboardCompras: true,
      canCoordenador: true, // canCoordenador inclui inDAT no usePermissions
    },
    expected: {
      canAccessApprovals: false,
      canAccessBlocks: false, // DAT sem view_all_availability nem canBloqueios
      canCreateSolicitation: true, // canCoordenador legacy true (inDAT)
      canViewComprasDashboard: true,
    },
  },
  {
    actor: 'Controle',
    policies: [
      'access_audit_logs', // operate_preagenda
      'manage_purchases_and_materials',
      'manage_solicitacao_status',
      'use_gcal',
      'view_all_availability', // após 0078
      'view_reports',
    ],
    legacy: {
      canBloqueios: true, // canControle (true) || canCoordenador || isFormador
      canCoordenador: false,
      canDashboardCompras: false, // Controle não vê dashboard compras
    },
    expected: {
      canAccessApprovals: false, // sem approve_solicitation nem canApproveSuper
      canAccessBlocks: true, // view_all_availability presente
      canCreateSolicitation: false,
      canViewComprasDashboard: false,
    },
  },
  {
    actor: 'Diretoria',
    policies: ['view_compras_dashboard', 'view_overview_dashboard', 'view_map_metrics'],
    legacy: {
      canBloqueios: false,
      canCoordenador: false,
      canDashboardCompras: true, // inDiretoria
    },
    expected: {
      canAccessApprovals: false,
      canAccessBlocks: false,
      canCreateSolicitation: false,
      canViewComprasDashboard: true, // policy presente + legacy true
    },
  },
  {
    actor: 'Gerente da Superintendência',
    // PR 3 hardening RBAC (2026-04-29): composite Setor Superintendência +
    // Função Gerente. Recebe a policy nova `access_solicitation_approvals`.
    policies: [
      'access_audit_logs',
      'access_solicitation_approvals',
      'manage_solicitacao_status',
      'use_gcal',
      'view_all_availability',
      'view_reports',
    ],
    legacy: {
      // PR 10 hardening RBAC (2026-04-30): canApproveSuper saiu do contrato
      // de useCanAccess. Decisão de Aprovações vem da policy
      // `access_solicitation_approvals` listada acima.
      canBloqueios: true,
      canCoordenador: false,
      canDashboardCompras: false,
    },
    expected: {
      canAccessApprovals: true, // policy access_solicitation_approvals presente
      canAccessBlocks: true, // view_all_availability presente
      canCreateSolicitation: false,
      canViewComprasDashboard: false,
    },
  },
  {
    actor: 'Coordenador',
    // Coord/Apoio são SCOPED — sem view_all_availability após 0078
    policies: [],
    legacy: {
      canBloqueios: true, // canCoordenador(=true) → canBloqueios true
      canCoordenador: true,
      canDashboardCompras: false,
    },
    expected: {
      canAccessApprovals: false,
      canAccessBlocks: true, // legacy.canBloqueios true
      canCreateSolicitation: true, // legacy.canCoordenador true
      canViewComprasDashboard: false,
    },
  },
  {
    actor: 'Apoio de Coordenação',
    // Apoio segue regra de Coordenador — sem view_all_availability
    policies: [],
    legacy: {
      canBloqueios: true,
      canCoordenador: true,
      canDashboardCompras: false,
    },
    expected: {
      canAccessApprovals: false,
      canAccessBlocks: true,
      canCreateSolicitation: true,
      canViewComprasDashboard: false,
    },
  },
  {
    actor: 'Formador',
    // Formador: nenhuma capability pública; só /me/events e bloqueio próprio (RD-02/03)
    policies: [],
    legacy: {
      canBloqueios: true, // isFormador → canBloqueios true (RD-02/03 — declara próprio)
      canCoordenador: false,
      canDashboardCompras: false,
    },
    expected: {
      canAccessApprovals: false,
      canAccessBlocks: true, // legacy via isFormador
      canCreateSolicitation: false,
      canViewComprasDashboard: false,
    },
  },
];

// ============================================================================
// Tests parametrizados
// ============================================================================

describe('RBAC Living Matrix (frontend)', () => {
  test.each(ACTORS)(
    '$actor: derived flags batem com matriz canônica',
    ({ actor, policies, legacy, expected }) => {
      const access = computeAccess(policies, legacy);
      const actual = {
        canAccessApprovals: access.canAccessApprovals,
        canAccessBlocks: access.canAccessBlocks,
        canCreateSolicitation: access.canCreateSolicitation,
        canViewComprasDashboard: access.canViewComprasDashboard,
      };
      expect(actual, `Mismatch para ator ${actor}. Atualize matriz frontend OU verifique drift de useCanAccess.`).toEqual(
        expected,
      );
    },
  );

  test('todos os atores estão cobertos (sanity)', () => {
    const expectedActors = new Set([
      'Superuser',
      'DAT',
      'Controle',
      'Diretoria',
      'Gerente da Superintendência',
      'Coordenador',
      'Apoio de Coordenação',
      'Formador',
    ]);
    const actualActors = new Set(ACTORS.map((a) => a.actor));
    expect(actualActors).toEqual(expectedActors);
  });
});
