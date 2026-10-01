/**
 * C2 (Programa C) — Gerências: salvar, excluir e estados que não mentem.
 *
 * - O erro de validação do backend aparece com o motivo, no campo (antes: "Erro de validação.").
 * - Salvar com loading; a exclusão começa no Cancelar, com acento; com projetos ativos vinculados,
 *   só o aviso de que não pode (Entendi), sem "Sim, excluir".
 * - O vocabulário de setor que não carregou avisa no campo, com "Tentar de novo".
 * - Confiança com rótulos de gente (Conferir/Média/Alta) e o filtro no topo, em qualquer largura:
 *   no cabeçalho da coluna, ele sumia abaixo de 768 px e deixava de valer sem aviso.
 */
import { act, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConfigProvider, Modal, message } from 'antd';
import ptBR from 'antd/locale/pt_BR';
import { MemoryRouter } from 'react-router';
import { beforeEach, describe, expect, test, vi } from 'vitest';

import { definirLarguraTela } from '../../../test/larguraTela';

const { GERENCIAS } = vi.hoisted(() => {
  const g = (id: number, rotulo: string, confianca: string, projetos: number) => ({
    id, nome: `GERENCIA ${id}`, nome_setor: rotulo, nome_exibicao: '', rotulo, setor_canonico: 'Vidas',
    setor_canonico_confianca: confianca, gerente: null, gerente_nome: '', ativo: true, descricao: '',
    projetos_count: projetos, created_at: '', updated_at: '',
  });
  return {
    GERENCIAS: [
      g(7, 'Formação Continuada', 'media', 5),
      g(8, 'Vidas', 'alta', 0),
      g(9, 'Fluir das Emoções', 'na', 1),
    ],
  };
});

vi.mock('../../../api/adminDAT', () => ({
  listGerencias: vi.fn(),
  createGerencia: vi.fn(),
  updateGerencia: vi.fn(),
  deleteGerencia: vi.fn(),
  getRBACMeta: vi.fn(),
}));

import { deleteGerencia, getRBACMeta, listGerencias, updateGerencia } from '../../../api/adminDAT';
import GerenciasPage from '../GerenciasPage';

const SETOR = 'Formação Continuada';

function renderPage() {
  return render(
    <ConfigProvider locale={ptBR}>
      <MemoryRouter>
        <GerenciasPage />
      </MemoryRouter>
    </ConfigProvider>,
  );
}

async function linha(nome = SETOR, acao = 'Editar'): Promise<HTMLElement> {
  return (await screen.findByRole('button', { name: `${acao}: ${nome}` }, { timeout: 15000 })).closest<HTMLElement>('tr')!;
}

async function abrirEditar(user: ReturnType<typeof userEvent.setup>): Promise<HTMLElement> {
  await user.click(within(await linha()).getByRole('button', { name: `Editar: ${SETOR}` }));
  return (await screen.findByText('Editar Gerencia', {}, { timeout: 10000 })).closest<HTMLElement>('[role="dialog"]')!;
}

