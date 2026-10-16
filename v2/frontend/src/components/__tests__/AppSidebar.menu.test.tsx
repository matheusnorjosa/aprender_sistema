/**
 * AppSidebar — Matriz Viva por perfil canônico (PR 11 hardening RBAC).
 *
 * Linha de base persona × menu para os 10 atores de `apps/core/rbac/matrix.py`
 * (`src/test/atoresRbac.ts`: payload de /me e policies medidas no backend). Cobre os
 * itens de topo, os filhos de Dashboards, DAT, Controle (Compras) e Solicitações.
 *
 * PR 7 das permissões: o menu decide só por policy (`AcessoContext`). Esta matriz foi
 * commitada verde com o código antigo e não mudou com a troca. As personas por vínculo
 * ("Ana" ≡ DAT, "Bruno" ≡ Controle) provam que quem recebe as mesmas policies vê o mesmo menu.
 */

import { useState } from 'react';
import { MemoryRouter } from 'react-router';
import { render, screen, within, fireEvent } from '@testing-library/react';
import { describe, expect, test, vi } from 'vitest';

import { AppSidebar } from '../AppSidebar';
import type { ModoSidebar } from '../../hooks/useResponsive';
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

/** Renderiza o menu com o acesso que o App monta (policies + superusuário). */
function renderSidebar(policies: readonly string[], superusuario = false): void {
  render(
    <MemoryRouter>
      <ComAcesso policies={policies} superusuario={superusuario}>
        <AppSidebar {...SIDEBAR_PROPS} />
      </ComAcesso>
    </MemoryRouter>,
  );
}

/** O menu da pessoa: só as policies e o superusuário do payload de /me contam. */
function renderSidebarDoAtor({ user, policies }: Pick<AtorRbac, 'user' | 'policies'>): void {
  renderSidebar(policies, user.is_superuser);
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
    // PR 10: o DAT é o administrador operacional (pacote final): Aprovações, Controle e Solicitações.
    // Sem Ações Internas. Bloqueios, Deslocamentos e Grade: view_all_availability e o grupo DAT.
    actor: 'DAT',
    expectedVisible: [
      'Página Inicial',
      'Meus Eventos',
      'Aprovações',
      'Bloqueios',
      'Controle',
      'Deslocamentos',
      'Dashboards',
      'DAT',
      'Grade Mensal',
      'Solicitações',
    ],
    // Sem Dashboard Geral (view_overview_dashboard é da Diretoria). O seed dá view_map_metrics ao DAT.
    expectedDashboardsChildren: ['Dashboard Compras', 'Dashboard Equipe', 'Dashboard GCal', 'Mapa do Brasil'],
    // Importação pela tela é só do superusuário (decisão do dono, 02/10/2026).
    expectedDatChildren: ['Administração', 'Cadastros', 'Registros de Turmas'],
    expectedControleChildren: TODO_O_CONTROLE,
    // Sem "Publicar na agenda" (é da Apoio de Coordenação, `publish_setor_solicitacao`).
    expectedSolicitacoesChildren: ['Minhas Solicitações', 'Nova Solicitação'],
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
    // D8: Diretoria fora da Grade Mensal; só dashboards. PR 10 (02/10, nº 13): fora do painel do Google.
    actor: 'Diretoria',
    expectedVisible: ['Página Inicial', 'Meus Eventos', 'Dashboards'],
    expectedDashboardsChildren: ['Dashboard Geral', 'Dashboard Compras', 'Dashboard Equipe', 'Mapa do Brasil'],
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
  test('policy access_solicitation_approvals → Aprovações VISÍVEL', () => {
    renderSidebar(['access_solicitation_approvals']);
    expect(screen.getByRole('link', { name: /^Aprovações$/i })).toBeInTheDocument();
  });

  test('sem a policy → Aprovações ESCONDIDA', () => {
    renderSidebar([]);
    expect(screen.queryByRole('link', { name: /^Aprovações$/i })).not.toBeInTheDocument();
  });
});

