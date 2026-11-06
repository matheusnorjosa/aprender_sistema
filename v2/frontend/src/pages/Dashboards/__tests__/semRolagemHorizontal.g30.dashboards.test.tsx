/**
 * G30 (Programa C) — Dashboards sem rolagem horizontal.
 *
 * As tabelas tinham `scroll.x` (800 ou max-content) e rolavam de lado. Agora são o ResponsiveTable:
 * a identidade e o número principal ficam na linha, o resto sobe por largura (VISIVEL_A_PARTIR) e o
 * que some vai para a linha expandida. Junto: o Drawer de detalhe do Google Calendar ocupa a tela
 * no celular (eram 720 px fixos), os botões do cabeçalho quebram linha e os cartões de indicador de
 * Compras só ficam 5 por linha a partir de 1600 px (na largura de 1/6 o título era cortado).
 */
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import type { JSX } from 'react';
import { MemoryRouter } from 'react-router';
import { describe, expect, test, vi } from 'vitest';

import { definirLarguraTela } from '../../../test/larguraTela';

vi.mock('../../../api/dashboard', () => ({
  getDashboardOverview: vi.fn().mockResolvedValue({
    kpis: { eventos_futuros: 1, eventos_aprovados: 1, total_formadores: 1, aprovacoes_pendentes: 0 },
    por_fluxo: [],
    por_gerencia: [],
    top_coordenadores: [{ nome: 'Maria Coordenadora', eventos: 5 }],
  }),
}));

vi.mock('../../../api/teamMetrics', () => ({
  getTeamProductivity: vi.fn().mockResolvedValue({
    period: '7d', events_created: 1, approval_rate: 1, avg_approval_time_hours: 1, gcal_error_rate: 0,
  }),
  getTeamFormadores: vi.fn().mockResolvedValue({
    period: '7d',
    formadores: [{ id: 3, nome: 'Rita Formadora', eventos: 4, horas_trabalhadas: 12, municipios_atendidos: 2 }],
  }),
  getTeamQuality: vi.fn().mockResolvedValue({
    period: '7d', rejection_rate: 0, conflict_rate: 0, rework_rate: 0, avg_publish_time_minutes: 1,
  }),
}));

vi.mock('../../../api/gcal', () => ({
  getDashboardMetrics: vi.fn().mockResolvedValue({ counts: {}, recent_errors: [] }),
  listDashboardEvents: vi.fn().mockResolvedValue({
    count: 1,
    results: [
      { id: 7, summary: 'Formação em Sobral', gcal_status: 'PUBLISHED', gcal_last_sync_at: null, gcal_last_error: null },
    ],
  }),
  getDashboardSuccessRate: vi.fn().mockResolvedValue({ published: 0, error: 0, pending: 0, none: 0, rate: 0 }),
  getDashboardTopInsights: vi.fn().mockResolvedValue({
    items: [{ name: 'Sobral', count: 3, published: 2, error: 1, rate: 0.66 }],
    metric: 'municipios',
    limit: 5,
  }),
  getDashboardEventDetail: vi.fn().mockResolvedValue({
    id: 7, municipio_nome: 'Sobral', projeto_nome: 'Projeto', tipo_evento_nome: 'Formação', inicio: null, fim: null,
    usuario_nome: 'Operadora', coordenador_nome: null, fluxo: 'NAO_SUPER', gcal_status: 'PUBLISHED',
    external_event_id: 'abc', gcal_last_sync_at: null, meet_link: null, gcal_last_error: null, updated_at: null,
    participations: [], timeline: [],
  }),
  reapplyBatch: vi.fn(),
  resyncBatch: vi.fn(),
  buildDashboardEventsExportUrl: vi.fn(),
}));

vi.mock('../../../api/datModule', () => ({
  getComprasDashboard: vi.fn().mockResolvedValue({
    kpis: {
      municipios_atendidos: 1, total_municipios_referencia: 10, cobertura_percentual: 10, total_itens: 5,
      total_entregue: 0, total_disponivel: 5, produtos_diferentes: 1, colecoes_diferentes: 1,
    },
    por_colecao: [],
    top_produtos: [],
    top_municipios: [{ municipio: 'Crato', uf: 'CE', quantidade: 9, entregues: 3, compras: 2 }],
    top_frequencia: [],
    por_ano: [],
    por_tipo_compra: [],
  }),
  getComprasPendencias: vi.fn().mockResolvedValue({
    total_com_compra: 1, total_com_evento: 0, total_pendentes: 1, percentual_pendentes: 100,
    pendentes: [
      {
        municipio_id: 1, municipio: 'Iguatu', uf: 'CE', projeto_id: 2, projeto: 'Projeto Pendente',
        total_itens: 4, total_compras: 1, ultima_compra: '2026-10-01',
      },
    ],
  }),
  getProdutosOptions: vi.fn().mockResolvedValue([]),
  getProjetosOptions: vi.fn().mockResolvedValue([]),
}));

