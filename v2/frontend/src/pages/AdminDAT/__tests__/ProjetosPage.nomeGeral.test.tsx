/**
 * Marca "Nome geral" (`Projeto.eh_nome_geral`) na tela Projetos (regra da compra, 14/10/2026).
 *
 * Projeto marcado aceita compra de qualquer projeto da mesma gerência, no mesmo município, para
 * entrar na Nova Solicitação. A grade mostra a etiqueta junto do nome; o modal tem o interruptor
 * com o texto do efeito, e o valor vai no PATCH.
 */
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { beforeEach, describe, expect, test, vi } from 'vitest';

const { PROJETOS } = vi.hoisted(() => ({
  PROJETOS: [
    {
      id: 601,
      nome: 'Cataventos',
      codigo: 'CAT',
      fluxo: 'NAO_SUPER',
      ativo: true,
      setor: 'Vidas',
      setor_efetivo: 'Vidas',
      gerencia: 4,
      gerencia_nome: 'Vidas',
      projeto_geral: null,
      projeto_geral_nome: null,
      eh_serie: false,
      eh_nome_geral: true,
    },
    {
      id: 602,
      nome: 'Trânsito Legal',
      codigo: 'TL',
      fluxo: 'NAO_SUPER',
      ativo: true,
      setor: 'Vidas',
      setor_efetivo: 'Vidas',
      gerencia: 4,
      gerencia_nome: 'Vidas',
      projeto_geral: null,
      projeto_geral_nome: null,
      eh_serie: false,
      eh_nome_geral: false,
    },
  ],
}));

vi.mock('../../../api/adminDAT', () => ({
  listProjetos: vi.fn().mockResolvedValue({ results: PROJETOS, count: 2, next: null, previous: null }),
  createProjeto: vi.fn().mockResolvedValue({}),
  updateProjeto: vi.fn().mockResolvedValue({}),
  deleteProjeto: vi.fn().mockResolvedValue({}),
  getRBACMeta: vi.fn().mockResolvedValue({ setor_groups: [], funcao_groups: [], categories: [], setores_produto: ['Vidas'] }),
  listGerencias: vi.fn().mockResolvedValue({
    results: [{ id: 4, nome: 'GERENCIA 4', nome_setor: 'Vidas', nome_exibicao: '', rotulo: 'Vidas', ativo: true }],
    count: 1,
    next: null,
    previous: null,
  }),
}));

import ProjetosPage from '../ProjetosPage';
import { updateProjeto } from '../../../api/adminDAT';

const MARCADO = 'Cataventos';
const SEM_MARCA = 'Trânsito Legal';

function renderPage() {
  return render(
    <MemoryRouter>
      <ProjetosPage />
    </MemoryRouter>,
  );
}

async function linhaDe(nome: string): Promise<HTMLElement> {
  const celula = await screen.findByText(nome, { selector: 'td, td *' }, { timeout: 15000 });
  const linha = celula.closest('tr');
  if (!linha) throw new Error('o nome não está numa linha da tabela');
  return linha;
}

async function abrirEdicao(user: ReturnType<typeof userEvent.setup>, nome: string): Promise<HTMLElement> {
  const linha = await linhaDe(nome);
  await user.click(within(linha).getByRole('button', { name: `Editar: ${nome}` }));
  return screen.findByRole('dialog', {}, { timeout: 10000 });
}

describe('ProjetosPage — nome geral', () => {
  beforeEach(() => vi.clearAllMocks());

  test('a grade mostra a etiqueta "Nome geral" só no projeto marcado', async () => {
    renderPage();
    expect(within(await linhaDe(MARCADO)).getByText('Nome geral')).toBeInTheDocument();
    expect(within(await linhaDe(SEM_MARCA)).queryByText('Nome geral')).not.toBeInTheDocument();
  }, 20000);

  test('o interruptor abre com a marca e diz o efeito', async () => {
    const user = userEvent.setup();
    renderPage();
    const dialog = await abrirEdicao(user, MARCADO);

    expect(within(dialog).getByRole('switch', { name: 'Nome geral' })).toBeChecked();
    expect(within(dialog).getByText(/compra de qualquer projeto da mesma gerência, no mesmo município/)).toBeInTheDocument();
  }, 30000);

  test('ligar o interruptor envia eh_nome_geral=true no salvar', async () => {
    const user = userEvent.setup();
    renderPage();
    const dialog = await abrirEdicao(user, SEM_MARCA);

    const interruptor = within(dialog).getByRole('switch', { name: 'Nome geral' });
    expect(interruptor).not.toBeChecked();
    await user.click(interruptor);
    await user.click(within(dialog).getByRole('button', { name: /salvar/i }));

    await waitFor(
      () => expect(updateProjeto).toHaveBeenCalledWith(602, expect.objectContaining({ eh_nome_geral: true })),
      { timeout: 10000 },
    );
  }, 30000);
});