// ============================================================================
// PR 7: setor, função e vínculo do /me não abrem item; quem tem as mesmas policies vê o mesmo menu
// ============================================================================

describe('AppSidebar — personas por vínculo ≡ grupo (PR 7)', () => {
  test.each(PERSONAS_POR_VINCULO)('$ator vê o mesmo menu que $equivale', ({ user, policies, equivale }) => {
    const esperado = ACTORS.find((a) => a.actor === equivale)!;
    renderSidebarDoAtor({ user, policies });
    expect(TOP_LEVEL_ITEMS.filter(isTopLevelVisible)).toEqual(esperado.expectedVisible);
  });

  test.each(PERSONAS_POR_VINCULO)('$ator: filhos de DAT e Controle iguais aos de $equivale', ({ user, policies, equivale }) => {
    const esperado = ACTORS.find((a) => a.actor === equivale)!;
    renderSidebarDoAtor({ user, policies });
    expect(filhosDoSubmenu('DAT', DAT_CHILDREN)).toEqual(esperado.expectedDatChildren);
    expect(filhosDoSubmenu('Controle', CONTROLE_CHILDREN)).toEqual(esperado.expectedControleChildren);
  });

  test('o payload de /me (grupos, vínculo, can_approve_super) sozinho não abre nada', () => {
    // Gerente da Superintendência inteiro no /me, nenhuma policy: só os itens de todos.
    const { user } = atorRbac('Gerente da Superintendência');
    renderSidebarDoAtor({ user, policies: [] });
    expect(TOP_LEVEL_ITEMS.filter(isTopLevelVisible)).toEqual(['Página Inicial', 'Meus Eventos']);
  });
});

// ============================================================================
// Solicitações → "Publicar na agenda" (#1656, policy publish_setor_solicitacao)
// ============================================================================

describe('AppSidebar — "Publicar na agenda" (#1656)', () => {
  const APOIO_POLICIES = ['create_solicitation', 'publish_setor_solicitacao'];

  test('Apoio de Coordenação vê Minhas, Nova e Publicar na agenda (→ /solicitacoes/publicacao)', () => {
    renderSidebar(APOIO_POLICIES);
    expect(getSolicitacoesChildren()).toEqual(SOLICITACOES_CHILDREN);
    expect(
      screen.getByRole('link', { name: /^Publicar na agenda$/i }).getAttribute('href'),
    ).toBe('/solicitacoes/publicacao');
  });

  test('Coordenador (só create_solicitation) continua com Minhas e Nova', () => {
    renderSidebar(['create_solicitation']);
    expect(getSolicitacoesChildren()).toEqual(['Minhas Solicitações', 'Nova Solicitação']);
  });

  test('só publish_setor_solicitacao: o submenu aparece, só com Publicar na agenda', () => {
    renderSidebar(['publish_setor_solicitacao']);
    expect(isTopLevelVisible('Solicitações')).toBe(true);
    expect(getSolicitacoesChildren()).toEqual(['Publicar na agenda']);
  });

  test('deep-link em /solicitacoes/publicacao abre o submenu e seleciona o item', () => {
    render(
      <MemoryRouter initialEntries={['/solicitacoes/publicacao']}>
        <ComAcesso policies={APOIO_POLICIES}>
          <AppSidebar {...SIDEBAR_PROPS} />
        </ComAcesso>
      </MemoryRouter>,
    );
    const link = screen.getByRole('link', { name: /^Publicar na agenda$/i });
    expect(link.closest('li')?.className).toContain('ant-menu-item-selected');
  });
});

