/**
 * Produtos (B#50): textos da tela acentuados ("Código", "Descrição", "obrigatório", "excluído", "Navegação").
 */
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConfigProvider, Modal, message } from 'antd';
import ptBR from 'antd/locale/pt_BR';
import { MemoryRouter } from 'react-router';
import { beforeEach, describe, expect, test, vi } from 'vitest';

const { PRODUTO } = vi.hoisted(() => ({
  PRODUTO: {
    id: 731, codigo: 'KIT-ALF-2026', nome: 'Kit Pedagógico de Alfabetização', descricao: '',
    projeto: 5, projeto_nome: 'Alfabetização e Letramento',
    ativo: true, created_at: '', updated_at: '',
  },
}));

vi.mock('../../../api/adminDAT', () => ({
  listProdutos: vi.fn(),
  createProduto: vi.fn(),
  updateProduto: vi.fn(),
  deleteProduto: vi.fn(),
  listProjetos: vi.fn(),
}));

import { deleteProduto, listProdutos, listProjetos } from '../../../api/adminDAT';
import ProdutosPage from '../ProdutosPage';

function renderPage() {
  return render(
    <ConfigProvider locale={ptBR}>
      <MemoryRouter>
        <ProdutosPage />
      </MemoryRouter>
    </ConfigProvider>,
  );
}

describe('ProdutosPage: textos acentuados', { timeout: 20000 }, () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(listProdutos).mockResolvedValue({ results: [PRODUTO], count: 1, next: null, previous: null });
    vi.mocked(listProjetos).mockResolvedValue({
      results: [{ id: 5, nome: 'Alfabetização e Letramento' }],
      count: 1, next: null, previous: null,
    } as never);
  });

  test('navegação e busca acentuadas', async () => {
    renderPage();
    await screen.findByText(PRODUTO.nome, { selector: 'td, td *' });

    expect(screen.getByRole('navigation', { name: 'Navegação' })).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Buscar por nome ou código...')).toBeInTheDocument();
  });

  test('formulário: rótulos, exemplos e obrigatórios acentuados', async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: /Novo Produto/ }));
    const modal = (await screen.findByText('Novo Produto', { selector: '.ant-modal-title' })).closest<HTMLElement>(
      '[role="dialog"]',
    )!;

    expect(within(modal).getByLabelText('Código')).toBeInTheDocument();
    expect(within(modal).getByLabelText('Descrição')).toHaveAttribute('placeholder', 'Descrição do produto');
    expect(within(modal).getByPlaceholderText('Ex: Material Didático')).toBeInTheDocument();

    await user.click(within(modal).getByRole('button', { name: 'Salvar' }));
    expect(await within(modal).findByText('Código é obrigatório')).toBeInTheDocument();
    expect(within(modal).getByText('Nome é obrigatório')).toBeInTheDocument();
    expect(within(modal).getByText('Projeto é obrigatório')).toBeInTheDocument();
  });

  test('excluir: "Produto excluído com sucesso"', async () => {
    const confirmar = vi.spyOn(Modal, 'confirm').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() }));
    const sucesso = vi.spyOn(message, 'success').mockImplementation(() => (() => undefined) as never);
    vi.mocked(deleteProduto).mockResolvedValue(undefined);
    const user = userEvent.setup();
    renderPage();
    const nome = await screen.findByText(PRODUTO.nome, { selector: 'td, td *' });
    await user.click(within(nome.closest<HTMLElement>('tr')!).getByRole('button', { name: `Excluir: ${PRODUTO.nome}` }));
    await confirmar.mock.calls[0]![0].onOk!();

    await waitFor(() => expect(sucesso).toHaveBeenCalledWith('Produto excluído com sucesso'));
    confirmar.mockRestore();
    sucesso.mockRestore();
  });
});
