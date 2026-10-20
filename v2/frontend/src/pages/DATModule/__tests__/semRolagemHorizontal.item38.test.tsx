/**
 * Gestão de Ações e Registros de Turmas sem rolagem horizontal (item 38, ensaio de 20/10/2026).
 *
 * A 390 px as duas rolavam para o lado (scrollWidth 1133 e 1431): `scroll.x` de 1400 e 1800 px,
 * colunas fixas à esquerda e à direita e um cabeçalho de grupos com larguras fixas (620 + 400 px
 * em Ações, 720 + 580 px em Registros). Agora são o ResponsiveTable: a identidade da linha e as
 * ações (AcoesLinha, menu no celular) ficam sempre na linha; o resto sobe por largura e o que
 * some vai para a linha expandida.
 */
import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, test, vi } from 'vitest';
import { MemoryRouter } from 'react-router';

import { definirLarguraTela } from '../../../test/larguraTela';

const { acaoRow, registroRow } = vi.hoisted(() => ({
  acaoRow: {
    id: 7,
    municipio: 1,
    municipio_nome: 'Fortaleza',
    municipio_uf: 'CE',
    projeto: 2,
    projeto_nome: 'Sub X',
    projeto_geral_nome: 'Coleção X',
    coordenador: 3,
    coordenador_nome: 'Josefa Coordenadora',
    status_carta: 'concluido',
    status_contato: 'pendente',
    status_reuniao: 'pendente',
    status_entrega: 'pendente',
  },
  registroRow: {
    id: 9,
    municipio_nome: 'Sobral',
    municipio_uf: 'CE',
    projeto_geral_nome: 'Coleção Y',
    projeto_nome: 'Projeto Y',
    ano: 2026,
    turma_formar_status: 'criada',
    obs_formar: 'Observação do FORMAR',
  },
}));

vi.mock('../../../api/datModule', () => ({
  listAcoes: vi.fn().mockResolvedValue({ results: [acaoRow], count: 1, next: null, previous: null }),
  getAcao: vi.fn().mockResolvedValue(acaoRow),
  createAcao: vi.fn(),
  updateAcao: vi.fn(),
  deleteAcao: vi.fn(),
  getAcoesStats: vi.fn().mockResolvedValue({}),
  listDATRegistros: vi.fn().mockResolvedValue({ results: [registroRow], count: 1, next: null, previous: null }),
  createDATRegistro: vi.fn(),
  updateDATRegistro: vi.fn(),
  deleteDATRegistro: vi.fn(),
  exportDATRegistros: vi.fn(),
  getMunicipiosOptions: vi.fn().mockResolvedValue([]),
  getProjetosOptions: vi.fn().mockResolvedValue([]),
  getProjetosGeraisOptions: vi.fn().mockResolvedValue([]),
  getCoordenadoresOptions: vi.fn().mockResolvedValue([]),
}));

import AcoesPage from '../AcoesPage';
import DATRegistrosPage from '../DATRegistrosPage';

// Telas pesadas (AntD + filtros + tabela): na CI, cerca de 4x mais lenta que local e com
// cobertura, passam dos 5 s padrão. Só o limite de tempo muda, nenhuma asserção.
vi.setConfig({ testTimeout: 20_000 });

const ACAO = 'Fortaleza - CE · Sub X';
const REGISTRO = 'Sobral - CE · Projeto Y · 2026';

function renderPagina(pagina: 'acoes' | 'registros'): ReturnType<typeof render> {
  return render(<MemoryRouter>{pagina === 'acoes' ? <AcoesPage /> : <DATRegistrosPage />}</MemoryRouter>);
}

/** Títulos das colunas de dados (sem a do botão de expandir). */
function cabecalhos(): string[] {
  return screen
    .getAllByRole('columnheader')
    .filter((th) => !th.classList.contains('ant-table-row-expand-icon-cell'))
    .map((th) => th.textContent?.trim() ?? '')
    .filter(Boolean);
}

async function linhaPelaAcao(nome: string): Promise<HTMLElement> {
  const botao = await screen.findByRole('button', { name: nome }, { timeout: 15000 });
  const linha = botao.closest('tr');
  if (!linha) throw new Error('o botão não está numa linha da tabela');
  return linha;
}

