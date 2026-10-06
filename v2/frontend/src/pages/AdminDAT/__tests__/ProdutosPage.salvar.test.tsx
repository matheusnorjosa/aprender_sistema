/**
 * C2 (Programa C) — Produtos: salvar e estados que não mentem.
 *
 * - O produto não tem Coleção própria: coleção é a família do projeto (decisão do dono, 06/10/2026),
 *   então o cadastro não tem o campo nem o envia.
 * - O erro de validação do backend (código repetido) aparece com o motivo, no campo.
 * - Salvar com loading; filtro por projeto no topo; falhas de carga com motivo e "Tentar de novo".
 */
import { act, render, screen, waitFor, within } from '@testing-library/react';
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

import { deleteProduto, listProdutos, listProjetos, updateProduto } from '../../../api/adminDAT';
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

async function abrirEditar(user: ReturnType<typeof userEvent.setup>): Promise<HTMLElement> {
  const nome = await screen.findByText(PRODUTO.nome, { selector: 'td, td *' }, { timeout: 15000 });
  await user.click(within(nome.closest<HTMLElement>('tr')!).getByRole('button', { name: `Editar: ${PRODUTO.nome}` }));
  return (await screen.findByText('Editar Produto', {}, { timeout: 10000 })).closest<HTMLElement>('[role="dialog"]')!;
}

