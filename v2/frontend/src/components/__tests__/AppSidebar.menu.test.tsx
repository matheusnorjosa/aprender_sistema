/**
 * AppSidebar — Matriz Viva por perfil canônico (PR 11 hardening RBAC).
 *
 * Cobre visibilidade de todos os itens top-level do menu lateral por 10
 * atores canônicos, espelhando a Matriz Viva do backend (`apps/core/rbac/matrix.py`)
 * e o `rbac_matrix.test.ts` do hook. Falha indica drift entre setor/função
 * legacy e capabilities/policies atuais.
 *
 * Cobertura especial para children críticos:
 * - Dashboards: cada child (geral, compras, equipe, gcal, mapa) tem condição própria.
 * - DAT: 4 children (admin, cadastros, importações, registros) — atalho para
 *   imports unificados (PR-A1/B/C/D DAT Imports, abril 2026).
 *
 * Fora de escopo (intencionalmente):
 * - Backend / policies / usePermissions / useCanAccess (apenas leitura).
 * - AppRoutes / HomePage / ApprovalsPage (cobertos pelos próprios testes).
 *
 * Convenção: `permissions` espelha `usePermissions(user)`; `policies` espelha
 * `GET /api/me/policies/`. Atualizar fixtures aqui exige atualizar
 * `rbac_matrix.test.ts` em paralelo.
 */

import { MemoryRouter } from 'react-router-dom';
import { render, screen, within, fireEvent } from '@testing-library/react';
import { describe, expect, test } from 'vitest';

import { AppSidebar } from '../AppSidebar';
import type { Permissions } from '../../hooks/usePermissions';

// ============================================================================
// Setup
// ============================================================================

const COLORS = { sidebarBackground: '#001529', borderLight: '#303030' };

