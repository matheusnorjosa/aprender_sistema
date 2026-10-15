/**
 * AppRoutes — gates de rota por perfil canônico (PR 12 hardening RBAC).
 *
 * Espelha o PR 11 (#1316) — que cobriu o menu lateral — mas para gates de
 * rota: garante que URL direta (deep-link, bookmark, redirect 3rd-party)
 * não abre página proibida. O `<Forbidden />` precisa renderizar e a
 * mensagem precisa ser genérica ("Recurso indisponível" — OWASP: não
 * vazar nome de policy/recurso).
 *
 * 10 atores canônicos × 16 rotas críticas = matriz declarativa.
 *
 * Foco: gate de rota. Conteúdo da página é responsabilidade dos testes
 * próprios. Mockamos APIs internas para evitar fetch real.
 */

import { MemoryRouter } from 'react-router';
import { render, screen, waitFor } from '@testing-library/react';
import { describe, expect, test, vi } from 'vitest';

import { AppRoutes } from '../AppRoutes';
import type { CurrentUser } from '../../types';
import { listDeslocamentos } from '../../api/deslocamentos';
import {
  ATORES_RBAC,
  PERSONAS_POR_VINCULO,
  atorRbac,
  usuarioDeTeste,
  type AtorRbac,
  type NomeDoAtor,
} from '../../test/atoresRbac';
import { ComAcesso } from '../../test/comAcesso';

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
  // FiltersBar chama getGerencias ao montar a página mensal; sem este stub a
  // chamada vira unhandled rejection que derruba o processo do vitest (exit 1).
  getGerencias: vi.fn().mockResolvedValue([]),
}));
vi.mock('../../api/deslocamentos', () => ({
  listDeslocamentos: vi.fn().mockResolvedValue({ count: 0, next: null, previous: null, results: [] }),
  listFormadoresDoSetor: vi.fn().mockResolvedValue([]),
  createDeslocamento: vi.fn(),
  updateDeslocamento: vi.fn(),
  deleteDeslocamento: vi.fn(),
}));
vi.mock('../../api/stats', () => ({
  getHomeStats: vi.fn().mockResolvedValue({}),
}));
// Issue #1169: este teste cobre o GATE de rota de /solicitacoes/:id/editar, não a
// página em si (que depende de getSolicitacao/lookup não mockados aqui). Stub isola o gate.
vi.mock('../../pages/Solicitacoes/EditSolicitacaoPage', () => ({
  default: () => 'EDIT_PAGE',
}));
// Idem para Compras (/controle/compras, /compras-materiais, /dat/compras-materiais).
vi.mock('../../pages/DATModule/ComprasPage', () => ({
  default: () => 'COMPRAS_PAGE',
}));
// #1656: idem para /solicitacoes/publicacao — o teste cobre o gate, não a página.
vi.mock('../../pages/Solicitacoes/PublicacaoSetorPage', () => ({
  default: () => 'PUBLICACAO_PAGE',
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
  gerencias: [],
  is_superuser: false,
  is_superintendencia: false,
  can_approve_super: false,
  permissions: [],
};

const FORBIDDEN_TEXT = /Recurso indisponível/i;

/** Rota com o acesso que o App monta: policies de /me/policies + superusuário do /me. */
function renderRoute(route: string, user: CurrentUser, policies: readonly string[]): void {
  render(
    <MemoryRouter initialEntries={[route]}>
      <ComAcesso policies={policies} superusuario={user.is_superuser}>
        <AppRoutes user={user} />
      </ComAcesso>
    </MemoryRouter>,
  );
}

// ============================================================================
// Rotas críticas (espelham AppRoutes.tsx)
// ============================================================================

const EDITAR = '/solicitacoes/42/editar';

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
  EDITAR,
  '/controle',
  '/controle/compras',
  '/compras-materiais',
  '/dat/compras-materiais',
  '/dat/admin',
  '/dat/importacoes',
] as const;

type CriticalRoute = (typeof CRITICAL_ROUTES)[number];

// ============================================================================
// Linha de base persona × rota: os 10 atores de `src/test/atoresRbac.ts` (payload de /me e
// policies medidas no backend). PR 7 das permissões: as rotas decidem só por policy; esta
// matriz foi commitada verde com o código antigo e não mudou com a troca.
// ============================================================================

interface ActorSnapshot {
  actor: NomeDoAtor;
  expectedAccess: Record<CriticalRoute, boolean>;
}

const NEGA_TUDO: Record<CriticalRoute, boolean> = Object.fromEntries(
  CRITICAL_ROUTES.map((r) => [r, false]),
) as Record<CriticalRoute, boolean>;

/** Rotas de Compras (su ∨ Controle ∨ DAT hoje). */
const COMPRAS = { '/controle/compras': true, '/compras-materiais': true, '/dat/compras-materiais': true } as const;
/** Grade, Bloqueios e Deslocamentos. */
const ESCOPO = {
  '/solicitacoes/disponibilidade': true,
  '/solicitacoes/bloqueios': true,
  '/solicitacoes/deslocamentos': true,
} as const;

const ACTORS: ActorSnapshot[] = [
  {
    actor: 'Superuser',
    expectedAccess: Object.fromEntries(CRITICAL_ROUTES.map((r) => [r, true])) as Record<CriticalRoute, boolean>,
  },
  {
    actor: 'DAT',
    expectedAccess: {
      ...NEGA_TUDO,
      '/dashboards/compras': true,
      '/dashboards/equipe': true,
      '/dashboards/gcal': true,
      '/mapa-brasil': true, // o seed dá view_map_metrics ao DAT
      ...ESCOPO,
      [EDITAR]: true,
      ...COMPRAS,
      '/dat/admin': true,
      // '/dat/importacoes' fica negada: importação pela tela é só do superusuário (02/10/2026)
    },
  },
  {
    actor: 'Controle',
    expectedAccess: {
      ...NEGA_TUDO,
      '/dashboards/gcal': true,
      ...ESCOPO,
      '/controle': true,
      ...COMPRAS,
    },
  },
  {
    actor: 'Diretoria',
    expectedAccess: {
      ...NEGA_TUDO,
      '/dashboards': true,
      '/dashboards/compras': true,
      '/dashboards/equipe': true,
      '/dashboards/gcal': true,
      '/mapa-brasil': true,
      // D8: fora da Grade Mensal.
    },
  },
  {
    // Vínculo GERENTE vigente: Grade, Bloqueios e Deslocamentos (PR A).
    actor: 'Gerente da Superintendência',
    expectedAccess: { ...NEGA_TUDO, '/solicitacoes/aprovacoes': true, ...ESCOPO, [EDITAR]: true },
  },
  {
    actor: 'Gerente pedagógico (Vidas)',
    expectedAccess: { ...NEGA_TUDO, ...ESCOPO, [EDITAR]: true },
  },
  {
    actor: 'Coordenador',
    expectedAccess: { ...NEGA_TUDO, ...ESCOPO, [EDITAR]: true },
  },
  {
    actor: 'Apoio de Coordenação',
    expectedAccess: { ...NEGA_TUDO, ...ESCOPO, [EDITAR]: true },
  },
  {
    // RD-02/03: só o próprio bloqueio.
    actor: 'Formador',
    expectedAccess: { ...NEGA_TUDO, '/solicitacoes/bloqueios': true },
  },
  {
    actor: 'Assistente Administrativo Controle',
    expectedAccess: {
      ...NEGA_TUDO,
      '/dashboards/gcal': true,
      '/solicitacoes/aprovacoes': true,
      ...ESCOPO,
      [EDITAR]: true,
      '/controle': true,
      ...COMPRAS,
    },
  },
];

/** Renderiza a rota como o App a monta para a pessoa (payload de /me + /me/policies). */
function renderRotaDoAtor(route: string, { user, policies }: Pick<AtorRbac, 'user' | 'policies'>): void {
  renderRoute(route, user, policies);
}

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
          renderRotaDoAtor(route, atorRbac(actor.actor));
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

// PR 7: quem recebe as mesmas policies abre as mesmas rotas, com ou sem grupo.
describe('AppRoutes — personas por vínculo ≡ grupo (PR 7)', () => {
  for (const persona of PERSONAS_POR_VINCULO) {
    const esperado = ACTORS.find((a) => a.actor === persona.equivale)!.expectedAccess;
    describe(`${persona.ator} ≡ ${persona.equivale}`, () => {
      for (const route of CRITICAL_ROUTES) {
        test(`${route} → ${esperado[route] ? 'abre' : 'Recurso indisponível'}`, async () => {
          renderRotaDoAtor(route, persona);
          if (esperado[route]) {
            await waitFor(() => expect(screen.queryByText(FORBIDDEN_TEXT)).not.toBeInTheDocument());
          } else {
            expect(await screen.findByText(FORBIDDEN_TEXT)).toBeInTheDocument();
          }
        });
      }
    });
  }
});

// ============================================================================
// Importação pela tela: só superusuário (decisão do dono, 02/10/2026)
// ============================================================================

describe('AppRoutes — telas de importação só abrem para superusuário', () => {
  const ROTAS_DE_IMPORTACAO = ['/dat/importacoes', '/dat/importacao', '/dat/admin/equipe-gerencia'];
  test.each(ROTAS_DE_IMPORTACAO)('DAT (manage_admin_registries, import_*) em %s → Recurso indisponível', async (rota) => {
    renderRotaDoAtor(rota, atorRbac('DAT'));
    expect(await screen.findByText(FORBIDDEN_TEXT)).toBeInTheDocument();
  });

  test.each(ROTAS_DE_IMPORTACAO)('Superusuário em %s → abre a tela', async (rota) => {
    renderRotaDoAtor(rota, atorRbac('Superuser'));
    expect((await screen.findAllByText(/Importa/, {}, { timeout: 15000 })).length).toBeGreaterThan(0);
    expect(screen.queryByText(FORBIDDEN_TEXT)).not.toBeInTheDocument();
  });
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
    renderRotaDoAtor('/controle', atorRbac('Coordenador'));
    expect(await screen.findByText(FORBIDDEN_TEXT)).toBeInTheDocument();
    for (const pat of FORBIDDEN_LEAKAGE_PATTERNS) {
      expect(screen.queryByText(pat)).not.toBeInTheDocument();
    }
  });

  test('Forbidden em /solicitacoes/aprovacoes (DAT) não vaza policy', async () => {
    renderRotaDoAtor('/solicitacoes/aprovacoes', atorRbac('DAT'));
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
    expect(new Set(ACTORS.map((a) => a.actor))).toEqual(expected);
    expect(new Set(ATORES_RBAC.map((a) => a.ator))).toEqual(expected);
  });
});