import DashboardsPage from '../DashboardsPage';
import EquipeDashboardPage from '../EquipeDashboardPage';
import GCalDashboardPage from '../GCalDashboardPage';
import ComprasDashboardPage from '../ComprasDashboardPage';

vi.setConfig({ testTimeout: 30_000 });

function renderPagina(pagina: JSX.Element): ReturnType<typeof render> {
  return render(<MemoryRouter>{pagina}</MemoryRouter>);
}

/** Cabeçalhos da tabela que contém `celula` (sem a coluna do botão de expandir). */
function cabecalhosDe(celula: HTMLElement): string[] {
  const tabela = celula.closest('table');
  if (!tabela) throw new Error('o texto não está numa tabela');
  return within(tabela)
    .getAllByRole('columnheader')
    .filter((th) => !th.classList.contains('ant-table-row-expand-icon-cell'))
    .map((th) => th.textContent?.trim() ?? '')
    .filter(Boolean);
}

/** Nada que force largura: sem scroll.x (overflow no contêiner), coluna fixa ou largura na tabela. */
/**
 * A tabela que monta depois da carga lê a largura no efeito de montagem (Grid.useBreakpoint do
 * AntD) e só então põe as colunas por prioridade: espera os cabeçalhos assentarem.
 */
async function esperarCabecalhos(achar: () => HTMLElement, esperado: string[]): Promise<void> {
  await waitFor(() => expect(cabecalhosDe(achar())).toEqual(esperado));
}

function semLarguraForcada(container: HTMLElement): void {
  expect(container.querySelector('.ant-table-cell-fix-right, .ant-table-cell-fix-left')).toBeNull();
  for (const conteudo of Array.from(container.querySelectorAll('.ant-table-content'))) {
    expect(conteudo.getAttribute('style') ?? '').not.toMatch(/overflow/);
  }
  for (const tabela of Array.from(container.querySelectorAll('table'))) expect(tabela.style.width).toBe('');
}

describe('Dashboards (/dashboards) sem rolagem horizontal (G30)', { timeout: 20000 }, () => {
  test('a 1280 px: Top 5 sem largura forçada, com posição, eventos e progresso', async () => {
    const { container } = renderPagina(<DashboardsPage />);
    const celula = await screen.findByText('Maria Coordenadora', {}, { timeout: 15000 });

    await esperarCabecalhos(() => celula, ['Posicao', 'Coordenador', 'Eventos', 'Progresso']);
    semLarguraForcada(container);
  });

  test('a 360 px: coordenador e eventos na linha; posição e progresso na linha expandida', async () => {
    definirLarguraTela(360);
    renderPagina(<DashboardsPage />);
    const celula = await screen.findByText('Maria Coordenadora', {}, { timeout: 15000 });

    await esperarCabecalhos(() => celula, ['Coordenador', 'Eventos']);
    fireEvent.click(screen.getByRole('button', { name: 'Expandir linha de Maria Coordenadora' }));
    const expandida = within(document.querySelector<HTMLElement>('.ant-table-expanded-row')!);
    expect(expandida.getByText('Posicao')).toBeInTheDocument();
    expect(expandida.getByText('Progresso')).toBeInTheDocument();
  });

  test('os botões do cabeçalho quebram linha', async () => {
    renderPagina(<DashboardsPage />);
    await screen.findByText('Maria Coordenadora', {}, { timeout: 15000 });

    expect(screen.getByRole('button', { name: /Exportar para CSV/ }).closest('header')).toHaveClass('flex-wrap');
    expect(screen.getByRole('button', { name: /Exportar para CSV/ }).closest('.ant-space')).toHaveStyle({ flexWrap: 'wrap' });
  });
});