const SIDEBAR_PROPS = {
  gcalErrorCount: 0,
  unreadNotifications: 0,
  isMobile: false,
  sidebarCollapsed: false,
  toggleSidebar: () => {},
  colors: COLORS,
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

function renderSidebar(permissions: Permissions, policies: readonly string[]): void {
  render(
    <MemoryRouter>
      <AppSidebar permissions={permissions} policies={policies} {...SIDEBAR_PROPS} />
    </MemoryRouter>,
  );
}

// ============================================================================
// Snapshot por ator
// ============================================================================

/**
 * Itens top-level do menu lateral. Labels exatos exibidos pelo `AppSidebar.tsx`.
 * Mantém ordem de declaração no componente para clareza de diff.
 */
const TOP_LEVEL_ITEMS = [
  'Página Inicial',
  'Meus Eventos',
  'Aprovações',
  'Bloqueios',
  'Controle',
  'Ações Internas',
  'Deslocamentos',
  'Dashboards',
  'DAT',
  'Grade Mensal',
  'Solicitações',
] as const;

type TopLevelItem = (typeof TOP_LEVEL_ITEMS)[number];

/**
 * Children críticos do submenu Dashboards (cada um tem condição independente).
 * Usado apenas para atores cujo `Dashboards` é visível.
 */
const DASHBOARDS_CHILDREN = [
  'Dashboard Geral',
  'Dashboard Compras',
  'Dashboard Equipe',
  'Dashboard GCal',
  'Mapa do Brasil',
] as const;

type DashboardsChild = (typeof DASHBOARDS_CHILDREN)[number];

interface ActorSnapshot {
  actor: string;
  permissions: Permissions;
  policies: readonly string[];
  /** Subset literal de TOP_LEVEL_ITEMS visível para este ator. */
  expectedVisible: readonly TopLevelItem[];
  /**
   * Subset de DASHBOARDS_CHILDREN visível DENTRO do submenu Dashboards.
   * Use `[]` quando 'Dashboards' não está em `expectedVisible`.
   */
  expectedDashboardsChildren: readonly DashboardsChild[];
  /** Children do DAT submenu visíveis. `[]` quando 'DAT' não está visível. */
  expectedDatChildren: readonly string[];
}

// SSOT: cada ator declara setores/funções (espelhando usePermissions) e
// policies (espelhando seed do backend). Asserções de visibilidade derivam
// das condições em AppSidebar.tsx (linhas 285-373).
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
    policies: [
      'access_audit_logs',
      'access_solicitation_approvals',
      'view_all_availability',
      'view_compras_dashboard',
      'view_overview_dashboard',
      'view_map_metrics',
    ],
    expectedVisible: [
      'Página Inicial',
      'Meus Eventos',
      'Aprovações',
      'Bloqueios',
      'Controle',
      'Ações Internas',
      'Deslocamentos',
      'Dashboards',
      'DAT',
      'Grade Mensal',
      'Solicitações',
    ],
    expectedDashboardsChildren: [
      'Dashboard Geral',
      'Dashboard Compras',
      'Dashboard Equipe',
      'Dashboard GCal',
      'Mapa do Brasil',
    ],
    expectedDatChildren: ['Administração', 'Cadastros', 'Importações', 'Registros de Turmas'],
  },
  {
    actor: 'DAT',
    permissions: {
      ...EMPTY_PERMISSIONS,
      inDAT: true,
      canDAT: true,
      canCoordenador: true, // canCoordenador inclui inDAT
      canAcoesInternas: true,
      canDashboardEquipe: true,
      canDashboardGcal: true,
      canDashboardCompras: true,
      canMapaBrasil: true,
      canDashboardsMenu: true,
      canDisponibilidade: true,
    },
    policies: [
      'access_audit_logs',
      'import_availability_blocks',
      'import_compras',
      'import_generic_spreadsheet',
      'manage_admin_registries',
      'manage_purchases_and_materials',
      'view_compras_dashboard',
    ],
    // Sem 'Aprovações' (sem policy), sem 'Controle' (canControle=false).
    // 'Bloqueios' aparece via canBloqueios = canCoordenador (DAT atua como coord operacional).
    expectedVisible: [
      'Página Inicial',
      'Meus Eventos',
      'Bloqueios',
      'Ações Internas',
      'Deslocamentos',
      'Dashboards',
      'DAT',
      'Grade Mensal',
      'Solicitações',
    ],
    expectedDashboardsChildren: [
      // 'Dashboard Geral' escondido (canDashboardOverview=false; só Diretoria/superuser)
      'Dashboard Compras',
      'Dashboard Equipe',
      'Dashboard GCal',
      'Mapa do Brasil',
    ],
    expectedDatChildren: ['Administração', 'Cadastros', 'Importações', 'Registros de Turmas'],
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
      'manage_purchases_and_materials',
      'manage_solicitacao_status',
      'use_gcal',
      'view_all_availability',
      'view_reports',
    ],
    // Sem 'Aprovações' (sem policy access_solicitation_approvals — Controle puro).
    // Sem 'DAT', sem 'Solicitações', sem 'Ações Internas'.
    expectedVisible: [
      'Página Inicial',
      'Meus Eventos',
      'Bloqueios',
      'Controle',
      'Deslocamentos',
      'Dashboards',
      'Grade Mensal',
    ],
    // Apenas Dashboard GCal (operação do calendário). Resto é Diretoria/DAT.
    expectedDashboardsChildren: ['Dashboard GCal'],
    expectedDatChildren: [],
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
      // canDisponibilidade=false (D8/D9: Diretoria removida da Grade Mensal).
    },
    policies: ['view_compras_dashboard', 'view_overview_dashboard', 'view_map_metrics'],
    expectedVisible: ['Página Inicial', 'Meus Eventos', 'Dashboards'],
    expectedDashboardsChildren: [
      'Dashboard Geral',
      'Dashboard Compras',
      'Dashboard Equipe',
      'Dashboard GCal',
      'Mapa do Brasil',
    ],
    expectedDatChildren: [],
  },
  {
    actor: 'Gerente da Superintendência',
    permissions: {
      ...EMPTY_PERMISSIONS,
      isGerente: true,
      inSuperintendencia: true,
      canSeeAllSectors: true,
      canAcoesInternas: true, // canAcoesInternas inclui isGerente
      canDisponibilidade: true, // canDisponibilidade inclui isGerente
    },
    policies: [
      'access_audit_logs',
      'access_solicitation_approvals',
      'manage_solicitacao_status',
      'use_gcal',
      'view_all_availability',
      'view_reports',
    ],
    // Aprovações via policy. Bloqueios via view_all_availability.
    // Sem dashboards (Gerente Sup não tem dashboard próprio).
    expectedVisible: [
      'Página Inicial',
      'Meus Eventos',
      'Aprovações',
      'Bloqueios',
      'Ações Internas',
      'Deslocamentos',
      'Grade Mensal',
    ],
    expectedDashboardsChildren: [],
    expectedDatChildren: [],
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
    // Gerente pedagógico/Vidas é scoped (sem view_all_availability após D9).
    policies: [],
    // Sem 'Aprovações' (não é Sup), sem 'Bloqueios' (sem view_all e sem canBloqueios).
    // Sem 'Deslocamentos' (não tem nenhuma das 4 condições).
    expectedVisible: [
      'Página Inicial',
      'Meus Eventos',
      'Ações Internas',
      'Grade Mensal',
    ],
    expectedDashboardsChildren: [],
    expectedDatChildren: [],
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
    expectedVisible: [
      'Página Inicial',
      'Meus Eventos',
      'Bloqueios', // canBloqueios via canCoordenador
      'Ações Internas',
      'Deslocamentos', // via canCoordenador
      'Grade Mensal',
      'Solicitações',
    ],
    expectedDashboardsChildren: [],
    expectedDatChildren: [],
  },
  {
    actor: 'Apoio de Coordenação',
    permissions: {
      ...EMPTY_PERMISSIONS,
      // usePermissions trata Apoio igual a Coordenador (isCoordenador=true).
      isCoordenador: true,
      canCoordenador: true,
      canAcoesInternas: true,
      canDisponibilidade: true,
    },
    policies: [],
    expectedVisible: [
      'Página Inicial',
      'Meus Eventos',
      'Bloqueios',
      'Ações Internas',
      'Deslocamentos',
      'Grade Mensal',
      'Solicitações',
    ],
    expectedDashboardsChildren: [],
    expectedDatChildren: [],
  },
  {
    actor: 'Formador',
    permissions: {
      ...EMPTY_PERMISSIONS,
      isFormador: true,
      // Formador NÃO está em canDisponibilidade após D8 (RD-02/03 — declara próprio bloqueio).
      // canBloqueios via isFormador.
    },
    policies: [],
    expectedVisible: [
      'Página Inicial',
      'Meus Eventos',
      'Bloqueios', // canBloqueios via isFormador (RD-02/03 — escopo próprio via queryset)
    ],
    expectedDashboardsChildren: [],
    expectedDatChildren: [],
  },
  {
    actor: 'Assistente Administrativo Controle',
    // Composite (PR 3 hardening RBAC, #1308): Asst Admin + setor Controle.
    // Recebe a policy access_solicitation_approvals + capabilities do Controle.
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
      'access_solicitation_approvals',
      'manage_purchases_and_materials',
      'manage_solicitacao_status',
      'use_gcal',
      'view_all_availability',
      'view_reports',
    ],
    expectedVisible: [
      'Página Inicial',
      'Meus Eventos',
      'Aprovações', // policy presente (composite)
      'Bloqueios',
      'Controle',
      'Deslocamentos',
      'Dashboards',
      'Grade Mensal',
    ],
    expectedDashboardsChildren: ['Dashboard GCal'],
    expectedDatChildren: [],
  },
];

