/**
 * AppSidebar — Matriz Viva por perfil canônico (PR 11 hardening RBAC).
 *
 * Linha de base persona × menu para os 10 atores de `apps/core/rbac/matrix.py`
 * (`src/test/atoresRbac.ts`: payload de /me e policies medidas no backend). Cobre os
 * itens de topo, os filhos de Dashboards, DAT, Controle (Compras) e Solicitações.
 *
 * PR 7 das permissões: o menu passa a decidir só por policy. Esta matriz foi
 * commitada verde com o código antigo; depois da troca ela não pode mudar.
 */

import { useState } from 'react';
import { MemoryRouter } from 'react-router';
import { render, screen, within, fireEvent } from '@testing-library/react';
import { describe, expect, test, vi } from 'vitest';

import { AppSidebar } from '../AppSidebar';
import type { Permissions } from '../../hooks/usePermissions';
import { computePermissions } from '../../hooks/usePermissions';
import type { ModoSidebar } from '../../hooks/useResponsive';
import { ATORES_RBAC, atorRbac, type AtorRbac, type NomeDoAtor } from '../../test/atoresRbac';

// ============================================================================
// Setup
// ============================================================================

const COLORS = { sidebarBackground: '#001529', borderLight: '#303030' };

const SIDEBAR_PROPS = {
  gcalErrorCount: 0,
  unreadNotifications: 0,
  modo: 'aberta' as const,
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
  isGestorPorVinculo: false,
  canSeeAllSectors: false,
};

function renderSidebar(permissions: Permissions, policies: readonly string[]): void {
  render(
    <MemoryRouter>
      <AppSidebar permissions={permissions} policies={policies} {...SIDEBAR_PROPS} />
    </MemoryRouter>,
  );
}