describe('ProdutosPage: salvar e filtrar (C2)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(listProdutos).mockResolvedValue({ results: [PRODUTO], count: 1, next: null, previous: null });
    vi.mocked(listProjetos).mockResolvedValue({
      results: [{ id: 5, nome: 'Alfabetização e Letramento' }, { id: 6, nome: 'Matemática em Foco' }],
      count: 2, next: null, previous: null,
    } as never);
    vi.mocked(updateProduto).mockResolvedValue(PRODUTO);
  });

  test('o cadastro do produto não tem Coleção: nem o campo, nem no que o Salvar envia', async () => {
    const user = userEvent.setup();
    renderPage();

    const modal = await abrirEditar(user);
    expect(within(modal).queryByRole('combobox', { name: 'Coleção' })).not.toBeInTheDocument();
    await user.click(within(modal).getByRole('combobox', { name: 'Projeto' }));
    await user.click(await screen.findByTitle('Matemática em Foco'));
    await user.click(within(modal).getByRole('button', { name: 'Salvar' }));

    await waitFor(() => expect(updateProduto).toHaveBeenCalledTimes(1));
    const payload = vi.mocked(updateProduto).mock.calls[0]![1];
    expect(payload).toMatchObject({ projeto: 6 });
    expect(payload).not.toHaveProperty('colecao');
  }, 40000);

  test('erro de validação ao salvar: o motivo do backend no toast e no campo Código', async () => {
    const erro = vi.spyOn(message, 'error').mockImplementation(() => (() => undefined) as never);
    vi.mocked(updateProduto).mockRejectedValue(
      Object.assign(new Error('Erro de validação.'), {
        response: { status: 400, data: { detail: 'Erro de validação.', errors: { codigo: ['produto com este codigo já existe.'] } } },
      }),
    );
    const user = userEvent.setup();
    renderPage();

    const modal = await abrirEditar(user);
    await user.click(within(modal).getByRole('button', { name: 'Salvar' }));

    await waitFor(() => expect(erro).toHaveBeenCalledWith('Erro: produto com este codigo já existe.'));
    expect(await within(modal).findByText('produto com este codigo já existe.')).toBeInTheDocument();
    erro.mockRestore();
  }, 40000);

  test('Salvar fica em loading enquanto a API trabalha', async () => {
    vi.mocked(updateProduto).mockReturnValue(new Promise(() => undefined));
    const user = userEvent.setup();
    renderPage();

    const modal = await abrirEditar(user);
    await user.click(within(modal).getByRole('button', { name: 'Salvar' }));

    await waitFor(() => expect(within(modal).getByRole('button', { name: /Salvar/ })).toHaveClass('ant-btn-loading'));
  }, 40000);

  test('filtro por projeto no topo, enviado ao backend', async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByText(PRODUTO.nome, { selector: 'td, td *' }, { timeout: 15000 });

    await user.click(screen.getByRole('combobox', { name: 'Filtrar por projeto' }));
    await user.click(await screen.findByTitle('Matemática em Foco'));

    await waitFor(() => expect(listProdutos).toHaveBeenLastCalledWith(expect.objectContaining({ projeto: 6, page: 1 })));
  }, 40000);

  test('falha ao carregar a lista: o motivo e "Tentar de novo", não "Não há dados"', async () => {
    vi.mocked(listProdutos).mockRejectedValue(new Error('Você não tem permissão para realizar esta ação.'));
    renderPage();

    const alerta = await screen.findByText('Não foi possível carregar a lista.', {}, { timeout: 15000 });
    expect(alerta.closest('[role="alert"]')).toHaveTextContent('Você não tem permissão para realizar esta ação.');
    expect(screen.queryByText('Não há dados')).not.toBeInTheDocument();
    // Sem número no título: "(0)" diria que não há produto.
    expect(screen.getByRole('heading', { level: 3 })).toHaveTextContent(/^Produtos$/);
  }, 30000);

  test('projetos não carregaram: no topo, o motivo e "Tentar de novo" pelo Tab; o filtro fica desabilitado', async () => {
    vi.mocked(listProjetos).mockRejectedValueOnce(new Error('Falha de rede'));
    const user = userEvent.setup();
    renderPage();
    await screen.findByText(PRODUTO.nome, { selector: 'td, td *' }, { timeout: 15000 });

    // Antes, o filtro dizia "Não há dados" e a página não mostrava a falha.
    const alerta = await screen.findByRole('alert');
    expect(alerta).toHaveTextContent('Não foi possível carregar os projetos.');
    expect(alerta).toHaveTextContent('Falha de rede');
    expect(screen.getByRole('combobox', { name: 'Filtrar por projeto' })).toBeDisabled();

    screen.getByRole('button', { name: /Novo Produto/ }).focus();
    await user.tab();
    expect(within(alerta).getByRole('button', { name: 'Tentar de novo: carregar os projetos' })).toHaveFocus();

    await user.keyboard('{Enter}');
    await waitFor(() => expect(listProjetos).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument());
    expect(screen.getByRole('combobox', { name: 'Filtrar por projeto' })).toBeEnabled();
  }, 40000);

  test('projetos não carregaram: no modal, o aviso fica abaixo do campo e o "Tentar de novo" entra no Tab', async () => {
    vi.mocked(listProjetos).mockRejectedValueOnce(new Error('Falha de rede'));
    const user = userEvent.setup();
    renderPage();

    const modal = await abrirEditar(user);
    const alerta = await within(modal).findByRole('alert');
    expect(alerta).toHaveTextContent('Não foi possível carregar os projetos.');
    expect(within(modal).getByRole('combobox', { name: 'Projeto' })).toBeDisabled();

    within(modal).getByLabelText('Descricao').focus();
    await user.tab();
    expect(within(alerta).getByRole('button', { name: 'Tentar de novo: carregar os projetos' })).toHaveFocus();
  }, 40000);

  test('"Tentar de novo" dos projetos no topo: falhou de novo, o foco fica no botão; carregou, vai para o filtro', async () => {
    vi.mocked(listProjetos)
      .mockRejectedValueOnce(new Error('Falha de rede'))
      .mockRejectedValueOnce(new Error('Falha de novo'));
    const user = userEvent.setup();
    renderPage();
    await screen.findByText(PRODUTO.nome, { selector: 'td, td *' }, { timeout: 15000 });
    const botao = (): HTMLElement => within(screen.getByRole('alert')).getByRole('button', { name: /^Tentar de novo/ });
    await screen.findByRole('alert');

    botao().focus();
    await user.keyboard('{Enter}');
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Falha de novo'));
    await waitFor(() => expect(botao()).not.toHaveClass('ant-btn-loading'));
    expect(botao()).toHaveFocus();

    await user.keyboard('{Enter}');
    await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument());
    expect(screen.getByRole('combobox', { name: 'Filtrar por projeto' })).toHaveFocus();
  }, 40000);

  test('"Tentar de novo" dos projetos no topo: se a pessoa já foi para a busca, a resposta não leva o foco', async () => {
    let responder: (pagina: Awaited<ReturnType<typeof listProjetos>>) => void = () => undefined;
    vi.mocked(listProjetos)
      .mockRejectedValueOnce(new Error('Falha de rede'))
      .mockImplementationOnce(() => new Promise((resolver) => { responder = resolver; }));
    const user = userEvent.setup();
    renderPage();
    await screen.findByText(PRODUTO.nome, { selector: 'td, td *' }, { timeout: 15000 });
    const alerta = await screen.findByRole('alert');

    within(alerta).getByRole('button', { name: /^Tentar de novo/ }).focus();
    await user.keyboard('{Enter}');
    await waitFor(() => expect(listProjetos).toHaveBeenCalledTimes(2));
    const busca = screen.getByRole('searchbox', { name: 'Buscar produtos por nome ou código' });
    await user.click(busca);
    await user.keyboard('ki');

    await act(async () => {
      responder({ results: [{ id: 5, nome: 'Alfabetização e Letramento' }], count: 1, next: null, previous: null } as never);
    });
    await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument());
    expect(busca).toHaveFocus();
    await user.keyboard('t');
    expect(busca).toHaveValue('kit');
  }, 40000);

  test('"Tentar de novo" no modal: os projetos que carregam levam o foco ao próprio campo', async () => {
    vi.mocked(listProjetos).mockRejectedValueOnce(new Error('Falha de rede'));
    const user = userEvent.setup();
    renderPage();
    const modal = await abrirEditar(user);
    const alerta = await within(modal).findByRole('alert');
    // O nome começa pelo texto visível (WCAG 2.5.3) e diz o que recarrega.
    const botao = within(alerta).getByRole('button', { name: 'Tentar de novo: carregar os projetos' });
    expect(botao).toHaveTextContent(/^Tentar de novo$/);

    botao.focus();
    await user.keyboard('{Enter}');
    await waitFor(() => expect(within(modal).queryByRole('alert')).not.toBeInTheDocument());
    expect(within(modal).getByRole('combobox', { name: 'Projeto' })).toHaveFocus();
  }, 40000);

  test('filtro de projeto e busca sem produto: cita os dois e oferece limpar os dois', async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByText(PRODUTO.nome, { selector: 'td, td *' }, { timeout: 15000 });
    vi.mocked(listProdutos).mockResolvedValue({ results: [], count: 0, next: null, previous: null });

    const busca = screen.getByRole('searchbox', { name: 'Buscar produtos por nome ou código' });
    await user.type(busca, 'kit azul{Enter}');
    await user.click(screen.getByRole('combobox', { name: 'Filtrar por projeto' }));
    await user.click(await screen.findByTitle('Matemática em Foco'));

    // O projeto pode ter produtos que só não batem com a busca: o texto não culpa só o projeto.
    expect(await screen.findByText('Nenhum produto para "kit azul" no projeto Matemática em Foco.')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Limpar busca e filtro de projeto' }));
    await waitFor(() =>
      expect(listProdutos).toHaveBeenLastCalledWith(expect.objectContaining({ search: '', projeto: undefined })),
    );
    expect(busca).toHaveValue('');
    // O botão some com o clique: o foco vai para a busca, não para o body.
    expect(busca).toHaveFocus();
  }, 40000);

  test('filtro por projeto sem produto: diz o projeto e oferece limpar o filtro', async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByText(PRODUTO.nome, { selector: 'td, td *' }, { timeout: 15000 });
    vi.mocked(listProdutos).mockResolvedValue({ results: [], count: 0, next: null, previous: null });

    await user.click(screen.getByRole('combobox', { name: 'Filtrar por projeto' }));
    await user.click(await screen.findByTitle('Matemática em Foco'));

    expect(await screen.findByText('Nenhum produto para o projeto Matemática em Foco.')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Limpar filtro de projeto' }));
    await waitFor(() => expect(listProdutos).toHaveBeenLastCalledWith(expect.objectContaining({ projeto: undefined })));
    expect(screen.getByRole('searchbox', { name: 'Buscar produtos por nome ou código' })).toHaveFocus();
  }, 40000);

  test('excluir registro em uso (409): o motivo e "Desativar", que grava ativo=false e recarrega a lista (C2b)', async () => {
    const confirmar = vi.spyOn(Modal, 'confirm').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() }));
    const erro = vi.spyOn(message, 'error').mockImplementation(() => (() => undefined) as never);
    const sucesso = vi.spyOn(message, 'success').mockImplementation(() => (() => undefined) as never);
    const motivo = 'Este registro não pode ser excluído porque está em uso (Compras).';
    vi.mocked(deleteProduto).mockRejectedValue(
      Object.assign(new Error(motivo), { response: { status: 409, data: { detail: motivo, code: 'CONFLICT' } } }),
    );
    const user = userEvent.setup();
    renderPage();

    const nome = await screen.findByText(PRODUTO.nome, { selector: 'td, td *' }, { timeout: 15000 });
    await user.click(within(nome.closest<HTMLElement>('tr')!).getByRole('button', { name: `Excluir: ${PRODUTO.nome}` }));
    await confirmar.mock.calls[0]![0].onOk!();
    // O diálogo do 409 só abre quando a confirmação termina de fechar: um por vez, sem perder o foco.
    expect(confirmar).toHaveBeenCalledTimes(1);
    confirmar.mock.calls[0]![0].afterClose!();

    expect(erro).not.toHaveBeenCalled();
    expect(confirmar).toHaveBeenCalledTimes(2);
    const emUso = confirmar.mock.calls[1]![0];
    expect(String(emUso.content)).toContain(motivo);
    // O nome pode repetir; o código, não.
    expect(String(emUso.content)).toContain(`Você pode desativar o produto "${PRODUTO.nome}" (código ${PRODUTO.codigo})`);
    expect(emUso.okText).toBe('Desativar');
    const cargas = vi.mocked(listProdutos).mock.calls.length;
    await emUso.onOk!();

    expect(updateProduto).toHaveBeenCalledWith(PRODUTO.id, { ativo: false });
    expect(sucesso).toHaveBeenCalledWith('Produto desativado');
    await waitFor(() => expect(listProdutos).toHaveBeenCalledTimes(cargas + 1));
    confirmar.mockRestore();
    erro.mockRestore();
    sucesso.mockRestore();
  }, 30000);
});