// ============================================================================
// Helpers de assertion
// ============================================================================

/**
 * Itens top-level: estão presentes como links no DOM (top-level) ou como
 * títulos de submenu. Antd renderiza ambos com `role="menuitem"`.
 *
 * Para itens-link (`<Menu.Item><Link>...`), busca por `role="link"`.
 * Para submenu titles (Controle, Ações Internas, Dashboards, DAT, Solicitações),
 * busca por `role="menuitem"` com o título.
 */
function isTopLevelVisible(label: TopLevelItem): boolean {
  // Tenta como link primeiro (item simples).
  const link = screen.queryByRole('link', { name: new RegExp(`^${label}$`, 'i') });
  if (link) return true;
  // Submenu titles: presentes como menuitem com texto.
  const submenu = screen.queryByRole('menuitem', { name: new RegExp(`^${label}$`, 'i') });
  if (submenu) return true;
  // Fallback: qualquer texto exato visível no menu.
  const navs = screen.queryAllByRole('navigation');
  for (const nav of navs) {
    const match = within(nav).queryByText(new RegExp(`^${label}$`, 'i'));
    if (match) return true;
  }
  return false;
}

/**
 * Antd inline submenu por padrão renderiza children sob demanda — fechado
 * não há nodes no DOM. Para inspecionar children precisa abrir clicando no
 * `.ant-menu-submenu-title`. Quando o submenu não existe (escondido para o
 * ator), retorna `[]` sem erro.
 */
