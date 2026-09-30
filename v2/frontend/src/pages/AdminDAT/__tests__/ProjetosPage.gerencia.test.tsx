/**
 * Regra do dono (30/09): fluxo SUPER só em projeto da gerência Superintendência. A trava do backend
 * deixou a ProjetosPage sem caminho para cadastrar SUPER (a tela não mandava `gerencia`).
 *
 * - Campo "Gerência": Select pelas gerências ATIVAS, pelo rótulo de tela (PR A); obrigatório ao criar
 *   (todo projeto pertence a uma gerência — decisão do dono 29/09).
 * - Edição: pré-preenchido com a gerência atual (inativa aparece pelo rótulo, não pelo id); não é
 *   obrigatório, para projeto antigo sem gerência continuar salvando.
 * - 400 da trava (erro sem campo) aparece junto do campo Gerência e some ao abrir outro projeto.
 * - Lista de gerências indisponível: o modal diz o motivo e que sem ela não dá para criar.
 */
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';

const { PROJETOS, GERENCIAS, MSG_TRAVA } = vi.hoisted(() => ({
  PROJETOS: [
    { id: 10, nome: 'Projeto Super', codigo: 'PS', fluxo: 'SUPER', ativo: true, setor: '', setor_efetivo: 'Super', gerencia: 1, gerencia_nome: 'Superintendência' },
    // gerência desativada: fora da lista de ativas do Select
    { id: 11, nome: 'Projeto Antigo', codigo: 'PA', fluxo: 'NAO_SUPER', ativo: true, setor: '', setor_efetivo: '', gerencia: 9, gerencia_nome: 'Setor Antigo' },
    // mesma gerência (Vidas) da tentativa que a trava recusa no teste do 400
    { id: 12, nome: 'Projeto Vidas', codigo: 'PV', fluxo: 'NAO_SUPER', ativo: true, setor: '', setor_efetivo: '', gerencia: 4, gerencia_nome: 'Vidas' },
    // projeto antigo sem gerência
    { id: 13, nome: 'Projeto Sem Gerencia', codigo: 'PSG', fluxo: 'NAO_SUPER', ativo: true, setor: '', setor_efetivo: '', gerencia: null, gerencia_nome: null },
  ],
  GERENCIAS: [
    { id: 4, nome: 'GERENCIA 4', nome_setor: 'Vidas', nome_exibicao: '', rotulo: 'Vidas', ativo: true },
    { id: 1, nome: 'SUPERINTENDENCIA', nome_setor: 'Super', nome_exibicao: 'Superintendência', rotulo: 'Superintendência', ativo: true },
  ],
  MSG_TRAVA: 'Fluxo SUPER só é permitido em projeto da gerência Superintendência.',
}));

vi.mock('../../../api/adminDAT', () => ({
  listProjetos: vi.fn().mockResolvedValue({ results: PROJETOS, count: 4, next: null, previous: null }),
  createProjeto: vi.fn().mockResolvedValue({}),
  updateProjeto: vi.fn().mockResolvedValue({}),
  deleteProjeto: vi.fn().mockResolvedValue({}),
  getRBACMeta: vi.fn().mockResolvedValue({ setor_groups: [], funcao_groups: [], categories: [], setores_produto: [] }),
  listGerencias: vi.fn().mockResolvedValue({ results: GERENCIAS, count: 2, next: null, previous: null }),
}));

import ProjetosPage from '../ProjetosPage';
import { createProjeto, updateProjeto, listGerencias } from '../../../api/adminDAT';

function renderPage() {
  return render(
    <MemoryRouter>
      <ProjetosPage />
    </MemoryRouter>,
  );
}

async function abrirNovo(user: ReturnType<typeof userEvent.setup>): Promise<HTMLElement> {
  await user.click(await screen.findByRole('button', { name: /novo projeto/i }, { timeout: 15000 }));
  const dialog = await screen.findByRole('dialog', {}, { timeout: 10000 });
  await user.type(within(dialog).getByLabelText('Nome do Projeto'), 'Projeto Novo');
  await user.type(within(dialog).getByLabelText('Código'), 'PN');
  return dialog;
}