/** Renderiza o menu como o App o monta para a pessoa (payload de /me + /me/policies). */
function renderSidebarDoAtor({ user, policies }: Pick<AtorRbac, 'user' | 'policies'>): void {
  renderSidebar(computePermissions(user), policies);
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

/** Filhos do submenu Dashboards (cada um tem condição própria). */
const DASHBOARDS_CHILDREN = [
  'Dashboard Geral',
  'Dashboard Compras',
  'Dashboard Equipe',
  'Dashboard GCal',
  'Mapa do Brasil',
] as const;

type DashboardsChild = (typeof DASHBOARDS_CHILDREN)[number];

const DAT_CHILDREN = ['Administração', 'Cadastros', 'Importações', 'Registros de Turmas'] as const;
const CONTROLE_CHILDREN = ['Ações', 'Compras', 'Coordenadores', 'Painel de Controle', 'Plano Anual', 'Pré-agenda'] as const;
const SOLICITACOES_CHILDREN = ['Minhas Solicitações', 'Nova Solicitação', 'Publicar na agenda'] as const;

interface ActorSnapshot {
  actor: NomeDoAtor;
  /** Subset literal de TOP_LEVEL_ITEMS visível para este ator. */
  expectedVisible: readonly TopLevelItem[];
  /** Filhos visíveis dentro de cada submenu. `[]` quando o submenu não aparece. */
  expectedDashboardsChildren: readonly DashboardsChild[];
  expectedDatChildren: readonly (typeof DAT_CHILDREN)[number][];
  expectedControleChildren: readonly (typeof CONTROLE_CHILDREN)[number][];
  expectedSolicitacoesChildren: readonly (typeof SOLICITACOES_CHILDREN)[number][];
}

const TODO_O_CONTROLE = [...CONTROLE_CHILDREN];

const ACTORS: ActorSnapshot[] = [
  {
    actor: 'Superuser',
    expectedVisible: [...TOP_LEVEL_ITEMS],
    expectedDashboardsChildren: [...DASHBOARDS_CHILDREN],
    expectedDatChildren: [...DAT_CHILDREN],
    expectedControleChildren: TODO_O_CONTROLE,
    expectedSolicitacoesChildren: [...SOLICITACOES_CHILDREN],
  },
  {
    // Sem Aprovações, Controle, Ações Internas e Solicitações (nenhuma dessas policies).
    // Bloqueios, Deslocamentos e Grade: view_all_availability e o grupo DAT.
    actor: 'DAT',
    expectedVisible: [
      'Página Inicial',
      'Meus Eventos',
      'Bloqueios',
      'Deslocamentos',
      'Dashboards',
      'DAT',
      'Grade Mensal',
    ],
    // Sem Dashboard Geral (view_overview_dashboard é da Diretoria). O seed dá view_map_metrics ao DAT.
    expectedDashboardsChildren: ['Dashboard Compras', 'Dashboard Equipe', 'Dashboard GCal', 'Mapa do Brasil'],
    // Importação pela tela é só do superusuário (decisão do dono, 02/10/2026).
    expectedDatChildren: ['Administração', 'Cadastros', 'Registros de Turmas'],
    expectedControleChildren: [],
    expectedSolicitacoesChildren: [],
  },
  {
    actor: 'Controle',
    expectedVisible: [
      'Página Inicial',
      'Meus Eventos',
      'Bloqueios',
      'Controle',
      'Deslocamentos',
      'Dashboards',
      'Grade Mensal',
    ],
    expectedDashboardsChildren: ['Dashboard GCal'],
    expectedDatChildren: [],
    expectedControleChildren: TODO_O_CONTROLE,
    expectedSolicitacoesChildren: [],
  },
  {
    // D8: Diretoria fora da Grade Mensal; só dashboards.
    actor: 'Diretoria',
    expectedVisible: ['Página Inicial', 'Meus Eventos', 'Dashboards'],
    expectedDashboardsChildren: [...DASHBOARDS_CHILDREN],
    expectedDatChildren: [],
    expectedControleChildren: [],
    expectedSolicitacoesChildren: [],
  },
  {
    // Vínculo GERENTE vigente: Bloqueios, Deslocamentos e Grade (PR A).
    actor: 'Gerente da Superintendência',
    expectedVisible: [
      'Página Inicial',
      'Meus Eventos',
      'Aprovações',
      'Bloqueios',
      'Deslocamentos',
      'Grade Mensal',
      'Solicitações',
    ],
    expectedDashboardsChildren: [],
    expectedDatChildren: [],
    expectedControleChildren: [],
    expectedSolicitacoesChildren: ['Minhas Solicitações', 'Nova Solicitação'],
  },
  {
    actor: 'Gerente pedagógico (Vidas)',
    expectedVisible: [
      'Página Inicial',
      'Meus Eventos',
      'Bloqueios',
      'Deslocamentos',
      'Grade Mensal',
      'Solicitações',
    ],
    expectedDashboardsChildren: [],
    expectedDatChildren: [],
    expectedControleChildren: [],
    expectedSolicitacoesChildren: ['Minhas Solicitações', 'Nova Solicitação'],
  },
  {
    actor: 'Coordenador',
    expectedVisible: [
      'Página Inicial',
      'Meus Eventos',
      'Bloqueios',
      'Deslocamentos',
      'Grade Mensal',
      'Solicitações',
    ],
    expectedDashboardsChildren: [],
    expectedDatChildren: [],
    expectedControleChildren: [],
    expectedSolicitacoesChildren: ['Minhas Solicitações', 'Nova Solicitação'],
  },
  {
    actor: 'Apoio de Coordenação',
    expectedVisible: [
      'Página Inicial',
      'Meus Eventos',
      'Bloqueios',
      'Deslocamentos',
      'Grade Mensal',
      'Solicitações',
    ],
    expectedDashboardsChildren: [],
    expectedDatChildren: [],
    expectedControleChildren: [],
    // #1656: a Apoio publica na agenda os aprovados do próprio setor.
    expectedSolicitacoesChildren: [...SOLICITACOES_CHILDREN],
  },
  {
    // RD-02/03: o Formador declara o próprio bloqueio; fora da Grade (D8).
    actor: 'Formador',
    expectedVisible: ['Página Inicial', 'Meus Eventos', 'Bloqueios'],
    expectedDashboardsChildren: [],
    expectedDatChildren: [],
    expectedControleChildren: [],
    expectedSolicitacoesChildren: [],
  },
  {
    actor: 'Assistente Administrativo Controle',
    expectedVisible: [
      'Página Inicial',
      'Meus Eventos',
      'Aprovações',
      'Bloqueios',
      'Controle',
      'Deslocamentos',
      'Dashboards',
      'Grade Mensal',
    ],
    expectedDashboardsChildren: ['Dashboard GCal'],
    expectedDatChildren: [],
    expectedControleChildren: TODO_O_CONTROLE,
    expectedSolicitacoesChildren: [],
  },
];

const renderAtor = (nome: NomeDoAtor): void => renderSidebarDoAtor(atorRbac(nome));


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

/** Filhos visíveis de um submenu (abre o submenu; `[]` quando ele não aparece). */
function filhosDoSubmenu(titulo: string, filhos: readonly string[]): string[] {
  if (!openSubmenuByTitle(titulo)) return [];
  return filhos.filter((label) => screen.queryByRole('link', { name: new RegExp(`^${label}$`, 'i') }) !== null);
}

function getDashboardsChildren(): string[] {
  return filhosDoSubmenu('Dashboards', DASHBOARDS_CHILDREN);
}

function getSolicitacoesChildren(): string[] {
  return filhosDoSubmenu('Solicitações', SOLICITACOES_CHILDREN);
}

// ============================================================================
// Tests parametrizados
// ============================================================================

describe('AppSidebar — visibilidade top-level por perfil', () => {
  test.each(ACTORS)('$actor: top-level visíveis batem com matriz canônica', ({ actor, expectedVisible }) => {
    renderAtor(actor);
    const actualVisible = TOP_LEVEL_ITEMS.filter(isTopLevelVisible);
    expect(actualVisible, `Drift de visibilidade para ${actor}`).toEqual(expectedVisible);
  });
});

describe('AppSidebar — filhos dos submenus por perfil', () => {
  test.each(ACTORS)('$actor: filhos de Dashboards', ({ actor, expectedDashboardsChildren }) => {
    renderAtor(actor);
    expect(getDashboardsChildren(), `Drift de Dashboards para ${actor}`).toEqual(expectedDashboardsChildren);
  });

  test.each(ACTORS)('$actor: filhos de DAT', ({ actor, expectedDatChildren }) => {
    renderAtor(actor);
    expect(filhosDoSubmenu('DAT', DAT_CHILDREN), `Drift de DAT para ${actor}`).toEqual(expectedDatChildren);
  });

  test.each(ACTORS)('$actor: filhos de Controle (Compras)', ({ actor, expectedControleChildren }) => {
    renderAtor(actor);
    expect(filhosDoSubmenu('Controle', CONTROLE_CHILDREN), `Drift de Controle para ${actor}`).toEqual(
      expectedControleChildren,
    );
  });

  test.each(ACTORS)('$actor: filhos de Solicitações', ({ actor, expectedSolicitacoesChildren }) => {
    renderAtor(actor);
    expect(getSolicitacoesChildren(), `Drift de Solicitações para ${actor}`).toEqual(expectedSolicitacoesChildren);
  });
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
    expect(new Set(ACTORS.map((a) => a.actor))).toEqual(expected);
    expect(new Set(ATORES_RBAC.map((a) => a.ator))).toEqual(expected);
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

// ============================================================================
// Solicitações → "Publicar na agenda" (#1656, policy publish_setor_solicitacao)
// ============================================================================

describe('AppSidebar — "Publicar na agenda" (#1656)', () => {
  // usePermissions trata Apoio igual a Coordenador; a diferença está na policy.
  const APOIO_PERMISSIONS: Permissions = {
    ...EMPTY_PERMISSIONS,
    isCoordenador: true,
    canCoordenador: true,
    canAcoesInternas: true,
    canDisponibilidade: true,
  };
  const APOIO_POLICIES = ['create_solicitation', 'publish_setor_solicitacao'];

  test('Apoio de Coordenação vê Minhas, Nova e Publicar na agenda (→ /solicitacoes/publicacao)', () => {
    renderSidebar(APOIO_PERMISSIONS, APOIO_POLICIES);
    expect(getSolicitacoesChildren()).toEqual(SOLICITACOES_CHILDREN);
    expect(
      screen.getByRole('link', { name: /^Publicar na agenda$/i }).getAttribute('href'),
    ).toBe('/solicitacoes/publicacao');
  });

  test('Coordenador (só create_solicitation) continua com Minhas e Nova', () => {
    renderSidebar(APOIO_PERMISSIONS, ['create_solicitation']);
    expect(getSolicitacoesChildren()).toEqual(['Minhas Solicitações', 'Nova Solicitação']);
  });

  test('só publish_setor_solicitacao: o submenu aparece, só com Publicar na agenda', () => {
    renderSidebar(EMPTY_PERMISSIONS, ['publish_setor_solicitacao']);
    expect(isTopLevelVisible('Solicitações')).toBe(true);
    expect(getSolicitacoesChildren()).toEqual(['Publicar na agenda']);
  });

  test('deep-link em /solicitacoes/publicacao abre o submenu e seleciona o item', () => {
    render(
      <MemoryRouter initialEntries={['/solicitacoes/publicacao']}>
        <AppSidebar permissions={APOIO_PERMISSIONS} policies={APOIO_POLICIES} {...SIDEBAR_PROPS} />
      </MemoryRouter>,
    );
    const link = screen.getByRole('link', { name: /^Publicar na agenda$/i });
    expect(link.closest('li')?.className).toContain('ant-menu-item-selected');
  });
});

describe('AppSidebar — Ações Internas é policy-only (Issue #1263)', () => {
  test('legacy canAcoesInternas=true sem policy → Ações Internas ESCONDIDA', () => {
    // Bug #1263: a flag legacy por grupo mostrava o menu para DAT/Coordenador/
    // Gerente, mas o backend exige `manage_internal_actions` (0 grupos no seed).
    // Sem a policy, o item some — alinhando frontend e backend (fim do menu→403).
    renderSidebar(
      { ...EMPTY_PERMISSIONS, canAcoesInternas: true, inDAT: true, canCoordenador: true },
      [], // policy ausente
    );
    expect(isTopLevelVisible('Ações Internas')).toBe(false);
  });

  test('policy manage_internal_actions sem flag legacy → Ações Internas VISÍVEL', () => {
    renderSidebar(EMPTY_PERMISSIONS, ['manage_internal_actions']);
    expect(isTopLevelVisible('Ações Internas')).toBe(true);
  });
});

describe('AppSidebar — gestor só por vínculo (PR A)', () => {
  test('vínculo de gestão sem grupo → Grade Mensal, Bloqueios e Deslocamentos visíveis', () => {
    // Espelha as rotas (AppRoutes): o backend escopa por vínculo EquipeGerencia.
    renderSidebar({ ...EMPTY_PERMISSIONS, isGestorPorVinculo: true, canDisponibilidade: true }, []);
    expect(isTopLevelVisible('Grade Mensal')).toBe(true);
    expect(isTopLevelVisible('Bloqueios')).toBe(true);
    expect(isTopLevelVisible('Deslocamentos')).toBe(true);
    expect(isTopLevelVisible('Aprovações')).toBe(false);
  });
});

describe('AppSidebar — modo pela largura (Programa C, C1)', () => {
  /** Com estado de verdade: `toggleSidebar` muda `sidebarCollapsed`, como o `useResponsive` no App. */
  function SidebarComEstado({ modo, recolhidaInicial }: { modo: ModoSidebar; recolhidaInicial: boolean }) {
    const [recolhida, setRecolhida] = useState(recolhidaInicial);
    return (
      <AppSidebar
        permissions={EMPTY_PERMISSIONS}
        policies={['manage_admin_registries']}
        {...SIDEBAR_PROPS}
        modo={modo}
        sidebarCollapsed={recolhida}
        toggleSidebar={() => setRecolhida((r) => !r)}
      />
    );
  }

  function renderModo(modo: 'sobreposta' | 'recolhida' | 'aberta', sidebarCollapsed: boolean, toggleSidebar = () => {}) {
    render(
      <MemoryRouter initialEntries={['/dat/admin/usuarios']}>
        <AppSidebar
          permissions={EMPTY_PERMISSIONS}
          policies={['manage_admin_registries']}
          {...SIDEBAR_PROPS}
          modo={modo}
          sidebarCollapsed={sidebarCollapsed}
          toggleSidebar={toggleSidebar}
        />
      </MemoryRouter>,
    );
  }

  test('recolhida (992–1279 px): só ícones, marca curta, e o submenu do item atual não abre sozinho', () => {
    renderModo('recolhida', true);
    const nav = screen.getByRole('navigation', { name: 'Navegacao principal' });
    expect(within(nav).getByText('AS')).toHaveAttribute('aria-hidden', 'true');
    expect(within(nav).getByText('Aprender Sistema')).toHaveClass('sr-only');
    expect(within(nav).getByRole('menu')).toHaveClass('ant-menu-inline-collapsed');
    // aberto, o flyout de "DAT" cobriria o conteúdo ao carregar a página
    expect(screen.queryByRole('link', { name: 'Administração' })).not.toBeInTheDocument();
    expect(document.querySelector('.mobile-sidebar-overlay')).toBeNull();
  });

  test('recolhida e aberta pelo botão: fica por cima do conteúdo, com fundo que fecha', () => {
    const toggle = vi.fn();
    renderModo('recolhida', false, toggle);
    const fundo = document.querySelector<HTMLElement>('.mobile-sidebar-overlay');
    expect(fundo).not.toBeNull();
    fireEvent.click(fundo!);
    expect(toggle).toHaveBeenCalledTimes(1);
  });

  test('sobreposta e fechada (< 992 px): nenhum item de menu na tela', () => {
    renderModo('sobreposta', true);
    expect(screen.queryByRole('menu')).not.toBeInTheDocument();
    expect(screen.queryByText('AS')).not.toBeInTheDocument();
  });

  test('sobreposta e aberta: escolher um item fecha a sidebar (uma vez só, mesmo mudando de rota)', () => {
    // Com estado de verdade: um espião contaria também o fechamento pela troca de rota,
    // que no App não acontece porque a sidebar já fechou pelo clique.
    render(
      <MemoryRouter initialEntries={['/dat/admin/usuarios']}>
        <SidebarComEstado modo="sobreposta" recolhidaInicial={false} />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole('link', { name: 'Página Inicial' }));
    expect(screen.queryByRole('menu')).not.toBeInTheDocument();
    expect(document.querySelector('.mobile-sidebar-overlay')).toBeNull();
  });

  test('sobreposta e aberta: o clique (mouse) no item fecha uma vez; o Enter (keydown) não chama o toggle', () => {
    // Na rota do próprio item a troca de rota não fecha: só o onItemClick pode fechar.
    const toggle = vi.fn();
    render(
      <MemoryRouter initialEntries={['/home']}>
        <AppSidebar
          permissions={EMPTY_PERMISSIONS}
          policies={['manage_admin_registries']}
          {...SIDEBAR_PROPS}
          modo="sobreposta"
          sidebarCollapsed={false}
          toggleSidebar={toggle}
        />
      </MemoryRouter>,
    );
    const inicio = screen.getByRole('link', { name: 'Página Inicial' });

    // O rc-menu chama o onClick do Menu já no keydown do Enter; fechar ali tiraria o foco do
    // <a> antes da ação padrão (o link não navegaria). Quem fecha é o clique que o <a> gera.
    fireEvent.keyDown(inicio, { key: 'Enter', code: 'Enter', keyCode: 13, which: 13 });
    expect(toggle).not.toHaveBeenCalled();

    fireEvent.click(inicio);
    expect(toggle).toHaveBeenCalledTimes(1);
  });

  test('recolhida → expandida: abre o submenu da página atual', () => {
    const props = { permissions: EMPTY_PERMISSIONS, policies: ['manage_admin_registries'], ...SIDEBAR_PROPS };
    const { rerender } = render(
      <MemoryRouter initialEntries={['/dat/admin/usuarios']}>
        <AppSidebar {...props} modo="recolhida" sidebarCollapsed />
      </MemoryRouter>,
    );
    expect(screen.queryByRole('link', { name: 'Administração' })).not.toBeInTheDocument();

    rerender(
      <MemoryRouter initialEntries={['/dat/admin/usuarios']}>
        <AppSidebar {...props} modo="recolhida" sidebarCollapsed={false} />
      </MemoryRouter>,
    );

    expect(screen.getByRole('link', { name: 'Administração' })).toBeInTheDocument();
  });

  test('cada item de topo tem ícone próprio (na recolhida, só o ícone distingue os itens)', () => {
    renderAtor('Superuser');
    const nav = screen.getByRole('navigation', { name: 'Navegacao principal' });
    const raiz = within(nav).getAllByRole('menu')[0]!;
    const iconePorItem = Array.from(raiz.children)
      .filter((li) => li.matches('.ant-menu-item, .ant-menu-submenu'))
      .map((li) => {
        const icone = Array.from(li.querySelector('.anticon')?.classList ?? []).find((c) => c.startsWith('anticon-'));
        return `${(li.textContent ?? '').trim()}: ${icone ?? 'sem ícone'}`;
      });
    expect(iconePorItem).toHaveLength(TOP_LEVEL_ITEMS.length);
    const icones = iconePorItem.map((par) => par.split(': ')[1]);
    const repetidos = iconePorItem.filter((_, i) => icones.indexOf(icones[i]) !== i || icones.lastIndexOf(icones[i]) !== i);
    expect(repetidos).toEqual([]);
  });

  test('aberta (>= 1280 px): nome inteiro, sem fundo escuro, e escolher item não fecha', () => {
    const toggle = vi.fn();
    renderModo('aberta', false, toggle);
    expect(screen.getByText('Aprender Sistema')).not.toHaveClass('sr-only');
    expect(document.querySelector('.mobile-sidebar-overlay')).toBeNull();
    fireEvent.click(screen.getByRole('link', { name: 'Página Inicial' }));
    expect(toggle).not.toHaveBeenCalled();
  });
});
