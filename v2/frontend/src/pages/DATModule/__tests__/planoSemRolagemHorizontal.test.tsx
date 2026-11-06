/**
 * G30 (Programa C) — Plano Anual sem rolagem horizontal (decisão do dono).
 *
 * A matriz tinha 27 colunas e `scroll.x` 2200: F1 a F15, A1, A2, P1 a P3, com colunas fixas dos dois
 * lados. Agora é o ResponsiveTable: as células de formações, acompanhamentos e provas viram UMA coluna
 * Progresso, com o resumo ("1/2 formações · 1/2 acompanhamentos · 0/3 provas"), e a edição de cada
 * célula passa para a linha aberta, onde cada formação, acompanhamento e prova continua clicável e
 * abre o mesmo modal de edição de antes. Nada deixou de ser editável. As tabelas do detalhe (modal)
 * também perdem o `scroll.x: max-content`.
 */
import { describe, expect, test, vi } from 'vitest';
import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router';

import { definirLarguraTela } from '../../../test/larguraTela';
import { ComAcesso } from '../../../test/comAcesso';
import { atorRbac } from '../../../test/atoresRbac';

const { PLANO } = vi.hoisted(() => ({
  PLANO: {
    id: 7,
    municipio: 1,
    municipio_nome: 'Fortaleza',
    municipio_uf: 'CE',
    projeto: 1,
    projeto_nome: 'Projeto Teste',
    projeto_geral_nome: 'Coleção Teste',
    ano: 2026,
    coordenador: null,
    coordenador_nome: 'Josefa',
    ch_estudo: 10,
    ch_anual: 20,
    observacoes: null,
    formacoes_list: [
      { id: 1, numero: 1, data: '2026-03-02', ch: 4, modalidade: 'presencial', realizada: true },
      { id: 2, numero: 2, data: null, ch: 4, modalidade: 'online', realizada: false },
    ],
    acompanhamentos_list: [
      { id: 11, tipo: 'primeiro', data: '2026-03-10', realizado: true },
      { id: 12, tipo: 'segundo', data: null, realizado: false },
    ],
    provas_list: [
      { id: 21, numero: 1, data: '2026-04-10', realizada: false },
      { id: 22, numero: 2, data: null, realizada: false },
      { id: 23, numero: 3, data: null, realizada: false },
    ],
  },
}));

vi.mock('../../../api/datModule', () => ({
  listPlanoFormacoes: vi.fn().mockResolvedValue({ results: [PLANO], count: 1, next: null, previous: null }),
  createPlanoFormacoes: vi.fn().mockResolvedValue({}),
  updatePlanoFormacoes: vi.fn().mockResolvedValue({}),
  deletePlanoFormacoes: vi.fn().mockResolvedValue({}),
  getPlanoFormacoesStats: vi.fn().mockResolvedValue({ total_planos: 1 }),
  updateFormacaoInline: vi.fn().mockResolvedValue({}),
  updateAcompanhamentoInline: vi.fn().mockResolvedValue({}),
  updateProvaInline: vi.fn().mockResolvedValue({}),
  getMunicipiosOptions: vi.fn().mockResolvedValue([]),
  getProjetosOptions: vi.fn().mockResolvedValue([]),
}));

import PlanoFormacoesPage from '../PlanoFormacoesPage';

vi.setConfig({ testTimeout: 30_000 });

const PLANO_NOME = 'Fortaleza - CE · Projeto Teste · 2026';
const RESUMO = '1/2 formações · 1/2 acompanhamentos · 0/3 provas';

function renderPage(): ReturnType<typeof render> {
  return render(
    <MemoryRouter>
      <ComAcesso policies={atorRbac('DAT').policies}>
        <PlanoFormacoesPage />
      </ComAcesso>
    </MemoryRouter>,
  );
}

function cabecalhos(): string[] {
  return screen
    .getAllByRole('columnheader')
    .filter((th) => !th.classList.contains('ant-table-row-expand-icon-cell'))
    .map((th) => th.textContent?.trim() ?? '')
    .filter(Boolean);
}

async function linha(acao: 'Editar' | 'Mais ações' = 'Editar'): Promise<HTMLElement> {
  const botao = await screen.findByRole('button', { name: `${acao}: ${PLANO_NOME}` }, { timeout: 15000 });
  const tr = botao.closest('tr');
  if (!tr) throw new Error('o botão não está numa linha da tabela');
  return tr;
}

function abrir(tr: HTMLElement): ReturnType<typeof within> {
  fireEvent.click(within(tr).getByRole('button', { name: `Expandir linha de ${PLANO_NOME}` }));
  return within(document.querySelector<HTMLElement>('.ant-table-expanded-row')!);
}