describe('ProjetosPage — gerência do projeto (trava SUPER, 30/09)', () => {
  beforeEach(() => vi.clearAllMocks());

  test('cria SUPER escolhendo a Superintendência: o payload leva a gerência', async () => {
    const user = userEvent.setup();
    renderPage();
    const dialog = await abrirNovo(user);

    await user.click(within(dialog).getByRole('combobox', { name: 'Gerência' }));
    await user.click(await screen.findByTitle('Superintendência'));
    await user.click(within(dialog).getByLabelText('Aprovação Manual'));
    await user.click(screen.getByRole('button', { name: /salvar/i }));

    await waitFor(
      () => expect(createProjeto).toHaveBeenCalledWith(expect.objectContaining({ fluxo: 'SUPER', gerencia: 1 })),
      { timeout: 10000 },
    );
    expect(listGerencias).toHaveBeenCalledWith(expect.objectContaining({ ativo: true }));
  }, 30000);

  test('gerência é obrigatória ao criar', async () => {
    const user = userEvent.setup();
    renderPage();
    const dialog = await abrirNovo(user);

    await user.click(screen.getByRole('button', { name: /salvar/i }));

    expect(await within(dialog).findByText('Gerência é obrigatória', {}, { timeout: 10000 })).toBeInTheDocument();
    expect(createProjeto).not.toHaveBeenCalled();
  }, 30000);

  test('editar mantém a gerência atual no payload', async () => {
    const user = userEvent.setup();
    renderPage();
    const editBtns = await screen.findAllByRole('button', { name: /editar/i }, { timeout: 15000 });
    await user.click(editBtns[0]!);
    await screen.findByRole('dialog', {}, { timeout: 10000 });

    await user.click(screen.getByRole('button', { name: /salvar/i }));

    await waitFor(
      () => expect(updateProjeto).toHaveBeenCalledWith(10, expect.objectContaining({ gerencia: 1, fluxo: 'SUPER' })),
      { timeout: 10000 },
    );
  }, 30000);

  test('gerência atual inativa aparece pelo rótulo, não pelo id', async () => {
    const user = userEvent.setup();
    renderPage();
    const editBtns = await screen.findAllByRole('button', { name: /editar/i }, { timeout: 15000 });
    await user.click(editBtns[1]!);
    const dialog = await screen.findByRole('dialog', {}, { timeout: 10000 });

    expect(within(dialog).getByTitle('Setor Antigo')).toBeInTheDocument();
  }, 30000);

  test('o 400 da trava aparece junto do campo Gerência', async () => {
    const erro = Object.assign(new Error(MSG_TRAVA), {
      status: 400,
      response: {
        status: 400,
        data: { detail: MSG_TRAVA, code: 'VALIDATION_ERROR', errors: { non_field_errors: [MSG_TRAVA] } },
      },
    });
    vi.mocked(createProjeto).mockRejectedValueOnce(erro);
    const user = userEvent.setup();
    renderPage();
    const dialog = await abrirNovo(user);
    await user.click(within(dialog).getByRole('combobox', { name: 'Gerência' }));
    await user.click(await screen.findByTitle('Vidas'));
    await user.click(within(dialog).getByLabelText('Aprovação Manual'));

    await user.click(screen.getByRole('button', { name: /salvar/i }));

    const aviso = await within(dialog).findByText(MSG_TRAVA, {}, { timeout: 10000 });
    const campo = aviso.closest('.ant-form-item');
    expect(campo).not.toBeNull();
    expect(within(campo as HTMLElement).getByText('Gerência')).toBeInTheDocument();

    // O aviso não sobra para o próximo projeto aberto, mesmo com a MESMA gerência (Vidas): o
    // setFieldsValue só limpa o erro de campo cujo valor muda.
    await user.click(within(dialog).getByRole('button', { name: /cancelar/i }));
    await user.click(within(linhaDo('Projeto Vidas')).getByRole('button', { name: /editar/i }));
    await waitFor(() => expect(within(dialog).getByLabelText('Nome do Projeto')).toHaveValue('Projeto Vidas'), {
      timeout: 10000,
    });
    await waitFor(() => expect(screen.queryByText(MSG_TRAVA)).not.toBeInTheDocument(), { timeout: 10000 });
  }, 40000);

  test('na edição a gerência não é obrigatória: projeto antigo sem gerência salva sem escolher', async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(within(await linhaDoAsync('Projeto Sem Gerencia')).getByRole('button', { name: /editar/i }));
    const dialog = await screen.findByRole('dialog', {}, { timeout: 10000 });
    const nome = within(dialog).getByLabelText('Nome do Projeto');
    await user.clear(nome);
    await user.type(nome, 'Projeto Renomeado');

    await user.click(screen.getByRole('button', { name: /salvar/i }));

    await waitFor(
      () => expect(updateProjeto).toHaveBeenCalledWith(13, expect.objectContaining({ nome: 'Projeto Renomeado' })),
      { timeout: 10000 },
    );
    expect(vi.mocked(updateProjeto).mock.calls[0]![1].gerencia).toBeUndefined();
    expect(within(dialog).queryByText('Gerência é obrigatória')).not.toBeInTheDocument();
  }, 30000);

  test('sem a lista de gerências o modal mostra o motivo e avisa que não dá para criar', async () => {
    vi.mocked(listGerencias).mockRejectedValueOnce(new Error('Serviço de gerências indisponível (500)'));
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: /novo projeto/i }, { timeout: 15000 }));
    const dialog = await screen.findByRole('dialog', {}, { timeout: 10000 });

    const alerta = await within(dialog).findByRole('alert', {}, { timeout: 10000 });
    expect(alerta).toHaveTextContent('Serviço de gerências indisponível (500)');
    expect(alerta).toHaveTextContent(/não dá para criar projeto/i);
  }, 30000);
});

function linhaDo(nome: string): HTMLElement {
  return screen.getByText(nome).closest('tr') as HTMLElement;
}

async function linhaDoAsync(nome: string): Promise<HTMLElement> {
  return (await screen.findByText(nome, {}, { timeout: 15000 })).closest('tr') as HTMLElement;
}
