/**
 * C2 (Programa C) — Produtos sem rolagem horizontal: lista enxuta no ResponsiveTable.
 *
 * Sempre na linha: o nome, a situação e as ações (AcoesLinha). Código sobe a partir de
 * `sm`, Projeto de `md` e Coleção de `lg`; a Descrição (texto longo) só aparece na grade
 * a partir de `xxl` (1600 px): nas larguras medidas (até 1280 px) ela fica na linha
 * expandida, inteira. O ID interno não vai para a grade. A 360 px as ações ficam no menu
 * "Mais ações".
 */
import { act, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConfigProvider, Modal } from 'antd';
import ptBR from 'antd/locale/pt_BR';
import { MemoryRouter } from 'react-router';
import { beforeEach, describe, expect, test, vi } from 'vitest';

import { definirLarguraTela } from '../../../test/larguraTela';

const { PRODUTOS } = vi.hoisted(() => ({
  PRODUTOS: [
    {
      id: 731,
      codigo: 'KIT-ALF-2026',
      nome: 'Kit Pedagógico de Alfabetização',
      descricao: 'Caixa com cartilhas, fichas de leitura e jogos de consciência fonológica para o 1º ano',
      projeto: 5,
      projeto_nome: 'Alfabetização e Letramento',
      colecao: 9,
      colecao_nome: 'Coleção Primeiros Passos',
      ativo: true,
      created_at: '2026-03-02T12:00:00Z',
      updated_at: '2026-09-29T13:30:00Z',
    },
  ],
}));

vi.mock('../../../api/adminDAT', () => ({
  listProdutos: vi.fn().mockResolvedValue({ results: PRODUTOS, count: 1, next: null, previous: null }),
  createProduto: vi.fn(),
  updateProduto: vi.fn(),
  deleteProduto: vi.fn(),
  listProjetos: vi.fn().mockResolvedValue({
    results: [{ id: 5, nome: 'Alfabetização e Letramento' }], count: 1, next: null, previous: null,
  }),
  listColecoesOptions: vi.fn().mockResolvedValue([{ id: 9, nome: 'Coleção Primeiros Passos', projeto: 5 }]),
}));

import ProdutosPage from '../ProdutosPage';

const NOME = 'Kit Pedagógico de Alfabetização';
const DESCRICAO = 'Caixa com cartilhas, fichas de leitura e jogos de consciência fonológica para o 1º ano';

function renderPage() {
  return render(
    <ConfigProvider locale={ptBR}>
      <MemoryRouter>
        <ProdutosPage />
      </MemoryRouter>
    </ConfigProvider>,
  );
}

async function linhaDoProduto(): Promise<HTMLElement> {
  const nome = await screen.findByText(NOME, { selector: 'td, td *' }, { timeout: 15000 });
  const linha = nome.closest('tr');
  if (!linha) throw new Error('o nome não está numa linha da tabela');
  return linha;
}

/** Títulos das colunas de dados (sem a do botão de expandir, cujo título é só para leitor de tela). */
function cabecalhos(): string[] {
  return screen
    .getAllByRole('columnheader')
    .filter((th) => !th.classList.contains('ant-table-row-expand-icon-cell'))
    .map((th) => th.textContent?.trim() ?? '')
    .filter(Boolean);
}

function linhaExpandida() {
  return within(document.querySelector<HTMLElement>('.ant-table-expanded-row')!);
}

