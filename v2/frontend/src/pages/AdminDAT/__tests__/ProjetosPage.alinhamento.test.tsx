/**
 * Projetos, lote C do alinhamento (06/11/2026).
 *
 * - "Em espera" (D41): o projeto sem compra que o libere some da Nova Solicitação; a lista diz por quê.
 * - Fluxo NAO_SUPER: "aprovado na criação", e sem compra vai para aprovação (D43, D28); não "Auto".
 * - Erros do servidor no campo certo (D73): nome repetido no Nome, série com nome geral no Nome geral, e o
 *   toast com o motivo, não "Erro de validação.".
 * - Falha ao carregar a lista: o motivo e "Tentar de novo", e o título sem "(0)".
 */
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { message } from 'antd';
import { MemoryRouter } from 'react-router';
import { beforeEach, describe, expect, test, vi } from 'vitest';

const { PROJETOS, GERENCIAS } = vi.hoisted(() => ({
  PROJETOS: [
    {
      id: 10, nome: 'Projeto Liberado', codigo: 'PL', fluxo: 'NAO_SUPER', ativo: true, setor: '', setor_efetivo: '',
      gerencia: 4, gerencia_nome: 'Vidas', em_espera: false,
    },
    {
      id: 11, nome: 'Projeto Parado', codigo: 'PP', fluxo: 'NAO_SUPER', ativo: true, setor: '', setor_efetivo: '',
      gerencia: 4, gerencia_nome: 'Vidas', em_espera: true,
    },
  ],
  GERENCIAS: [{ id: 4, nome: 'GERENCIA 4', nome_setor: 'Vidas', nome_exibicao: '', rotulo: 'Vidas', ativo: true }],
}));

vi.mock('../../../api/adminDAT', () => ({
  listProjetos: vi.fn(),
  createProjeto: vi.fn(),
  updateProjeto: vi.fn(),
  deleteProjeto: vi.fn(),
  getRBACMeta: vi.fn().mockResolvedValue({ setor_groups: [], funcao_groups: [], categories: [], setores_produto: [] }),
  listGerencias: vi.fn().mockResolvedValue({ results: GERENCIAS, count: 1, next: null, previous: null }),
}));

import { createProjeto, listProjetos, updateProjeto } from '../../../api/adminDAT';
import ProjetosPage from '../ProjetosPage';

function renderPage() {
  return render(
    <MemoryRouter>
      <ProjetosPage />
    </MemoryRouter>,
  );
}

function erro400(errors: Record<string, string[]>) {
  return Object.assign(new Error('Erro de validação.'), {
    response: { status: 400, data: { detail: 'Erro de validação.', code: 'VALIDATION_ERROR', errors } },
  });
}

async function linha(nome: string): Promise<HTMLElement> {
  return (await screen.findByText(nome, {}, { timeout: 15000 })).closest('tr') as HTMLElement;
}

async function editar(user: ReturnType<typeof userEvent.setup>, nome: string): Promise<HTMLElement> {
  await user.click(within(await linha(nome)).getByRole('button', { name: `Editar: ${nome}` }));
  return screen.findByRole('dialog', {}, { timeout: 10000 });
}

function campoDe(aviso: HTMLElement): HTMLElement {
  const campo = aviso.closest<HTMLElement>('.ant-form-item');
  if (!campo) throw new Error('o aviso não está num campo');
  return campo;
}

describe('ProjetosPage — alinhamento (lote C)', { timeout: 45000 }, () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(listProjetos).mockResolvedValue({ results: PROJETOS, count: 2, next: null, previous: null } as never);
  });

  test('o projeto em espera tem a etiqueta "Em espera"; o liberado, não', async () => {
    renderPage();

    expect(within(await linha('Projeto Parado')).getByText('Em espera')).toBeInTheDocument();
    expect(within(await linha('Projeto Liberado')).queryByText('Em espera')).not.toBeInTheDocument();
  });

  test('NAO_SUPER diz "aprovado na criação", e o formulário avisa que sem compra vai para aprovação', async () => {
    const user = userEvent.setup();
    renderPage();

    expect(within(await linha('Projeto Liberado')).getByText('NAO_SUPER (aprovado na criação)')).toBeInTheDocument();
    expect(screen.queryByText(/Auto/)).not.toBeInTheDocument();
    const dialog = await editar(user, 'Projeto Liberado');
    expect(within(dialog).getByLabelText('Aprovado na criação (sem compra vai para aprovação)')).toBeChecked();
    expect(within(dialog).queryByText('Auto-aprovado')).not.toBeInTheDocument();
  });

  test('nome repetido: o motivo no campo Nome e no toast', async () => {
    const toast = vi.spyOn(message, 'error');
    vi.mocked(updateProjeto).mockRejectedValueOnce(erro400({ nome: ['projeto com este nome já existe.'] }));
    const user = userEvent.setup();
    renderPage();
    const dialog = await editar(user, 'Projeto Liberado');

    await user.click(within(dialog).getByRole('button', { name: /salvar/i }));

    const aviso = await within(dialog).findByText('projeto com este nome já existe.', {}, { timeout: 10000 });
    expect(within(campoDe(aviso)).getByText('Nome do Projeto')).toBeInTheDocument();
    expect(toast).toHaveBeenCalledWith('Erro: projeto com este nome já existe.');
    toast.mockRestore();
  });

  test('série com nome geral: o motivo no campo Nome geral, não na Gerência', async () => {
    const msg = 'Série não pode ser nome geral: desmarque uma das duas.';
    vi.mocked(createProjeto).mockRejectedValueOnce(erro400({ eh_nome_geral: [msg] }));
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: /novo projeto/i }, { timeout: 15000 }));
    const dialog = await screen.findByRole('dialog', {}, { timeout: 10000 });
    await user.type(within(dialog).getByLabelText('Nome do Projeto'), 'Projeto Novo');
    await user.type(within(dialog).getByLabelText('Código'), 'PN');
    await user.click(within(dialog).getByRole('combobox', { name: 'Gerência' }));
    await user.click(await screen.findByTitle('Vidas'));

    await user.click(within(dialog).getByRole('button', { name: /salvar/i }));

    const aviso = await within(dialog).findByText(msg, {}, { timeout: 10000 });
    expect(within(campoDe(aviso)).getByText('Nome geral')).toBeInTheDocument();
  });

  test('falha ao carregar a lista: o motivo, "Tentar de novo" e o título sem "(0)"', async () => {
    vi.mocked(listProjetos).mockRejectedValueOnce(new Error('Serviço indisponível (500)'));
    const user = userEvent.setup();
    renderPage();

    const alerta = await screen.findByText('Não foi possível carregar a lista.', {}, { timeout: 15000 });
    expect(alerta.closest('[role="alert"]')).toHaveTextContent('Serviço indisponível (500)');
    expect(screen.getByRole('heading', { level: 3 })).toHaveTextContent(/^Projetos$/);

    await user.click(screen.getByRole('button', { name: /^Tentar de novo/ }));
    expect(await linha('Projeto Parado')).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole('heading', { level: 3 })).toHaveTextContent('Projetos (2)'));
  });
});