describe('Dashboard da Equipe sem rolagem horizontal (G30)', { timeout: 20000 }, () => {
  test('a 1280 px: todas as colunas, sem largura forçada; o cabeçalho quebra linha', async () => {
    const { container } = renderPagina(<EquipeDashboardPage />);
    const celula = await screen.findByText('Rita Formadora', { selector: 'td, td *' }, { timeout: 15000 });

    await esperarCabecalhos(() => celula, ['#', 'Nome', 'Eventos', 'Horas', 'Municípios']);
    semLarguraForcada(container);
    expect(screen.getByRole('button', { name: /Exportar CSV/ }).closest('.ant-space')).toHaveStyle({ flexWrap: 'wrap' });
  });

  test('a 768 px (tabela na metade da tela): só posição, nome e eventos', async () => {
    definirLarguraTela(768);
    renderPagina(<EquipeDashboardPage />);
    const celula = await screen.findByText('Rita Formadora', { selector: 'td, td *' }, { timeout: 15000 });

    await esperarCabecalhos(() => celula, ['#', 'Nome', 'Eventos']);
  });
});

describe('Dashboard Google Calendar sem rolagem horizontal (G30)', { timeout: 20000 }, () => {
  test('a 1280 px: eventos e "os 5 com mais eventos" sem largura forçada', async () => {
    const { container } = renderPagina(<GCalDashboardPage />);
    const evento = await screen.findByText('Formação em Sobral', {}, { timeout: 15000 });
    const insight = await screen.findByText('Sobral', { selector: 'td, td *' });

    await esperarCabecalhos(() => evento, ['ID', 'Resumo', 'Status GCal', 'Última Sincronização', 'Erro']);
    await esperarCabecalhos(() => insight, ['Nome', 'Total', 'Publicados', 'Erros', 'Taxa (%)']);
    semLarguraForcada(container);
  });

  test('a 360 px: resumo e status na linha; o detalhe do evento ocupa a tela', async () => {
    definirLarguraTela(360);
    renderPagina(<GCalDashboardPage />);
    const evento = await screen.findByText('Formação em Sobral', {}, { timeout: 15000 });
    const insight = await screen.findByText('Sobral', { selector: 'td, td *' });

    await esperarCabecalhos(() => evento, ['Resumo', 'Status GCal']);
    await esperarCabecalhos(() => insight, ['Nome', 'Total', 'Taxa (%)']);

    fireEvent.click(evento);
    await waitFor(() => expect(document.querySelector('.ant-drawer-content-wrapper')).not.toBeNull());
    expect(document.querySelector<HTMLElement>('.ant-drawer-content-wrapper')!.style.width).toBe('100%');
  });

  test('a 1280 px o detalhe do evento continua com 720 px', async () => {
    renderPagina(<GCalDashboardPage />);
    fireEvent.click(await screen.findByText('Formação em Sobral', {}, { timeout: 15000 }));
    await waitFor(() => expect(document.querySelector('.ant-drawer-content-wrapper')).not.toBeNull());
    expect(document.querySelector<HTMLElement>('.ant-drawer-content-wrapper')!.style.width).toBe('720px');
  });
});

describe('Dashboard de Compras sem rolagem horizontal (G30)', { timeout: 20000 }, () => {
  test('a 1280 px: pendências e "quem compra mais" sem largura forçada', async () => {
    const { container } = renderPagina(<ComprasDashboardPage />);
    const pendente = await screen.findByText('Iguatu', {}, { timeout: 15000 });
    const comprador = screen.getByText('Crato');

    await esperarCabecalhos(() => pendente, ['Município', 'Projeto', 'Itens', 'Compras', 'Última compra']);
    await esperarCabecalhos(() => comprador, ['Município', 'Itens', 'Entregues', 'Compras', 'Comparativo']);
    semLarguraForcada(container);
  });

  test('a 360 px: só o município na linha; o resto na linha expandida', async () => {
    definirLarguraTela(360);
    renderPagina(<ComprasDashboardPage />);
    const pendente = await screen.findByText('Iguatu', {}, { timeout: 15000 });

    await esperarCabecalhos(() => pendente, ['Município']);
    await esperarCabecalhos(() => screen.getByText('Crato'), ['Município', 'Itens']);
  });

  test('os cartões de indicador só ficam 5 por linha a partir de xxl', async () => {
    renderPagina(<ComprasDashboardPage />);
    await screen.findByText('Iguatu', {}, { timeout: 15000 });

    const coluna = screen.getByText('Municípios atendidos').closest('.ant-col');
    expect(coluna).toHaveClass('ant-col-md-8', 'ant-col-xxl-4');
    expect(coluna).not.toHaveClass('ant-col-lg-4');
  });

  test('mudar a largura reorganiza as colunas', async () => {
    renderPagina(<ComprasDashboardPage />);
    await screen.findByText('Iguatu', {}, { timeout: 15000 });

    act(() => definirLarguraTela(768));
    await esperarCabecalhos(() => screen.getByText('Iguatu'), ['Município', 'Projeto', 'Itens']);
  });
});
