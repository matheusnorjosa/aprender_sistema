/**
 * Controle > Compras no ensaio de 20/10/2026 (rodada 2, item 38).
 *
 * - "Exportar" não fazia nada (botão sem ação, e não há export de compras no servidor): saiu.
 * - Excluir aparecia para o Controle, que recebe 403 (o destroy exige
 *   `execute_restricted_operations`), e a confirmação dizia 'Deseja excluir "null"?' quando a
 *   compra não tem produto.
 * - A 390 px a tabela rolava para o lado (scroll.x de 1400 px, 13 colunas, três fixas).
 * - Os 8 filtros não tinham nome acessível: o rótulo visível não estava ligado ao campo.
 */
import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { MemoryRouter } from 'react-router';
import { Modal } from 'antd';

import { ComAcesso } from '../../../test/comAcesso';
import { definirLarguraTela } from '../../../test/larguraTela';

const { comProduto, semProduto } = vi.hoisted(() => ({
  comProduto: {
    id: 1, projeto: 10, projeto_nome: 'NOVO LENDO 1', projeto_geral_nome: 'NOVO LENDO',
    produto: 100, produto_nome: 'Livro do Aluno', codigo_produto: 'LA1',
    municipio: 20, municipio_nome: 'Fortaleza', municipio_uf: 'CE',
    quantidade: 100, quantidade_utilizada: 40, data_compra: '2026-03-01', ano_uso: 2026,
    tipo_compra: 'primeira', status_uso: null,
  },
  semProduto: {
    id: 2, projeto: 11, projeto_nome: 'Projeto Teste Super', projeto_geral_nome: null,
    produto: null, produto_nome: null, codigo_produto: null,
    municipio: 21, municipio_nome: 'Crato', municipio_uf: 'CE',
    quantidade: 100, quantidade_utilizada: 0, data_compra: null, ano_uso: 2027,
    tipo_compra: null, status_uso: null,
  },
}));

vi.mock('../../../api/datModule', () => ({
  listCompras: vi.fn().mockResolvedValue({ results: [comProduto, semProduto], count: 2, next: null, previous: null }),
  createCompra: vi.fn(),
  updateCompra: vi.fn().mockResolvedValue({}),
  deleteCompra: vi.fn().mockResolvedValue(undefined),
  getMunicipiosOptions: vi.fn().mockResolvedValue([]),
  getProjetosOptions: vi.fn().mockResolvedValue([]),
  getProdutosOptions: vi.fn().mockResolvedValue([]),
}));

import ComprasPage from '../ComprasPage';

// Tela pesada (AntD + filtros + tabela + modal): na CI passa dos 5 s padrão.
vi.setConfig({ testTimeout: 30_000 });

const CONTROLE = ['view_compras_stats', 'access_controle_section', 'run_daily_operations'];
const DAT = [...CONTROLE, 'execute_restricted_operations'];

const COMPRA = 'Livro do Aluno · Fortaleza - CE';
const COMPRA_SEM_PRODUTO = 'Projeto Teste Super · Crato - CE';

function renderPagina(policies: readonly string[] = DAT): ReturnType<typeof render> {
  return render(
    <MemoryRouter>
      <ComAcesso policies={policies}>
        <ComprasPage />
      </ComAcesso>
    </MemoryRouter>,
  );
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

/** Nada que obrigue a tela a ser mais larga que o celular: scroll.x ou coluna fixa. */
function semLarguraForcada(container: HTMLElement): void {
  expect(container.querySelector('.ant-table-cell-fix-right, .ant-table-cell-fix-left')).toBeNull();
  expect(container.querySelector('.ant-table-content')?.getAttribute('style') ?? '').not.toMatch(/overflow/);
  expect(container.querySelector('table')?.style.width ?? '').toBe('');
}

beforeEach(() => vi.clearAllMocks());

describe('Compras: Exportar', () => {
  test('não há botão Exportar (não existe export de compras)', async () => {
    renderPagina();
    await linhaPelaAcao(`Editar: ${COMPRA}`);
    expect(screen.queryByRole('button', { name: /Exportar/ })).not.toBeInTheDocument();
  });
});

describe('Compras: Excluir só para quem pode', () => {
  test('o Controle (sem execute_restricted_operations) não vê Excluir, nem na linha nem no modal', async () => {
    renderPagina(CONTROLE);
    const linha = await linhaPelaAcao(`Editar: ${COMPRA}`);
    expect(within(linha).queryByRole('button', { name: /Excluir/ })).not.toBeInTheDocument();

    fireEvent.click(within(linha).getByRole('button', { name: `Editar: ${COMPRA}` }));
    await screen.findByText('Editar Compra');
    expect(screen.queryByRole('button', { name: /Excluir/ })).not.toBeInTheDocument();
  });

  test('com execute_restricted_operations vê Excluir na linha', async () => {
    renderPagina(DAT);
    const linha = await linhaPelaAcao(`Editar: ${COMPRA}`);
    expect(within(linha).getByRole('button', { name: `Excluir: ${COMPRA}` })).toBeInTheDocument();
  });

  test('a confirmação nomeia a compra sem produto pelo projeto e município, nunca "null"', async () => {
    // Modal.confirm não monta de forma confiável sob React 19 no jsdom: confere o que ele recebe.
    const confirmar = vi.spyOn(Modal, 'confirm').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() }));
    renderPagina(DAT);
    const linha = await linhaPelaAcao(`Excluir: ${COMPRA_SEM_PRODUTO}`);
    fireEvent.click(within(linha).getByRole('button', { name: `Excluir: ${COMPRA_SEM_PRODUTO}` }));

    expect(confirmar).toHaveBeenCalledTimes(1);
    const conteudo = String(confirmar.mock.calls[0]![0].content);
    expect(conteudo).toBe(`Deseja excluir a compra "${COMPRA_SEM_PRODUTO}"? Esta ação não pode ser desfeita.`);
    expect(conteudo).not.toMatch(/null/);
    confirmar.mockRestore();
  });
});

