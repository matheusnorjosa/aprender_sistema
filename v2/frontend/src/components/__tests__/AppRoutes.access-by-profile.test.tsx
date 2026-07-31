/**
 * AppRoutes — gates de rota por perfil canônico (PR 12 hardening RBAC).
 *
 * Espelha o PR 11 (#1316) — que cobriu o menu lateral — mas para gates de
 * rota: garante que URL direta (deep-link, bookmark, redirect 3rd-party)
 * não abre página proibida. O `<Forbidden />` precisa renderizar e a
 * mensagem precisa ser genérica ("Recurso indisponível" — OWASP: não
 * vazar nome de policy/recurso).
 *
 * 10 atores canônicos × 12 rotas críticas = matriz declarativa.
 *
 * Foco: gate de rota. Conteúdo da página é responsabilidade dos testes
 * próprios. Mockamos APIs internas para evitar fetch real.
 */

import { MemoryRouter } from 'react-router';
import { render, screen, waitFor } from '@testing-library/react';
import { describe, expect, test, vi } from 'vitest';

import { AppRoutes } from '../AppRoutes';
import type { CurrentUser } from '../../types';
import type { Permissions } from '../../hooks/usePermissions';

// ============================================================================
// Mocks de APIs internas das páginas (evita fetch real durante render)
// ============================================================================

vi.mock('../../api/me', () => ({
  getMyPolicies: vi.fn().mockResolvedValue([]),
}));
vi.mock('../../api/solicitacoes', () => ({
  listSolicitacoes: vi.fn().mockResolvedValue({ results: [], count: 0 }),
  approveSolicitacao: vi.fn(),
  rejectSolicitacao: vi.fn(),
  previewSolicitacao: vi.fn(),
  approveSolicitacoesBatch: vi.fn(),
  rejectSolicitacoesBatch: vi.fn(),
}));
vi.mock('../../api/ops', () => ({
  importAcoes: vi.fn(),
  importBloqueios: vi.fn(),
  importCadastros: vi.fn(),
  importColecoes: vi.fn(),
  importCompras: vi.fn(),
  importDeslocamentos: vi.fn(),
  importEquipeGerencia: vi.fn(),
  importEventos: vi.fn(),
  importMunicipios: vi.fn(),
  importProdutos: vi.fn(),
  importUsuarios: vi.fn(),
}));
vi.mock('../../api/availability', () => ({
  getMe: vi.fn().mockResolvedValue({}),
  listAvailabilityBlocks: vi.fn().mockResolvedValue([]),
  // MonthlyGridResponse: shape mínimo que evita TypeError no Grid.tsx
  // (espera arrays — `days`, `people`, `cells`).
  getMonthlyAvailability: vi.fn().mockResolvedValue({
    days: [],
    legend: {},
    people: [],
    cells: [],
    details_index: {},
  }),
  getMonthly: vi.fn().mockResolvedValue({
    days: [],
    legend: {},
    people: [],
    cells: [],
    details_index: {},
  }),
}));
vi.mock('../../api/stats', () => ({
  getHomeStats: vi.fn().mockResolvedValue({}),
}));
// Issue #1169: este teste cobre o GATE de rota de /solicitacoes/:id/editar, não a
// página em si (que depende de getSolicitacao/lookup não mockados aqui). Stub isola o gate.
vi.mock('../../pages/Solicitacoes/EditSolicitacaoPage', () => ({
  default: () => 'EDIT_PAGE',
}));

// ============================================================================
// Setup
// ============================================================================

const BASE_USER: CurrentUser = {
  id: 1,
  username: 'tester',
  email: 'tester@test.com',
  first_name: 'Test',
  last_name: 'User',
  name: 'Test User',
  groups: [],
  setores: [],
  funcoes: [],
  is_superuser: false,
  is_superintendencia: false,
  can_approve_super: false,
  permissions: [],
};