function openSubmenuByTitle(title: string): boolean {
  // Antd renderiza o trigger como `<div class="ant-menu-submenu-title">`.
  // O `role="menuitem"` envolvente nem sempre é nominal-acessível por nome;
  // navegamos direto pelo class para garantir o disparo.
  const titles = document.querySelectorAll<HTMLElement>('.ant-menu-submenu-title');
  for (const el of Array.from(titles)) {
    if ((el.textContent || '').trim() === title) {
      fireEvent.click(el);
      return true;
    }
  }
  return false;
}

function getDashboardsChildren(): string[] {
  if (!openSubmenuByTitle('Dashboards')) return [];
  return DASHBOARDS_CHILDREN.filter(
    (child) => screen.queryByRole('link', { name: new RegExp(child, 'i') }) !== null,
  );
}

function getDatChildren(): string[] {
  if (!openSubmenuByTitle('DAT')) return [];
  const labels = ['Administração', 'Cadastros', 'Importações', 'Registros de Turmas'];
  return labels.filter(
    (label) => screen.queryByRole('link', { name: new RegExp(`^${label}$`, 'i') }) !== null,
  );
}

// ============================================================================
// Tests parametrizados
// ============================================================================

describe('AppSidebar — visibilidade top-level por perfil', () => {
  test.each(ACTORS)(
    '$actor: top-level visíveis batem com matriz canônica',
    ({ actor, permissions, policies, expectedVisible }) => {
      renderSidebar(permissions, policies);
      const actualVisible = TOP_LEVEL_ITEMS.filter(isTopLevelVisible);
      expect(actualVisible, `Drift de visibilidade para ${actor}`).toEqual(expectedVisible);
    },
  );
});

describe('AppSidebar — children de Dashboards por perfil', () => {
  test.each(ACTORS)(
    '$actor: children de Dashboards batem com matriz',
    ({ actor, permissions, policies, expectedDashboardsChildren }) => {
      renderSidebar(permissions, policies);
      const actual = getDashboardsChildren();
      expect(actual, `Drift de children Dashboards para ${actor}`).toEqual(
        expectedDashboardsChildren,
      );
    },
  );
});

describe('AppSidebar — children de DAT por perfil', () => {
  test.each(ACTORS)(
    '$actor: children de DAT batem com matriz',
    ({ actor, permissions, policies, expectedDatChildren }) => {
      renderSidebar(permissions, policies);
      const actual = getDatChildren();
      expect(actual, `Drift de children DAT para ${actor}`).toEqual(expectedDatChildren);
    },
  );
});

// ============================================================================
// Sanity / Aprovações policy-only (cobertura especial PR 10)
// ============================================================================

describe('AppSidebar — sanity da matriz', () => {
  test('cada item top-level tem ≥1 ator que vê', () => {
    for (const item of TOP_LEVEL_ITEMS) {
      const anyShows = ACTORS.some((a) => a.expectedVisible.includes(item));
      expect(anyShows, `Item "${item}" nunca aparece em nenhum ator`).toBe(true);
    }
  });

  test('cada item top-level tem ≥1 ator que NÃO vê (exceto sempre-visíveis)', () => {
    const ALWAYS_VISIBLE: readonly TopLevelItem[] = ['Página Inicial', 'Meus Eventos'];
    for (const item of TOP_LEVEL_ITEMS) {
      if (ALWAYS_VISIBLE.includes(item)) continue;
      const anyHides = ACTORS.some((a) => !a.expectedVisible.includes(item));
      expect(anyHides, `Item "${item}" aparece para todos os atores (deveria ser sempre-visível?)`).toBe(true);
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

describe('AppSidebar — Aprovações é policy-only (PR 10 hardening RBAC)', () => {
  test('legacy canApproveSuper=true sem policy → Aprovações ESCONDIDA', () => {
    // Garante que o regression do PR 10 (#1315) não regrediu: o frontend não
    // deve consultar `permissions.canApproveSuper`. Mesmo com a flag legacy
    // setada, sem `access_solicitation_approvals` o item não aparece.
    renderSidebar(
      {
        ...EMPTY_PERMISSIONS,
        canApproveSuper: true, // legacy — não deve influenciar
        inSuperintendencia: true,
        isGerente: true,
        canSeeAllSectors: true,
      },
      [], // policy ausente
    );
    expect(screen.queryByRole('link', { name: /^Aprovações$/i })).not.toBeInTheDocument();
  });

  test('policy access_solicitation_approvals sem flag legacy → Aprovações VISÍVEL', () => {
    renderSidebar(EMPTY_PERMISSIONS, ['access_solicitation_approvals']);
    expect(screen.getByRole('link', { name: /^Aprovações$/i })).toBeInTheDocument();
  });
});