describe('ProdutosPage responsiva (C2)', () => {
  beforeEach(() => vi.clearAllMocks());

  test('a 1280 px: nome, código, projeto, coleção, situação e ações; descrição na linha expandida', async () => {
    const user = userEvent.setup();
    renderPage();
    const linha = await linhaDoProduto();

    expect(cabecalhos()).toEqual(['Nome', 'Código', 'Projeto', 'Coleção', 'Situação', 'Ações']);
    // O nome (identidade) quebra linha em vez de cortar com reticências: não há detalhe que o mostre.
    expect(within(linha).getByText(NOME).closest('td')).not.toHaveClass('ant-table-cell-ellipsis');
    expect(within(linha).queryByText('731')).not.toBeInTheDocument();
    expect(within(linha).queryByText(DESCRICAO)).not.toBeInTheDocument();
    expect(within(linha).getByRole('button', { name: `Editar: ${NOME}` })).toBeInTheDocument();
    expect(within(linha).getByRole('button', { name: `Excluir: ${NOME}` })).toBeInTheDocument();

    await user.click(within(linha).getByRole('button', { name: `Expandir linha de ${NOME}` }));
    expect(linhaExpandida().getByText(DESCRICAO)).toBeInTheDocument();
  }, 20000);

  test('a 360 px: só nome, situação e o menu de ações; o resto na linha expandida', async () => {
    definirLarguraTela(360);
    const user = userEvent.setup();
    renderPage();
    const linha = await linhaDoProduto();

    expect(cabecalhos()).toEqual(['Nome', 'Situação', 'Ações']);
    // Sem a coluna Código, o código (a chave única: o nome pode repetir) fica junto do nome.
    expect(within(linha).getByText(NOME).closest('td')).toHaveTextContent('KIT-ALF-2026');
    expect(within(linha).queryByRole('button', { name: `Editar: ${NOME}` })).not.toBeInTheDocument();
    expect(within(linha).getByRole('button', { name: `Mais ações: ${NOME}` })).toBeInTheDocument();

    await user.click(within(linha).getByRole('button', { name: `Expandir linha de ${NOME}` }));
    for (const texto of ['KIT-ALF-2026', 'Alfabetização e Letramento', 'Coleção Primeiros Passos', DESCRICAO]) {
      expect(linhaExpandida().getByText(texto)).toBeInTheDocument();
    }
  }, 20000);

  test('mudar a largura com a página aberta reorganiza as colunas', async () => {
    renderPage();
    await linhaDoProduto();
    expect(cabecalhos()).toContain('Coleção');

    act(() => definirLarguraTela(360));

    expect(cabecalhos()).toEqual(['Nome', 'Situação', 'Ações']);
  }, 20000);

  test('a etiqueta de situação tem contraste AA (texto green-8)', async () => {
    renderPage();
    const linha = await linhaDoProduto();

    expect(within(linha).getByText('Ativo')).toHaveStyle({ color: '#237804' });
  }, 20000);

  test('Editar abre o modal de sempre com o produto', async () => {
    const user = userEvent.setup();
    renderPage();
    const linha = await linhaDoProduto();

    await user.click(within(linha).getByRole('button', { name: `Editar: ${NOME}` }));
    // (no jsdom o AntD dá o mesmo id "test-id" a todo diálogo: o nome acessível não distingue)
    const modal = (await screen.findByText('Editar Produto', {}, { timeout: 10000 })).closest<HTMLElement>(
      '[role="dialog"]',
    );
    expect(modal).not.toBeNull();
    expect(within(modal!).getByLabelText('Nome do Produto')).toHaveValue(NOME);
  }, 30000);

  test('Excluir: a confirmação cita o produto e começa no Cancelar', async () => {
    const confirmar = vi.spyOn(Modal, 'confirm').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() }));
    const user = userEvent.setup();
    renderPage();
    const linha = await linhaDoProduto();

    // Modal.confirm não monta de forma confiável sob React 19 no jsdom: confere o que ele recebe.
    await user.click(within(linha).getByRole('button', { name: `Excluir: ${NOME}` }));
    expect(confirmar).toHaveBeenCalledTimes(1);
    expect(confirmar.mock.calls[0]![0]).toMatchObject({ autoFocusButton: 'cancel', title: 'Confirmar exclusão' });
    // o nome pode repetir; o código não
    expect(String(confirmar.mock.calls[0]![0].content)).toContain(`${NOME}" (código KIT-ALF-2026)`);
    confirmar.mockRestore();
  }, 30000);
});