const EMPTY_PERMISSIONS: Permissions = {
  isAdmin: false,
  isCoordenador: false,
  isFormador: false,
  isGerente: false,
  inSuperintendencia: false,
  inGerencia: false,
  inDAT: false,
  inControle: false,
  inDiretoria: false,
  canApproveSuper: false,
  canCoordenador: false,
  canControle: false,
  canDAT: false,
  canAcoesInternas: false,
  canDashboardOverview: false,
  canDashboardEquipe: false,
  canDashboardGcal: false,
  canDashboardCompras: false,
  canMapaBrasil: false,
  canDashboardsMenu: false,
  canDisponibilidade: false,
  canSeeAllSectors: false,
};

const FORBIDDEN_TEXT = /Recurso indisponível/i;

function renderRoute(
  route: string,
  user: CurrentUser,
  permissions: Permissions,
  policies: readonly string[],
): void {
  render(
    <MemoryRouter initialEntries={[route]}>
      <AppRoutes user={user} permissions={permissions} policies={policies} />
    </MemoryRouter>,
  );
}

// ============================================================================
// Rotas críticas (espelham AppRoutes.tsx)
// ============================================================================

const CRITICAL_ROUTES = [
  '/dashboards',
  '/dashboards/compras',
  '/dashboards/equipe',
  '/dashboards/gcal',
  '/mapa-brasil',
  '/solicitacoes/aprovacoes',
  '/solicitacoes/disponibilidade',
  '/solicitacoes/bloqueios',
  '/solicitacoes/deslocamentos',
  '/controle',
  '/dat/admin',
  '/dat/importacoes',
] as const;

type CriticalRoute = (typeof CRITICAL_ROUTES)[number];

// ============================================================================
// Snapshot por ator: setores/funções (Permissions) + policies (do backend)
// + matriz `expectedAccess[route] = true|false`. Espelha rbac_matrix.test.ts
// e AppSidebar.menu.test.tsx (PR 11 #1316).
// ============================================================================

interface ActorSnapshot {
  actor: string;
  permissions: Permissions;
  policies: readonly string[];
  expectedAccess: Record<CriticalRoute, boolean>;
}