// ============================================================================
// Gate de /solicitacoes/:id/editar (Issue #1169; PR 7 das permissões)
// ============================================================================
// Quem pode ser dono ou decidir: `create_solicitation` (quem cria é dono, e o servidor deixa o
// dono editar), `access_solicitation_approvals` (aprovador) ou `manage_admin_registries` (DAT).
// Antes o gate lia o grupo (Coordenador/Apoio/DAT) e o `can_approve_super` do /me. O backend
// segue autoritativo no salvar.
describe('AppRoutes — gate de /solicitacoes/:id/editar', () => {
  test.each(['create_solicitation', 'access_solicitation_approvals', 'manage_admin_registries'])(
    '%s → carrega a edição',
    async (policy) => {
      renderRoute(EDITAR, BASE_USER, [policy]);
      expect(await screen.findByText('EDIT_PAGE')).toBeInTheDocument();
      expect(screen.queryByText(FORBIDDEN_TEXT)).not.toBeInTheDocument();
    },
  );

  test('sem nenhuma das três → Forbidden', async () => {
    renderRoute(EDITAR, BASE_USER, ['view_all_availability', 'access_travel']);
    expect(await screen.findByText(FORBIDDEN_TEXT)).toBeInTheDocument();
  });

  test('can_approve_super e grupos no /me, sem policy → Forbidden (o payload não decide)', async () => {
    const user = usuarioDeTeste({ setores: ['DAT'], funcoes: ['Coordenador'], aprovador: true });
    renderRoute(EDITAR, user, []);
    expect(await screen.findByText(FORBIDDEN_TEXT)).toBeInTheDocument();
    expect(screen.queryByText('EDIT_PAGE')).not.toBeInTheDocument();
  });
});

