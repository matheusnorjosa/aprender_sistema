/**
 * C2 (Programa C) — Gerências: salvar, excluir e estados que não mentem.
 *
 * - O erro de validação do backend aparece com o motivo, no campo (antes: "Erro de validação.").
 * - Salvar com loading; a exclusão começa no Cancelar, com acento; com projetos ativos vinculados,
 *   o aviso de que não pode, sem "Sim, excluir", com a saída: Desativar (C2b).
 * - O vocabulário de setor que não carregou avisa no campo, com "Tentar de novo".
 * - C2b: excluir em uso (409) mostra o motivo e oferece Desativar.
 */
import { act, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConfigProvider, Modal, message } from 'antd';
import ptBR from 'antd/locale/pt_BR';
import { MemoryRouter } from 'react-router';
import { beforeEach, describe, expect, test, vi } from 'vitest';

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

describe('GerenciasPage: salvar e excluir (C2)', () => {
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

  test('a marca "pergunta se pretende avaliar o formador" vai no payload (decisão do dono, 05/10/2026)', async () => {
    vi.mocked(updateGerencia).mockResolvedValue({ ...GERENCIAS[0]!, pergunta_avaliar_formador: false });
    const user = userEvent.setup();
    renderPage();

    const modal = await abrirEditar(user);
    const marca = within(modal).getByRole('checkbox', {
      name: 'Perguntar, na Nova Solicitação, se a pessoa pretende avaliar o formador',
    });
    expect(marca).toBeChecked();
    await user.click(marca);
    await user.click(within(modal).getByRole('button', { name: 'Salvar' }));

    await waitFor(() =>
      expect(updateGerencia).toHaveBeenCalledWith(7, expect.objectContaining({ pergunta_avaliar_formador: false })),
    );
  }, 40000);

  test('Salvar fica em loading enquanto a API trabalha', async () => {
    vi.mocked(updateGerencia).mockReturnValue(new Promise(() => undefined));
    const user = userEvent.setup();
    renderPage();

    const modal = await abrirEditar(user);
    await user.click(within(modal).getByRole('button', { name: 'Salvar' }));

    await waitFor(() => expect(within(modal).getByRole('button', { name: /Salvar/ })).toHaveClass('ant-btn-loading'));
  }, 40000);

  test('com projetos ativos, excluir avisa que não pode, sem "Sim, excluir", e oferece Desativar (C2b)', async () => {
    const confirmar = vi.spyOn(Modal, 'confirm').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() }));
    const avisar = vi.spyOn(Modal, 'info').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() }));
    const sucesso = vi.spyOn(message, 'success').mockImplementation(() => (() => undefined) as never);
    vi.mocked(updateGerencia).mockResolvedValue({ ...GERENCIAS[0]!, ativo: false });
    const user = userEvent.setup();
    renderPage();

    await user.click(within(await linha()).getByRole('button', { name: `Excluir: ${SETOR}` }));

    // A contagem já prova que o backend recusaria (PROTECT, 409): "Sim, excluir" só levaria ao erro.
    // Decisão do dono: quando não dá para excluir, a tela oferece Desativar.
    expect(avisar).not.toHaveBeenCalled();
    expect(confirmar).toHaveBeenCalledTimes(1);
    const aviso = confirmar.mock.calls[0]![0];
    expect(aviso.title).toBe('Não é possível excluir');
    expect(String(aviso.content)).toBe(
      `A gerência "${SETOR}" tem 5 projeto(s) ativo(s) vinculado(s). Gerência com projetos ou equipes vinculados,` +
        ` mesmo inativos, não pode ser excluída. Você pode desativar a gerência "${SETOR}": os projetos e a equipe` +
        ' continuam cadastrados, mas a gerência sai das listas de escolha em Projetos e Usuários, a equipe perde o' +
        ' acesso que tem por ela a Disponibilidade, Bloqueios e Deslocamentos, a situação passa a Inativo e dá para' +
        ' reativar em Editar.',
    );
    // Desativar gerência não é inofensivo: o texto não promete que "os vínculos continuam".
    expect(String(aviso.content)).not.toContain('os vínculos continuam');
    expect(aviso.okText).toBe('Desativar');
    expect(aviso.cancelText).toBe('Cancelar');
    expect(aviso.autoFocusButton).toBe('cancel');
    const cargas = vi.mocked(listGerencias).mock.calls.length;
    await aviso.onOk!();

    expect(deleteGerencia).not.toHaveBeenCalled();
    expect(updateGerencia).toHaveBeenCalledWith(7, { ativo: false });
    expect(sucesso).toHaveBeenCalledWith('Gerência desativada');
    await waitFor(() => expect(listGerencias).toHaveBeenCalledTimes(cargas + 1));
    confirmar.mockRestore();
    avisar.mockRestore();
    sucesso.mockRestore();
  }, 30000);

  test('com projetos ativos e a gerência já inativa: só o aviso (Entendi), sem Desativar', async () => {
    vi.mocked(listGerencias).mockResolvedValue({
      results: [{ ...GERENCIAS[0]!, ativo: false }], count: 1, next: null, previous: null,
    });
    const confirmar = vi.spyOn(Modal, 'confirm').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() }));
    const avisar = vi.spyOn(Modal, 'info').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() }));
    const user = userEvent.setup();
    renderPage();

    await user.click(within(await linha()).getByRole('button', { name: `Excluir: ${SETOR}` }));

    expect(confirmar).not.toHaveBeenCalled();
    const aviso = avisar.mock.calls[0]![0];
    expect(aviso.title).toBe('Não é possível excluir');
    expect(String(aviso.content)).toBe(
      `A gerência "${SETOR}" tem 5 projeto(s) ativo(s) vinculado(s). Gerência com projetos ou equipes vinculados,` +
        ' mesmo inativos, não pode ser excluída. O registro já está inativo.',
    );
    expect(aviso.okText).toBe('Entendi');
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

  test('excluir registro em uso (409): o motivo e "Desativar", que grava ativo=false e recarrega a lista (C2b)', async () => {
    const confirmar = vi.spyOn(Modal, 'confirm').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() }));
    const erro = vi.spyOn(message, 'error').mockImplementation(() => (() => undefined) as never);
    const sucesso = vi.spyOn(message, 'success').mockImplementation(() => (() => undefined) as never);
    const motivo = 'Este registro não pode ser excluído porque está em uso (Projetos).';
    vi.mocked(deleteGerencia).mockRejectedValue(
      Object.assign(new Error(motivo), { response: { status: 409, data: { detail: motivo, code: 'CONFLICT' } } }),
    );
    vi.mocked(updateGerencia).mockResolvedValue({ ...GERENCIAS[1]!, ativo: false });
    const user = userEvent.setup();
    renderPage();

    // Sem projeto ativo (só equipe ou projeto inativo): a confirmação abre e quem recusa é o backend.
    await user.click(within(await linha('Vidas')).getByRole('button', { name: 'Excluir: Vidas' }));
    await confirmar.mock.calls[0]![0].onOk!();
    // O diálogo do 409 só abre quando a confirmação termina de fechar: um por vez, sem perder o foco.
    expect(confirmar).toHaveBeenCalledTimes(1);
    confirmar.mock.calls[0]![0].afterClose!();

    expect(erro).not.toHaveBeenCalled();
    expect(confirmar).toHaveBeenCalledTimes(2);
    const emUso = confirmar.mock.calls[1]![0];
    expect(String(emUso.content)).toContain(motivo);
    expect(String(emUso.content)).toContain('Você pode desativar a gerência "Vidas"');
    // A consequência de desativar gerência, também no 409.
    expect(String(emUso.content)).toContain('a equipe perde o acesso que tem por ela a Disponibilidade, Bloqueios e Deslocamentos');
    expect(String(emUso.content)).not.toContain('os vínculos continuam');
    expect(emUso.okText).toBe('Desativar');
    const cargas = vi.mocked(listGerencias).mock.calls.length;
    await emUso.onOk!();

    expect(updateGerencia).toHaveBeenCalledWith(8, { ativo: false });
    expect(sucesso).toHaveBeenCalledWith('Gerência desativada');
    await waitFor(() => expect(listGerencias).toHaveBeenCalledTimes(cargas + 1));
    confirmar.mockRestore();
    erro.mockRestore();
    sucesso.mockRestore();
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
});