describe('Compras sem rolagem horizontal', () => {
  test('a 1280 px: sem coluna fixa nem largura forçada; Coleção na linha e ordena', async () => {
    const { container } = renderPagina();
    await linhaPelaAcao(`Editar: ${COMPRA}`);

    expect(cabecalhos()).toEqual([
      'Produto',
      'Projeto',
      'Coleção',
      'Município',
      'Quantidade',
      'Disponível',
      'Ano Uso',
      'Status',
      'Ações',
    ]);
    semLarguraForcada(container);

    const colecao = screen.getByRole('columnheader', { name: /Coleção/ });
    fireEvent.click(colecao);
    expect(colecao).toHaveAttribute('aria-sort', 'ascending');
  });

  test('a 1280 px: o resto (UF, data, utilizado, tipo) na linha expandida', async () => {
    renderPagina();
    const linha = await linhaPelaAcao(`Editar: ${COMPRA}`);

    fireEvent.click(within(linha).getByRole('button', { name: `Expandir linha de ${COMPRA}` }));
    const expandida = within(document.querySelector<HTMLElement>('.ant-table-expanded-row')!);
    for (const texto of ['UF', 'Data Compra', '01/03/2026', 'Utilizado', 'Tipo Compra', 'Primeira compra']) {
      expect(expandida.getByText(texto)).toBeInTheDocument();
    }
  });

  test('a 390 px: só o produto (com projeto e município) e o menu de ações', async () => {
    definirLarguraTela(390);
    const { container } = renderPagina();
    const linha = await linhaPelaAcao(`Mais ações: ${COMPRA}`);

    expect(cabecalhos()).toEqual(['Produto', 'Ações']);
    expect(within(linha).getByText('NOVO LENDO 1 · Fortaleza - CE')).toBeInTheDocument();
    semLarguraForcada(container);
  });

  test('mudar a largura com a página aberta reorganiza as colunas', async () => {
    renderPagina();
    await linhaPelaAcao(`Editar: ${COMPRA}`);

    act(() => definirLarguraTela(390));

    expect(cabecalhos()).toEqual(['Produto', 'Ações']);
  });

  test('os totais da página continuam na tela, em qualquer largura', async () => {
    definirLarguraTela(390);
    renderPagina();
    await linhaPelaAcao(`Mais ações: ${COMPRA}`);

    const rodape = document.querySelector<HTMLElement>('.ant-table-footer');
    expect(rodape?.textContent).toBe('Total da página: quantidade 200 · utilizado 40 · disponível 160');
    // O disponível mantém a cor de antes (verde se sobra, vermelho se não).
    expect(within(rodape!).getByText('160')).toHaveClass('ant-typography-success');
  });

  test('entre 576 e 991 px: projeto e município embaixo do produto (as colunas ainda não estão todas)', async () => {
    definirLarguraTela(700);
    renderPagina();
    const linha = await linhaPelaAcao(`Editar: ${COMPRA}`);

    expect(cabecalhos()).not.toContain('Projeto');
    expect(cabecalhos()).not.toContain('Município');
    expect(within(linha).getByText('NOVO LENDO 1 · Fortaleza - CE')).toBeInTheDocument();
  });

  test('a 1280 px: projeto e município só nas colunas, não repetidos embaixo do produto', async () => {
    renderPagina();
    const linha = await linhaPelaAcao(`Editar: ${COMPRA}`);

    expect(within(linha).queryByText('NOVO LENDO 1 · Fortaleza - CE')).not.toBeInTheDocument();
  });
});

describe('Compras: filtros com nome acessível', () => {
  test('cada filtro tem o nome do rótulo visível', async () => {
    renderPagina();
    await linhaPelaAcao(`Editar: ${COMPRA}`);

    expect(screen.getByRole('searchbox', { name: 'Buscar' })).toBeInTheDocument();
    for (const nome of ['Projeto', 'Produto', 'UF', 'Município', 'Ano Uso', 'Status', 'Tipo Compra']) {
      expect(screen.getByRole('combobox', { name: nome })).toBeInTheDocument();
    }
  });
});
