/**
 * Aprovações sem rolagem horizontal (achado do item 36, 19/10/2026): lista enxuta no ResponsiveTable.
 *
 * No celular a coluna fixa Ações (220 px) cobria a tabela e a pessoa aprovava sem ver o evento.
 * Sempre na linha: o Evento (data e horário, município, projeto) e as ações (AcoesLinha, que leva
 * o evento no nome: "Aprovar: 25/08/2026 08:00 · Município · Projeto"). As demais sobem por largura e o
 * que some vai para a linha expandida. Sem `scroll.x` e sem coluna fixa.
 */
import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { MemoryRouter } from 'react-router';
import { ConfigProvider } from 'antd';

import { AcessoContext, montarAcesso } from '../../../contexts/AcessoContext';
import { definirLarguraTela } from '../../../test/larguraTela';
import type { PaginatedResponse, Solicitacao } from '../../../types';

vi.mock('../../../api/solicitacoes', () => ({
  listSolicitacoes: vi.fn(),
  approveSolicitacao: vi.fn(),
  rejectSolicitacao: vi.fn(),
  previewSolicitacao: vi.fn(),
  approveSolicitacoesBatch: vi.fn(),
  rejectSolicitacoesBatch: vi.fn(),
}));
vi.mock('../../../api/availability', () => ({ getMe: vi.fn().mockResolvedValue(null) }));
vi.mock('../../../hooks/usePolling', () => ({ usePolling: vi.fn(() => ({ pausado: false, pausar: vi.fn() })) }));

import ApprovalsPage from '../ApprovalsPage';
import { listSolicitacoes } from '../../../api/solicitacoes';

const EVENTO = '25/08/2026 10:00 · MunicipioTeste · ProjetoTeste';

function linhas(n: number): PaginatedResponse<Solicitacao> {
  return {
    count: n,
    next: null,
    previous: null,
    results: Array.from({ length: n }, (_, i) => ({
      id: i + 1,
      usuario: 5,
      municipio_nome: i === 0 ? 'MunicipioTeste' : `Municipio${i + 1}`,
      projeto_nome: 'ProjetoTeste',
      coordenador_nome: 'Coordenadora Teste',
      coordenador_acompanha: true,
      tipo: 'FORMACAO',
      encontro: null,
      segmento: null,
      inicio: '2026-08-25T13:00:00Z',
      fim: '2026-08-25T15:00:00Z',
      status: 'pendente',
      participations: [],
    })) as unknown as Solicitacao[],
  };
}

function renderPage(): ReturnType<typeof render> {
  return render(
    <AcessoContext.Provider value={montarAcesso(['access_solicitation_approvals'], null)}>
      <MemoryRouter>
        <ApprovalsPage />
      </MemoryRouter>
    </AcessoContext.Provider>,
  );
}

/** Títulos das colunas de dados (sem a da seleção e a do botão de expandir). */
function cabecalhos(): string[] {
  return screen
    .getAllByRole('columnheader')
    .filter((th) => !th.classList.contains('ant-table-row-expand-icon-cell') && !th.classList.contains('ant-table-selection-column'))
    .map((th) => th.textContent?.trim() ?? '')
    .filter(Boolean);
}

async function linhaDoEvento(acao: 'Aprovar' | 'Mais ações'): Promise<HTMLElement> {
  const botao = await screen.findByRole('button', { name: `${acao}: ${EVENTO}` }, { timeout: 15000 });
  const linha = botao.closest('tr');
  if (!linha) throw new Error('o botão não está numa linha da tabela');
  return linha;
}

/**
 * Fundo que o CSS-in-JS do AntD dá à célula da linha selecionada, parada ou com o mouse em cima.
 * O jsdom não aplica o CSS do AntD: o teste lê a regra gerada para o hash da própria tabela.
 */
function fundoDaLinhaSelecionada(linha: HTMLElement, comMouse: boolean): string {
  const hash = Array.from(linha.closest('.ant-table-wrapper')?.classList ?? []).find((c) => c.startsWith('css-'));
  const css = Array.from(document.querySelectorAll('style')).map((s) => s.textContent ?? '').join('').replace(/\s/g, '');
  const alvo = `.ant-table-row-selected>.ant-table-cell${comMouse ? '-row-hover' : ''}{`;
  const regra = css.split('}').find((r) => r.includes(`(.${hash})`) && r.includes(alvo));
  const cor = /background:(#[0-9a-f]{6})/i.exec(regra ?? '')?.[1];
  if (!cor) throw new Error(`sem regra de fundo para ${alvo} em .${hash}`);
  return cor;
}

function luminancia(hex: string): number {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
    .map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4)) as [number, number, number];
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contraste(a: string, b: string): number {
  const [claro, escuro] = [luminancia(a), luminancia(b)].sort((x, y) => y - x) as [number, number];
  return (claro + 0.05) / (escuro + 0.05);
}