// ============================================================================
// Gate de /solicitacoes/publicacao (#1656) — policy publish_setor_solicitacao
// ============================================================================
// A Apoio de Coordenação publica no Google Agenda os eventos aprovados do próprio
// setor. A rota exige a MESMA policy da API; `use_gcal` (Controle) não basta, e a
// Apoio continua fora da Pré-agenda (access_controle_section).
describe('AppRoutes — gate de /solicitacoes/publicacao (#1656)', () => {
  const PUBLICACAO = '/solicitacoes/publicacao';
  const APOIO_POLICIES = ['create_solicitation', 'publish_setor_solicitacao'];

  test('Apoio de Coordenação (publish_setor_solicitacao) → carrega a página', async () => {
    renderRoute(PUBLICACAO, BASE_USER, APOIO_POLICIES);
    expect(await screen.findByText('PUBLICACAO_PAGE')).toBeInTheDocument();
    expect(screen.queryByText(FORBIDDEN_TEXT)).not.toBeInTheDocument();
  });

  test('Coordenador (só create_solicitation) → Forbidden', async () => {
    renderRoute(PUBLICACAO, BASE_USER, ['create_solicitation']);
    expect(await screen.findByText(FORBIDDEN_TEXT)).toBeInTheDocument();
    expect(screen.queryByText('PUBLICACAO_PAGE')).not.toBeInTheDocument();
  });

  test('Controle (use_gcal, sem publish_setor_solicitacao) → Forbidden', async () => {
    renderRoute(PUBLICACAO, BASE_USER, [
      'access_controle_section',
      'manage_solicitacao_status',
      'use_gcal',
      'view_gcal_dashboard',
    ]);
    expect(await screen.findByText(FORBIDDEN_TEXT)).toBeInTheDocument();
    expect(screen.queryByText('PUBLICACAO_PAGE')).not.toBeInTheDocument();
  });

  test('Apoio continua bloqueada na /pre-agenda', async () => {
    renderRoute('/pre-agenda', BASE_USER, APOIO_POLICIES);
    expect(await screen.findByText(FORBIDDEN_TEXT)).toBeInTheDocument();
  });
});