describe('AppSidebar — Ações Internas é policy-only (Issue #1263)', () => {
  test('sem manage_internal_actions → Ações Internas ESCONDIDA (mesmo para DAT)', () => {
    // Bug #1263: o grupo mostrava o menu, mas o backend exige a policy (0 grupos no seed).
    renderSidebarDoAtor(atorRbac('DAT'));
    expect(isTopLevelVisible('Ações Internas')).toBe(false);
  });

  test('policy manage_internal_actions → Ações Internas VISÍVEL', () => {
    renderSidebar(['manage_internal_actions']);
    expect(isTopLevelVisible('Ações Internas')).toBe(true);
  });
});

describe('AppSidebar — telas de escopo pela policy (PR 7)', () => {
  test.each([
    ['access_monthly_availability', 'Grade Mensal'],
    ['access_availability_blocks', 'Bloqueios'],
    ['access_travel', 'Deslocamentos'],
  ] as const)('%s → %s visível, e só ela', (policy, item) => {
    renderSidebar([policy]);
    expect(TOP_LEVEL_ITEMS.filter(isTopLevelVisible)).toEqual(['Página Inicial', 'Meus Eventos', item]);
  });

  test('vínculo de gestão no /me sem as policies → nenhuma das três', () => {
    // O servidor já soma o vínculo nas policies (access_*); a tela não relê o payload.
    const user = usuarioDeTeste({ gerencias: [{ id: 4, rotulo: 'Superativar', papeis: ['COORDENADOR'] }] });
    renderSidebarDoAtor({ user, policies: [] });
    expect(isTopLevelVisible('Grade Mensal')).toBe(false);
    expect(isTopLevelVisible('Bloqueios')).toBe(false);
    expect(isTopLevelVisible('Deslocamentos')).toBe(false);
  });

  test('Importações (DAT) é do superusuário, não da policy', () => {
    renderSidebar(['manage_admin_registries'], false);
    expect(filhosDoSubmenu('DAT', DAT_CHILDREN)).not.toContain('Importações');
  });
});

describe('AppSidebar — modo pela largura (Programa C, C1)', () => {
  /** Com estado de verdade: `toggleSidebar` muda `sidebarCollapsed`, como o `useResponsive` no App. */
  function SidebarComEstado({ modo, recolhidaInicial }: { modo: ModoSidebar; recolhidaInicial: boolean }) {
    const [recolhida, setRecolhida] = useState(recolhidaInicial);
    return (
      <ComAcesso policies={['manage_admin_registries']}>
        <AppSidebar
          {...SIDEBAR_PROPS}
          modo={modo}
          sidebarCollapsed={recolhida}
          toggleSidebar={() => setRecolhida((r) => !r)}
        />
      </ComAcesso>
    );
  }

  function renderModo(modo: 'sobreposta' | 'recolhida' | 'aberta', sidebarCollapsed: boolean, toggleSidebar = () => {}) {
    render(
      <MemoryRouter initialEntries={['/dat/admin/usuarios']}>
        <ComAcesso policies={['manage_admin_registries']}>
          <AppSidebar {...SIDEBAR_PROPS} modo={modo} sidebarCollapsed={sidebarCollapsed} toggleSidebar={toggleSidebar} />
        </ComAcesso>
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
        <ComAcesso policies={['manage_admin_registries']}>
          <AppSidebar {...SIDEBAR_PROPS} modo="sobreposta" sidebarCollapsed={false} toggleSidebar={toggle} />
        </ComAcesso>
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
    const { rerender } = render(
      <MemoryRouter initialEntries={['/dat/admin/usuarios']}>
        <ComAcesso policies={['manage_admin_registries']}>
          <AppSidebar {...SIDEBAR_PROPS} modo="recolhida" sidebarCollapsed />
        </ComAcesso>
      </MemoryRouter>,
    );
    expect(screen.queryByRole('link', { name: 'Administração' })).not.toBeInTheDocument();

    rerender(
      <MemoryRouter initialEntries={['/dat/admin/usuarios']}>
        <ComAcesso policies={['manage_admin_registries']}>
          <AppSidebar {...SIDEBAR_PROPS} modo="recolhida" sidebarCollapsed={false} />
        </ComAcesso>
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