const ACTORS: ActorSnapshot[] = [
  {
    actor: 'Superuser',
    permissions: {
      ...EMPTY_PERMISSIONS,
      isAdmin: true,
      canControle: true,
      canDAT: true,
      canCoordenador: true,
      canAcoesInternas: true,
      canDashboardOverview: true,
      canDashboardEquipe: true,
      canDashboardGcal: true,
      canDashboardCompras: true,
      canMapaBrasil: true,
      canDashboardsMenu: true,
      canDisponibilidade: true,
      canSeeAllSectors: true,
      canApproveSuper: true,
    },
    // Superuser recebe todas as PUBLIC_POLICY_KEYS (bypass no backend). #1271: inclui
    // as 3 policies de menu do #1589.
    policies: [
      'access_audit_logs',
      'access_solicitation_approvals',
      'access_controle_section',
      'create_solicitation',
      'import_availability_blocks',
      'import_compras',
      'import_generic_spreadsheet',
      'manage_admin_registries',
      'manage_internal_actions',
      'manage_purchases_and_materials',
      'manage_solicitacao_status',
      'use_gcal',
      'view_all_availability',
      'view_compras_dashboard',
      'view_compras_pendencias',
      'view_compras_stats',
      'view_gcal_dashboard',
      'view_map_metrics',
      'view_overview_dashboard',
      'view_reports',
      'view_team_dashboard',
    ],
    expectedAccess: {
      '/dashboards': true,
      '/dashboards/compras': true,
      '/dashboards/equipe': true,
      '/dashboards/gcal': true,
      '/mapa-brasil': true,
      '/solicitacoes/aprovacoes': true,
      '/solicitacoes/disponibilidade': true,
      '/solicitacoes/bloqueios': true,
      '/solicitacoes/deslocamentos': true,
      '/controle': true,
      '/dat/admin': true,
      '/dat/importacoes': true,
    },
  },
  {
    actor: 'DAT',
    permissions: {
      ...EMPTY_PERMISSIONS,
      inDAT: true,
      canDAT: true,
      canCoordenador: true,
      canAcoesInternas: true,
      canDashboardEquipe: true,
      canDashboardGcal: true,
      canDashboardCompras: true,
      canMapaBrasil: true,
      canDashboardsMenu: true,
      canDisponibilidade: true,
    },
    // Prod-verificado (#1588) + view_team/gcal_dashboard (#1589: DAT via manage_admin_registries).
    policies: [
      'access_audit_logs',
      'import_availability_blocks',
      'import_compras',
      'import_generic_spreadsheet',
      'manage_admin_registries',
      'manage_purchases_and_materials',
      'view_all_availability',
      'view_compras_dashboard',
      'view_compras_pendencias',
      'view_compras_stats',
      'view_reports',
      'view_team_dashboard',
      'view_gcal_dashboard',
    ],
    expectedAccess: {
      '/dashboards': false, // sem view_overview_dashboard (Diretoria/superuser only)
      '/dashboards/compras': true,
      '/dashboards/equipe': true, // view_team_dashboard (via manage_admin_registries)
      '/dashboards/gcal': true, // view_gcal_dashboard
      '/mapa-brasil': false, // #1271: sem view_map_metrics (Diretoria-only) — antes via grupo
      '/solicitacoes/aprovacoes': false, // sem policy
      '/solicitacoes/disponibilidade': true, // canDisponibilidade
      '/solicitacoes/bloqueios': true, // canCoordenador (via inDAT) → canBloqueios
      '/solicitacoes/deslocamentos': true, // canDAT
      '/controle': false, // canControle=false
      '/dat/admin': true,
      '/dat/importacoes': true,
    },
  },
  {
    actor: 'Controle',
    permissions: {
      ...EMPTY_PERMISSIONS,
      inControle: true,
      canControle: true,
      canDashboardGcal: true,
      canDashboardsMenu: true,
      canDisponibilidade: true,
    },
    policies: [
      'access_audit_logs',
      'access_controle_section',
      'manage_purchases_and_materials',
      'manage_solicitacao_status',
      'use_gcal',
      'view_all_availability',
      'view_gcal_dashboard',
      'view_reports',
    ],
    expectedAccess: {
      '/dashboards': false,
      '/dashboards/compras': false, // sem policy view_compras_dashboard
      '/dashboards/equipe': false, // sem view_team_dashboard
      '/dashboards/gcal': true, // view_gcal_dashboard
      '/mapa-brasil': false,
      '/solicitacoes/aprovacoes': false, // Controle puro: sem policy
      '/solicitacoes/disponibilidade': true,
      '/solicitacoes/bloqueios': true, // canControle → canBloqueios
      '/solicitacoes/deslocamentos': true,
      '/controle': true,
      '/dat/admin': false,
      '/dat/importacoes': false,
    },
  },
  {
    actor: 'Diretoria',
    permissions: {
      ...EMPTY_PERMISSIONS,
      inDiretoria: true,
      canDashboardOverview: true,
      canDashboardEquipe: true,
      canDashboardGcal: true,
      canDashboardCompras: true,
      canMapaBrasil: true,
      canDashboardsMenu: true,
    },
    policies: [
      'view_compras_dashboard',
      'view_gcal_dashboard',
      'view_map_metrics',
      'view_overview_dashboard',
      'view_team_dashboard',
    ],
    expectedAccess: {
      '/dashboards': true,
      '/dashboards/compras': true,
      '/dashboards/equipe': true, // view_team_dashboard
      '/dashboards/gcal': true, // view_gcal_dashboard
      '/mapa-brasil': true,
      '/solicitacoes/aprovacoes': false,
      '/solicitacoes/disponibilidade': false, // D8/D9: removida
      '/solicitacoes/bloqueios': false, // sem view_all_availability nem canBloqueios
      '/solicitacoes/deslocamentos': false,
      '/controle': false,
      '/dat/admin': false,
      '/dat/importacoes': false,
    },
  },
  {
    actor: 'Gerente da Superintendência',
    permissions: {
      ...EMPTY_PERMISSIONS,
      isGerente: true,
      inSuperintendencia: true,
      canSeeAllSectors: true,
      canAcoesInternas: true,
      canDisponibilidade: true,
    },
    policies: [
      'access_audit_logs',
      'access_solicitation_approvals',
      'manage_solicitacao_status',
      'use_gcal',
      'view_all_availability',
      'view_reports',
    ],
    expectedAccess: {
      '/dashboards': false,
      '/dashboards/compras': false,
      '/dashboards/equipe': false,
      '/dashboards/gcal': false,
      '/mapa-brasil': false,
      '/solicitacoes/aprovacoes': true, // policy presente
      '/solicitacoes/disponibilidade': true,
      '/solicitacoes/bloqueios': true, // view_all_availability
      '/solicitacoes/deslocamentos': true, // view_all_availability
      '/controle': false,
      '/dat/admin': false,
      '/dat/importacoes': false,
    },
  },
  {
    actor: 'Gerente pedagógico (Vidas)',
    permissions: {
      ...EMPTY_PERMISSIONS,
      isGerente: true,
      inGerencia: true,
      canAcoesInternas: true,
      canDisponibilidade: true,
    },
    policies: [], // scoped após D9 — sem view_all_availability
    expectedAccess: {
      '/dashboards': false,
      '/dashboards/compras': false,
      '/dashboards/equipe': false,
      '/dashboards/gcal': false,
      '/mapa-brasil': false,
      '/solicitacoes/aprovacoes': false,
      '/solicitacoes/disponibilidade': true, // canDisponibilidade
      '/solicitacoes/bloqueios': false, // sem view_all_availability nem canBloqueios
      '/solicitacoes/deslocamentos': false,
      '/controle': false,
      '/dat/admin': false,
      '/dat/importacoes': false,
    },
  },
  {
    actor: 'Coordenador',
    permissions: {
      ...EMPTY_PERMISSIONS,
      isCoordenador: true,
      canCoordenador: true,
      canAcoesInternas: true,
      canDisponibilidade: true,
    },
    policies: [],
    expectedAccess: {
      '/dashboards': false,
      '/dashboards/compras': false,
      '/dashboards/equipe': false,
      '/dashboards/gcal': false,
      '/mapa-brasil': false,
      '/solicitacoes/aprovacoes': false,
      '/solicitacoes/disponibilidade': true,
      '/solicitacoes/bloqueios': true, // canCoordenador → canBloqueios
      '/solicitacoes/deslocamentos': true, // canCoordenador
      '/controle': false,
      '/dat/admin': false,
      '/dat/importacoes': false,
    },
  },
  {
    actor: 'Apoio de Coordenação',
    permissions: {
      ...EMPTY_PERMISSIONS,
      isCoordenador: true, // usePermissions trata Apoio igual a Coordenador
      canCoordenador: true,
      canAcoesInternas: true,
      canDisponibilidade: true,
    },
    policies: [],
    expectedAccess: {
      '/dashboards': false,
      '/dashboards/compras': false,
      '/dashboards/equipe': false,
      '/dashboards/gcal': false,
      '/mapa-brasil': false,
      '/solicitacoes/aprovacoes': false,
      '/solicitacoes/disponibilidade': true,
      '/solicitacoes/bloqueios': true,
      '/solicitacoes/deslocamentos': true,
      '/controle': false,
      '/dat/admin': false,
      '/dat/importacoes': false,
    },
  },
  {
    actor: 'Formador',
    permissions: {
      ...EMPTY_PERMISSIONS,
      isFormador: true,
    },
    policies: [],
    expectedAccess: {
      '/dashboards': false,
      '/dashboards/compras': false,
      '/dashboards/equipe': false,
      '/dashboards/gcal': false,
      '/mapa-brasil': false,
      '/solicitacoes/aprovacoes': false,
      '/solicitacoes/disponibilidade': false, // D8: Formador removido
      '/solicitacoes/bloqueios': true, // isFormador (RD-02/03)
      '/solicitacoes/deslocamentos': false,
      '/controle': false,
      '/dat/admin': false,
      '/dat/importacoes': false,
    },
  },
  {
    actor: 'Assistente Administrativo Controle',
    permissions: {
      ...EMPTY_PERMISSIONS,
      inControle: true,
      canControle: true,
      canDashboardGcal: true,
      canDashboardsMenu: true,
      canDisponibilidade: true,
    },
    policies: [
      'access_audit_logs',
      'access_controle_section',
      'access_solicitation_approvals',
      'manage_purchases_and_materials',
      'manage_solicitacao_status',
      'use_gcal',
      'view_all_availability',
      'view_gcal_dashboard',
      'view_reports',
    ],
    expectedAccess: {
      '/dashboards': false,
      '/dashboards/compras': false,
      '/dashboards/equipe': false, // sem view_team_dashboard
      '/dashboards/gcal': true, // view_gcal_dashboard
      '/mapa-brasil': false,
      '/solicitacoes/aprovacoes': true, // access_solicitation_approvals
      '/solicitacoes/disponibilidade': true,
      '/solicitacoes/bloqueios': true,
      '/solicitacoes/deslocamentos': true,
      '/controle': true,
      '/dat/admin': false,
      '/dat/importacoes': false,
    },
  },
];