// ============================================================================
// PR A + PR 7: gestão só por VÍNCULO (sem grupo de FUNÇÃO)
// ============================================================================
// O servidor soma o vínculo GERENTE/COORDENADOR/APOIO nas policies access_* (Grade, Bloqueios,
// Deslocamentos). A rota lê só a policy: com ela abre, sem ela nega, tenha o /me o vínculo ou não.
describe('AppRoutes — gestor só por vínculo (PR A)', () => {
  const comVinculo = (papel: string): CurrentUser =>
    usuarioDeTeste({ gerencias: [{ id: 4, rotulo: 'Superativar', papeis: [papel] }] });
  const POLICIES_DO_VINCULO = ['access_availability_blocks', 'access_monthly_availability', 'access_travel'];

  for (const route of ['/solicitacoes/disponibilidade', '/solicitacoes/bloqueios', '/solicitacoes/deslocamentos']) {
    test(`COORDENADOR por vínculo (policies do servidor): ${route} → NÃO renderiza Forbidden`, async () => {
      renderRoute(route, comVinculo('COORDENADOR'), POLICIES_DO_VINCULO);
      await waitFor(() => {
        expect(screen.queryByText(FORBIDDEN_TEXT)).not.toBeInTheDocument();
      });
    });

    test(`vínculo no /me sem as policies: ${route} → Forbidden`, async () => {
      renderRoute(route, comVinculo('COORDENADOR'), []);
      expect(await screen.findByText(FORBIDDEN_TEXT)).toBeInTheDocument();
    });
  }

  test('COORDENADOR por vínculo: Deslocamentos abre de fato (sem "Sem permissão") e lista', async () => {
    renderRoute('/solicitacoes/deslocamentos', comVinculo('COORDENADOR'), POLICIES_DO_VINCULO);
    await waitFor(() => expect(listDeslocamentos).toHaveBeenCalled(), { timeout: 3000 });
    expect(screen.queryByText('Sem permissão')).not.toBeInTheDocument();
  });

  test('COORDENADOR por vínculo: /solicitacoes/aprovacoes continua negada (vínculo não é policy)', async () => {
    renderRoute('/solicitacoes/aprovacoes', comVinculo('COORDENADOR'), POLICIES_DO_VINCULO);
    expect(await screen.findByText(FORBIDDEN_TEXT)).toBeInTheDocument();
  });
});