describe('ApprovalsPage responsiva', () => {
  beforeEach(() => {
    vi.mocked(listSolicitacoes).mockResolvedValue(linhas(1));
  });

  test('a 1280 px: o evento e as ações na linha, sem coluna fixa nem rolagem', async () => {
    const { container } = renderPage();
    const linha = await linhaDoEvento('Aprovar');

    expect(cabecalhos()).toEqual(['Evento', 'Coordenador', 'Tipo/Enc./Seg.', 'Formadores', 'Status', 'Ações']);
    for (const texto of ['25/08/2026', 'MunicipioTeste', 'ProjetoTeste']) {
      expect(within(linha).getByText(texto, { exact: false })).toBeInTheDocument();
    }
    expect(within(linha).getByRole('button', { name: `Reprovar: ${EVENTO}` })).toBeInTheDocument();
    expect(within(linha).getByRole('button', { name: `Ver prévia do evento: ${EVENTO}` })).toBeInTheDocument();
    expect(container.querySelector('.ant-table-cell-fix-right, .ant-table-cell-fix-left')).toBeNull();
    expect(container.querySelector('.ant-table-content')?.getAttribute('style') ?? '').not.toMatch(/overflow/);
  }, 20000);

  test('a 360 px: só o evento e o menu de ações; o resto na linha expandida', async () => {
    definirLarguraTela(360);
    renderPage();
    const linha = await linhaDoEvento('Mais ações');

    expect(cabecalhos()).toEqual(['Evento', 'Ações']);
    // Data, município e projeto continuam ao lado das ações.
    for (const texto of ['25/08/2026', 'MunicipioTeste', 'ProjetoTeste']) {
      expect(within(linha).getByText(texto, { exact: false })).toBeInTheDocument();
    }

    // fireEvent: o Spin da carga pode estar com pointer-events none (o userEvent recusa).
    fireEvent.click(within(linha).getByRole('button', { name: `Expandir linha de ${EVENTO}` }));
    const expandida = within(document.querySelector<HTMLElement>('.ant-table-expanded-row')!);
    for (const texto of ['Coordenadora Teste', 'FORMACAO', 'Pendente']) {
      expect(expandida.getByText(texto)).toBeInTheDocument();
    }
  }, 20000);

  test('mudar a largura com a página aberta reorganiza as colunas', async () => {
    renderPage();
    await linhaDoEvento('Aprovar');

    act(() => definirLarguraTela(360));

    expect(cabecalhos()).toEqual(['Evento', 'Ações']);
  }, 20000);

  // axe (item 36): checkbox da linha sem nome ([critical] label) e Tag laranja sem contraste AA.
  test('a caixa de seleção diz qual evento marca e as etiquetas têm contraste AA', async () => {
    renderPage();
    const linha = await linhaDoEvento('Aprovar');

    expect(within(linha).getByRole('checkbox', { name: `Selecionar: ${EVENTO}` })).toBeInTheDocument();
    expect(within(linha).getByText('Pendente')).toHaveStyle({ color: '#ad4e00' });
    expect(screen.getByText('1', { selector: '.ant-tag' })).toHaveStyle({ color: '#ad4e00' });
  }, 20000);

  // Achado da revisão do item 36: o AntD tira o fundo da linha selecionada do colorPrimary
  // (#006B52 → #9aaba4) e os ícones de link do AcoesLinha (sem fundo próprio) caíam para 1,71:1
  // (Aprovar, #1677ff) e 1,36:1 (Reprovar, #ff4d4f); o projeto, small gray-500, para 2,01:1.
  test('linha marcada para o lote: Aprovar e Reprovar com 3:1 e o texto cinza com 4,5:1', async () => {
    render(
      <ConfigProvider theme={{ token: { colorPrimary: '#006B52' } }}>
        <AcessoContext.Provider value={montarAcesso(['access_solicitation_approvals'], null)}>
          <MemoryRouter>
            <ApprovalsPage />
          </MemoryRouter>
        </AcessoContext.Provider>
      </ConfigProvider>,
    );
    const linha = await linhaDoEvento('Aprovar');
    fireEvent.click(within(linha).getByRole('checkbox'));
    expect(linha).toHaveClass('ant-table-row-selected');

    for (const comMouse of [false, true]) {
      const fundo = fundoDaLinhaSelecionada(linha, comMouse);
      expect(contraste('#1677ff', fundo), `Aprovar sobre ${fundo}`).toBeGreaterThanOrEqual(3);
      expect(contraste('#ff4d4f', fundo), `Reprovar sobre ${fundo}`).toBeGreaterThanOrEqual(3);
      expect(contraste('#6b7280', fundo), `gray-500 sobre ${fundo}`).toBeGreaterThanOrEqual(4.5);
    }
  }, 20000);

  test('a barra do lote quebra linha em tela estreita', async () => {
    vi.mocked(listSolicitacoes).mockResolvedValue(linhas(2));
    definirLarguraTela(360);
    renderPage();
    const linha = await linhaDoEvento('Mais ações');

    // fireEvent: o Spin da carga põe pointer-events none na tabela (o userEvent recusa).
    fireEvent.click(within(linha).getByRole('checkbox'));

    const barra = screen.getByRole('navigation', { name: 'Acoes em lote' });
    expect(barra.firstElementChild).toHaveStyle({ flexWrap: 'wrap' });
  }, 20000);
});