// ============================================================================
// Tests parametrizados
// ============================================================================

describe('AppRoutes — gates de rota por perfil canônico', () => {
  for (const actor of ACTORS) {
    describe(`${actor.actor}`, () => {
      for (const route of CRITICAL_ROUTES) {
        const expected = actor.expectedAccess[route];
        const label = expected ? 'NÃO renderiza Forbidden' : 'renderiza Forbidden';
        test(`${route} → ${label}`, async () => {
          renderRoute(route, BASE_USER, actor.permissions, actor.policies);
          if (expected) {
            // Ator autorizado: a página pode estar carregando, com erros de
            // fetch ou já renderizada — qualquer coisa exceto Forbidden.
            // Esperamos pelo menos um tick para Suspense resolver, então
            // asserimos ausência do texto-sentinela.
            await waitFor(() => {
              expect(screen.queryByText(FORBIDDEN_TEXT)).not.toBeInTheDocument();
            });
          } else {
            // Ator negado: <Forbidden /> renderiza síncrono (sem lazy).
            expect(await screen.findByText(FORBIDDEN_TEXT)).toBeInTheDocument();
          }
        });
      }
    });
  }
});

// ============================================================================
// OWASP — Forbidden é genérico, sem vazar nome de policy/recurso
// ============================================================================