describe('GerenciasPage: salvar, excluir e filtrar (C2)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(listGerencias).mockResolvedValue({ results: GERENCIAS, count: 3, next: null, previous: null });
    vi.mocked(getRBACMeta).mockResolvedValue({
      setor_groups: [], funcao_groups: [], categories: [], setores_produto: ['Vidas', 'Fluir'],
    });
  });

  test('erro de validação ao salvar: o motivo do backend no toast e no campo', async () => {
    const erro = vi.spyOn(message, 'error').mockImplementation(() => (() => undefined) as never);
    vi.mocked(updateGerencia).mockRejectedValue(
      Object.assign(new Error('Erro de validação.'), {
        response: { status: 400, data: { detail: 'Erro de validação.', errors: { nome_setor: ['Rótulo já usado por outra gerência.'] } } },
      }),
    );
    const user = userEvent.setup();
    renderPage();

    const modal = await abrirEditar(user);
    await user.click(within(modal).getByRole('button', { name: 'Salvar' }));

    await waitFor(() => expect(erro).toHaveBeenCalledWith('Erro: Rótulo já usado por outra gerência.'));
    expect(await within(modal).findByText('Rótulo já usado por outra gerência.')).toBeInTheDocument();
    erro.mockRestore();
  }, 40000);

  test('Salvar fica em loading enquanto a API trabalha', async () => {
    vi.mocked(updateGerencia).mockReturnValue(new Promise(() => undefined));
    const user = userEvent.setup();
    renderPage();

    const modal = await abrirEditar(user);
    await user.click(within(modal).getByRole('button', { name: 'Salvar' }));

    await waitFor(() => expect(within(modal).getByRole('button', { name: /Salvar/ })).toHaveClass('ant-btn-loading'));
  }, 40000);

  test('com projetos ativos, excluir só avisa que não pode (Entendi), sem botão de excluir', async () => {
    const confirmar = vi.spyOn(Modal, 'confirm').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() }));
    const avisar = vi.spyOn(Modal, 'info').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() }));
    const user = userEvent.setup();
    renderPage();

    await user.click(within(await linha()).getByRole('button', { name: `Excluir: ${SETOR}` }));

    // A contagem já prova que o backend recusaria (PROTECT, 409): "Sim, excluir" só levaria ao erro.
    expect(confirmar).not.toHaveBeenCalled();
    expect(avisar).toHaveBeenCalledTimes(1);
    const aviso = avisar.mock.calls[0]![0];
    expect(aviso.title).toBe('Não é possível excluir');
    expect(String(aviso.content)).toBe(
      `A gerência "${SETOR}" tem 5 projeto(s) ativo(s) vinculado(s). Gerência com projetos ou equipes vinculados,` +
        ' mesmo inativos, não pode ser excluída.',
    );
    expect(aviso.okText).toBe('Entendi');
    expect(aviso.onOk).toBeUndefined();
    expect(deleteGerencia).not.toHaveBeenCalled();
    confirmar.mockRestore();
    avisar.mockRestore();
  }, 30000);

  test('sem projetos ativos, a confirmação normal: título com acento, cita o nome e começa no Cancelar', async () => {
    const confirmar = vi.spyOn(Modal, 'confirm').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() }));
    const avisar = vi.spyOn(Modal, 'info').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() }));
    const user = userEvent.setup();
    renderPage();

    await user.click(within(await linha('Vidas')).getByRole('button', { name: 'Excluir: Vidas' }));

    // Equipe ou projeto inativo vinculado também barram, mas quem diz é o backend (409 com o motivo).
    expect(avisar).not.toHaveBeenCalled();
    const opcoes = confirmar.mock.calls[0]![0];
    expect(opcoes.title).toBe('Confirmar exclusão');
    expect(String(opcoes.content)).toBe('Tem certeza que deseja excluir a gerência "Vidas"?');
    expect(opcoes.okText).toBe('Sim, excluir');
    expect(opcoes.autoFocusButton).toBe('cancel');
    confirmar.mockRestore();
    avisar.mockRestore();
  }, 30000);

  test('excluir registro em uso: o motivo do backend (409) no toast', async () => {
    const confirmar = vi.spyOn(Modal, 'confirm').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() }));
    const erro = vi.spyOn(message, 'error').mockImplementation(() => (() => undefined) as never);
    const motivo = 'Este registro não pode ser excluído porque está em uso (Projetos).';
    vi.mocked(deleteGerencia).mockRejectedValue(
      Object.assign(new Error(motivo), { response: { status: 409, data: { detail: motivo, code: 'CONFLICT' } } }),
    );
    const user = userEvent.setup();
    renderPage();

    // Sem projeto ativo (só equipe ou projeto inativo): a confirmação abre e quem recusa é o backend.
    await user.click(within(await linha('Vidas')).getByRole('button', { name: 'Excluir: Vidas' }));
    await confirmar.mock.calls[0]![0].onOk!();

    expect(erro).toHaveBeenCalledWith(`Erro ao excluir: ${motivo}`);
    confirmar.mockRestore();
    erro.mockRestore();
  }, 30000);

  test('setores não carregaram: aviso e "Tentar de novo" fora do Select, alcançáveis pelo Tab', async () => {
    vi.mocked(getRBACMeta).mockRejectedValueOnce(new Error('Falha de rede'));
    const user = userEvent.setup();
    renderPage();

    const modal = await abrirEditar(user);
    // Sem abrir o Select: dentro do dropdown (portal) o botão ficava fora do Tab e o alerta, dentro do listbox.
    const alerta = await within(modal).findByRole('alert');
    expect(alerta).toHaveTextContent('Não foi possível carregar os setores.');
    expect(alerta).toHaveTextContent('Falha de rede');
    expect(within(modal).getByRole('combobox', { name: /Setor canônico/ })).toBeDisabled();

    within(modal).getByLabelText('Rótulo nas planilhas').focus();
    await user.tab();
    expect(within(alerta).getByRole('button', { name: 'Tentar de novo: carregar os setores' })).toHaveFocus();

    await user.keyboard('{Enter}');
    await waitFor(() => expect(getRBACMeta).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(within(modal).queryByRole('alert')).not.toBeInTheDocument());
    expect(within(modal).getByRole('combobox', { name: /Setor canônico/ })).toBeEnabled();
  }, 40000);

  test('"Tentar de novo" dos setores diz o que recarrega', async () => {
    vi.mocked(getRBACMeta).mockRejectedValueOnce(new Error('Falha de rede'));
    const user = userEvent.setup();
    renderPage();

    const alerta = await within(await abrirEditar(user)).findByRole('alert');
    // O nome começa pelo texto visível (WCAG 2.5.3) e diz o que recarrega.
    expect(within(alerta).getByRole('button', { name: 'Tentar de novo: carregar os setores' })).toHaveTextContent(/^Tentar de novo$/);
  }, 40000);

  test('"Tentar de novo" dos setores: falhou de novo, o foco fica no botão; carregou, vai para o campo', async () => {
    vi.mocked(getRBACMeta)
      .mockRejectedValueOnce(new Error('Falha de rede'))
      .mockRejectedValueOnce(new Error('Falha de novo'));
    const user = userEvent.setup();
    renderPage();
    const modal = await abrirEditar(user);
    const botao = (): HTMLElement => within(within(modal).getByRole('alert')).getByRole('button', { name: /^Tentar de novo/ });
    await within(modal).findByRole('alert');

    botao().focus();
    await user.keyboard('{Enter}');
    await waitFor(() => expect(within(modal).getByRole('alert')).toHaveTextContent('Falha de novo'));
    await waitFor(() => expect(botao()).not.toHaveClass('ant-btn-loading'));
    expect(botao()).toHaveFocus();

    await user.keyboard('{Enter}');
    await waitFor(() => expect(within(modal).queryByRole('alert')).not.toBeInTheDocument());
    expect(within(modal).getByRole('combobox', { name: /Setor canônico/ })).toHaveFocus();
  }, 40000);

  test('"Tentar de novo" dos setores: se a pessoa já foi digitar em outro campo, a resposta não leva o foco', async () => {
    let responder: (meta: Awaited<ReturnType<typeof getRBACMeta>>) => void = () => undefined;
    vi.mocked(getRBACMeta)
      .mockRejectedValueOnce(new Error('Falha de rede'))
      .mockImplementationOnce(() => new Promise((resolver) => { responder = resolver; }));
    const user = userEvent.setup();
    renderPage();
    const modal = await abrirEditar(user);
    const alerta = await within(modal).findByRole('alert');

    within(alerta).getByRole('button', { name: /^Tentar de novo/ }).focus();
    await user.keyboard('{Enter}');
    await waitFor(() => expect(getRBACMeta).toHaveBeenCalledTimes(2));
    const nome = within(modal).getByLabelText('Nome na tela');
    await user.click(nome);
    await user.keyboard('Super');

    await act(async () => {
      responder({ setor_groups: [], funcao_groups: [], categories: [], setores_produto: ['Vidas', 'Fluir'] });
    });
    await waitFor(() => expect(within(modal).queryByRole('alert')).not.toBeInTheDocument());
    expect(nome).toHaveFocus();
    await user.keyboard('ativar');
    expect(nome).toHaveValue('Superativar');
  }, 40000);

  test('falha ao carregar a lista: o motivo e "Tentar de novo", não "Não há dados"', async () => {
    vi.mocked(listGerencias).mockRejectedValue(new Error('Você não tem permissão para realizar esta ação.'));
    renderPage();

    const alerta = await screen.findByText('Não foi possível carregar a lista.', {}, { timeout: 15000 });
    expect(alerta.closest('[role="alert"]')).toHaveTextContent('Você não tem permissão para realizar esta ação.');
    expect(screen.queryByText('Não há dados')).not.toBeInTheDocument();
    // Sem número no título: "(0)" diria que não há gerência.
    expect(screen.getByRole('heading', { level: 3 })).toHaveTextContent(/^Gerencias$/);
  }, 30000);

  test('confiança com rótulos de gente e filtro no topo que vale também a 360 px', async () => {
    definirLarguraTela(360);
    const user = userEvent.setup();
    renderPage();
    await linha(SETOR, 'Mais ações');

    await user.click(screen.getByRole('combobox', { name: 'Filtrar por confiança' }));
    await user.click(await screen.findByTitle('Conferir'));

    await waitFor(() => expect(screen.queryByRole('button', { name: `Mais ações: ${SETOR}` })).not.toBeInTheDocument());
    const conferir = await linha('Fluir das Emoções', 'Mais ações');
    expect(screen.queryByRole('button', { name: 'Mais ações: Vidas' })).not.toBeInTheDocument();

    await user.click(within(conferir).getByRole('button', { name: 'Expandir linha de Fluir das Emoções' }));
    const expandida = within(document.querySelector<HTMLElement>('.ant-table-expanded-row')!);
    expect(expandida.getByText('Conferir')).toBeInTheDocument();
  }, 40000);
});