describe('Plano Anual sem rolagem horizontal (G30)', { timeout: 20000 }, () => {
  test('a 1280 px: uma coluna Progresso no lugar de F1-F15, A1-A2 e P1-P3; sem coluna fixa nem largura forçada', async () => {
    const { container } = renderPage();
    const tr = await linha();

    expect(cabecalhos()).toEqual(['Município', 'Projeto', 'Coleção', 'Coord.', 'Ano', 'Progresso', 'CH', 'Ações']);
    expect(within(tr).getByText(RESUMO)).toBeInTheDocument();
    for (const antiga of ['F1', 'F15', 'A1', 'P3']) {
      expect(screen.queryByRole('columnheader', { name: antiga })).not.toBeInTheDocument();
    }
    expect(container.querySelector('.ant-table-cell-fix-right, .ant-table-cell-fix-left')).toBeNull();
    expect(container.querySelector('.ant-table-content')?.getAttribute('style') ?? '').not.toMatch(/overflow/);
    expect(container.querySelector('table')?.style.width ?? '').toBe('');
    for (const acao of ['Ver detalhes', 'Excluir']) {
      expect(within(tr).getByRole('button', { name: `${acao}: ${PLANO_NOME}` })).toBeInTheDocument();
    }
  });

  test('a linha aberta edita cada formação: abre o modal da formação certa', async () => {
    renderPage();
    const aberta = abrir(await linha());

    // As 15 posições estão na linha aberta; a 2ª formação existe (sem data) e também edita.
    for (let n = 1; n <= 15; n += 1) expect(aberta.getByText(`F${n}`)).toBeInTheDocument();
    fireEvent.click(aberta.getByRole('button', { name: 'Editar formação 2' }));
    expect(await screen.findByText('Editar Formação 2')).toBeInTheDocument();
  });

  test('a linha aberta edita acompanhamentos e provas', async () => {
    renderPage();
    const aberta = abrir(await linha());

    for (const rotulo of ['Editar acompanhamento primeiro', 'Editar acompanhamento segundo']) {
      expect(aberta.getByRole('button', { name: rotulo })).toBeInTheDocument();
    }
    for (const rotulo of ['Editar prova 1', 'Editar prova 2', 'Editar prova 3']) {
      expect(aberta.getByRole('button', { name: rotulo })).toBeInTheDocument();
    }
    fireEvent.click(aberta.getByRole('button', { name: 'Editar prova 3' }));
    expect(await screen.findByText('Editar Prova 3')).toBeInTheDocument();
  });

  test('a 360 px: município com o progresso e o menu de ações; projeto, ano e CH na linha aberta', async () => {
    definirLarguraTela(360);
    renderPage();
    const tr = await linha('Mais ações');

    expect(cabecalhos()).toEqual(['Município', 'Ações']);
    expect(within(tr).getByText(RESUMO)).toBeInTheDocument();
    const aberta = abrir(tr);
    for (const texto of ['Projeto Teste', '2026', '20h', 'Formações', 'Acompanhamentos', 'Provas']) {
      expect(aberta.getByText(texto)).toBeInTheDocument();
    }
    expect(aberta.getByRole('button', { name: 'Editar formação 1' })).toBeInTheDocument();
  });

  test('mudar a largura reorganiza as colunas', async () => {
    renderPage();
    await linha();

    act(() => definirLarguraTela(768));
    expect(cabecalhos()).toEqual(['Município', 'Projeto', 'Ano', 'Progresso', 'CH', 'Ações']);
  });

  test('o detalhe (modal) não força largura: tabelas sem scroll.x', async () => {
    renderPage();
    const tr = await linha();

    fireEvent.click(within(tr).getByRole('button', { name: `Ver detalhes: ${PLANO_NOME}` }));
    const dialogo = await screen.findByRole('dialog');
    expect(within(dialogo).getByText('Presencial')).toBeInTheDocument();
    for (const conteudo of Array.from(dialogo.querySelectorAll('.ant-table-content'))) {
      expect(conteudo.getAttribute('style') ?? '').not.toMatch(/overflow/);
    }
    expect(dialogo.querySelector('table')?.style.width ?? '').toBe('');
  });

  test('o cabeçalho e a barra de botões dos filtros quebram linha', async () => {
    renderPage();
    await linha();

    expect(screen.getByRole('button', { name: /Novo Plano/ }).closest('header')).toHaveClass('flex-wrap');
    expect(screen.getByRole('button', { name: /Limpar/ }).closest('.flex')).toHaveClass('flex-wrap');
  });
});