describe('AppRoutes — Forbidden é mensagem genérica (OWASP)', () => {
  const FORBIDDEN_LEAKAGE_PATTERNS = [
    /access_solicitation_approvals/i,
    /view_compras_dashboard/i,
    /view_all_availability/i,
    /manage_admin_registries/i,
    /superintend/i,
    /policy/i,
    /capability/i,
    /HasPerm/,
  ];

  test('Forbidden em /controle (Coordenador) não vaza policy/setor', async () => {
    renderRoute(
      '/controle',
      BASE_USER,
      { ...EMPTY_PERMISSIONS, isCoordenador: true, canCoordenador: true },
      [],
    );
    expect(await screen.findByText(FORBIDDEN_TEXT)).toBeInTheDocument();
    for (const pat of FORBIDDEN_LEAKAGE_PATTERNS) {
      expect(screen.queryByText(pat)).not.toBeInTheDocument();
    }
  });

  test('Forbidden em /solicitacoes/aprovacoes (DAT) não vaza policy', async () => {
    renderRoute(
      '/solicitacoes/aprovacoes',
      BASE_USER,
      { ...EMPTY_PERMISSIONS, inDAT: true, canDAT: true, canCoordenador: true },
      [], // sem policy
    );
    expect(await screen.findByText(FORBIDDEN_TEXT)).toBeInTheDocument();
    for (const pat of FORBIDDEN_LEAKAGE_PATTERNS) {
      expect(screen.queryByText(pat)).not.toBeInTheDocument();
    }
  });
});