/** Nada que obrigue a tela a ser mais larga que o celular: scroll.x, coluna fixa, flex de largura fixa. */
function semLarguraForcada(container: HTMLElement): void {
  expect(container.querySelector('.ant-table-cell-fix-right, .ant-table-cell-fix-left')).toBeNull();
  expect(container.querySelector('.ant-table-content')?.getAttribute('style') ?? '').not.toMatch(/overflow/);
  expect(container.querySelector('table')?.style.width ?? '').toBe('');
  const fixos = Array.from(container.querySelectorAll<HTMLElement>('[style]')).filter((el) => /\d{3,}px/.test(el.style.flex));
  expect(fixos.map((el) => el.style.flex)).toEqual([]);
}

describe('Gestão de Ações sem rolagem horizontal', () => {
  test('a 1280 px: o fluxo e o coordenador na linha, sem coluna fixa nem largura forçada', async () => {
    const { container } = renderPagina('acoes');
    const linha = await linhaPelaAcao(`Editar: ${ACAO}`);

    expect(cabecalhos()).toEqual([
      'Município - UF',
      'Projeto',
      'Coleção',
      'Coordenador',
      'Carta',
      'Contato',
      'Reunião',
      'Entrega',
      'Ações',
    ]);
    expect(within(linha).getByRole('button', { name: `Excluir: ${ACAO}` })).toBeInTheDocument();
    semLarguraForcada(container);
  });

  test('a 1280 px: a Coleção fica na linha e ordena (o "reagrupar por família", #1897)', async () => {
    renderPagina('acoes');
    await linhaPelaAcao(`Editar: ${ACAO}`);

    const colecao = screen.getByRole('columnheader', { name: /Coleção/ });
    fireEvent.click(colecao);
    expect(colecao).toHaveAttribute('aria-sort', 'ascending');
  });

  test('a 360 px: só a ação (município e projeto) e o menu; o resto na linha expandida', async () => {
    definirLarguraTela(360);
    const { container } = renderPagina('acoes');
    const linha = await linhaPelaAcao(`Mais ações: ${ACAO}`);

    expect(cabecalhos()).toEqual(['Município - UF', 'Ações']);
    expect(within(linha).getByText('Sub X')).toBeInTheDocument();
    semLarguraForcada(container);

    fireEvent.click(within(linha).getByRole('button', { name: `Expandir linha de ${ACAO}` }));
    const expandida = within(document.querySelector<HTMLElement>('.ant-table-expanded-row')!);
    for (const texto of ['Josefa Coordenadora', 'Coleção X', 'Carta', 'Entrega', 'Progresso']) {
      expect(expandida.getByText(texto)).toBeInTheDocument();
    }
  });

  test('mudar a largura com a página aberta reorganiza as colunas', async () => {
    renderPagina('acoes');
    await linhaPelaAcao(`Editar: ${ACAO}`);

    act(() => definirLarguraTela(360));

    expect(cabecalhos()).toEqual(['Município - UF', 'Ações']);
  });
});

describe('Registros de Turmas sem rolagem horizontal', () => {
  test('a 1280 px: sem coluna fixa nem largura forçada; o detalhe do FORMAR e do AVALIAR na linha expandida', async () => {
    const { container } = renderPagina('registros');
    const linha = await linhaPelaAcao(`Editar: ${REGISTRO}`);

    expect(cabecalhos()).toEqual([
      'Município - UF',
      'Projeto',
      'Ano',
      'Alunos',
      'Profs.',
      'Status Turma',
      'Chaves',
      'Usa AVALIAR',
      'Ações',
    ]);
    semLarguraForcada(container);

    fireEvent.click(within(linha).getByRole('button', { name: `Expandir linha de ${REGISTRO}` }));
    const expandida = within(document.querySelector<HTMLElement>('.ant-table-expanded-row')!);
    for (const texto of ['Coleção Y', 'Observação do FORMAR', 'Obs. AVALIAR', 'Importados']) {
      expect(expandida.getByText(texto)).toBeInTheDocument();
    }
  });

  test('a 360 px: só município, ano e o menu de ações', async () => {
    definirLarguraTela(360);
    const { container } = renderPagina('registros');
    const linha = await linhaPelaAcao(`Mais ações: ${REGISTRO}`);

    expect(cabecalhos()).toEqual(['Município - UF', 'Ano', 'Ações']);
    expect(within(linha).getByText('Projeto Y')).toBeInTheDocument();
    semLarguraForcada(container);
  });
});