// ============================================================================
// Sanity da matriz
// ============================================================================

describe('AppRoutes — sanity da matriz', () => {
  test('cada rota crítica tem ≥1 ator autorizado', () => {
    for (const route of CRITICAL_ROUTES) {
      const anyAllows = ACTORS.some((a) => a.expectedAccess[route]);
      expect(anyAllows, `Rota ${route} é negada para todos os atores — config incorreta?`).toBe(true);
    }
  });

  test('cada rota crítica tem ≥1 ator negado', () => {
    for (const route of CRITICAL_ROUTES) {
      const anyDenies = ACTORS.some((a) => !a.expectedAccess[route]);
      expect(anyDenies, `Rota ${route} é aberta para todos — não precisa de gate?`).toBe(true);
    }
  });

  test('cada ator (exceto Superuser) tem ≥1 rota crítica negada', () => {
    for (const actor of ACTORS) {
      if (actor.actor === 'Superuser') continue;
      const denied = CRITICAL_ROUTES.filter((r) => !actor.expectedAccess[r]);
      expect(denied.length, `Ator ${actor.actor} tem acesso a TODAS as rotas críticas`).toBeGreaterThan(0);
    }
  });

  test('cada ator tem ≥1 rota crítica autorizada', () => {
    for (const actor of ACTORS) {
      const allowed = CRITICAL_ROUTES.filter((r) => actor.expectedAccess[r]);
      expect(allowed.length, `Ator ${actor.actor} é negado em todas as rotas críticas`).toBeGreaterThan(0);
    }
  });

  test('todos os 10 atores canônicos cobertos', () => {
    const expected = new Set([
      'Superuser',
      'DAT',
      'Controle',
      'Diretoria',
      'Gerente da Superintendência',
      'Gerente pedagógico (Vidas)',
      'Coordenador',
      'Apoio de Coordenação',
      'Formador',
      'Assistente Administrativo Controle',
    ]);
    const actual = new Set(ACTORS.map((a) => a.actor));
    expect(actual).toEqual(expected);
  });
});

// ============================================================================
// Gate de /solicitacoes/:id/editar (Issue #1169, Item 1)
// ============================================================================
// Antes: `element={user ? <EditSolicitacaoPage /> : <Forbidden />}` — qualquer
// autenticado abria a tela e falhava no submit (backend IsOwnerOrPrivileged → 403).
// Depois: gate alinhado ao menu — só canCoordenador (owner plausível) ou
// canApproveSuper (privilegiado) carregam. Backend segue autoritativo.
describe('AppRoutes — gate de /solicitacoes/:id/editar (Issue #1169)', () => {
  const EDITAR = '/solicitacoes/42/editar';

  test('autenticado sem canCoordenador nem canApproveSuper → Forbidden', async () => {
    renderRoute(EDITAR, BASE_USER, { ...EMPTY_PERMISSIONS }, []);
    expect(await screen.findByText(FORBIDDEN_TEXT)).toBeInTheDocument();
  });

  test('canCoordenador → carrega a edição (não Forbidden)', async () => {
    renderRoute(EDITAR, BASE_USER, { ...EMPTY_PERMISSIONS, canCoordenador: true }, []);
    expect(await screen.findByText('EDIT_PAGE')).toBeInTheDocument();
    expect(screen.queryByText(FORBIDDEN_TEXT)).not.toBeInTheDocument();
  });

  test('canApproveSuper → carrega a edição (não Forbidden)', async () => {
    renderRoute(EDITAR, BASE_USER, { ...EMPTY_PERMISSIONS, canApproveSuper: true }, []);
    expect(await screen.findByText('EDIT_PAGE')).toBeInTheDocument();
  });
});
