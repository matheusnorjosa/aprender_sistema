/**
 * PR A — GerenciasPage mostra o nome de tela (`rotulo`), não o código interno (`nome`).
 *
 * - 1ª coluna "Setor" = `rotulo` (nome_exibicao || nome_setor); ordenação por rótulo.
 * - Campo novo "Nome na tela" (`nome_exibicao`).
 * - `nome` vira "Código interno", desabilitado na edição (chave técnica — seed e aprovação).
 * - `nome_setor` passa a se chamar "Rótulo nas planilhas" (chave do import).
 */
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { Modal } from 'antd';

const { GERENCIAS } = vi.hoisted(() => ({
  GERENCIAS: [
    {
      id: 4, nome: 'GERENCIA 4', nome_setor: 'ACerta', nome_exibicao: 'Superativar', rotulo: 'Superativar',
      setor_canonico: '', setor_canonico_confianca: '', gerente: null, gerente_nome: '', ativo: true,
      descricao: '', projetos_count: 3, created_at: '', updated_at: '',
    },
    {
      id: 2, nome: 'GERENCIA 2', nome_setor: 'Vidas', nome_exibicao: '', rotulo: 'Vidas',
      setor_canonico: '', setor_canonico_confianca: '', gerente: null, gerente_nome: '', ativo: true,
      descricao: '', projetos_count: 1, created_at: '', updated_at: '',
    },
  ],
}));

vi.mock('../../../api/adminDAT', () => ({
  listGerencias: vi.fn().mockResolvedValue({ results: GERENCIAS, count: 2, next: null, previous: null }),
  createGerencia: vi.fn().mockResolvedValue({}),
  updateGerencia: vi.fn().mockResolvedValue({}),
  deleteGerencia: vi.fn().mockResolvedValue({}),
  getRBACMeta: vi.fn().mockResolvedValue({ setor_groups: [], funcao_groups: [], categories: [], setores_produto: [] }),
}));

import GerenciasPage from '../GerenciasPage';
import { listGerencias, updateGerencia } from '../../../api/adminDAT';

function renderPage() {
  return render(
    <MemoryRouter>
      <GerenciasPage />
    </MemoryRouter>,
  );
}

describe('GerenciasPage — nome de tela (PR A)', () => {
  beforeEach(() => vi.clearAllMocks());

  test('a coluna "Setor" mostra o rótulo e a tabela não mostra o código interno', async () => {
    renderPage();
    expect(await screen.findByText('Superativar', {}, { timeout: 15000 })).toBeInTheDocument();
    expect(screen.queryByText('GERENCIA 4')).not.toBeInTheDocument();
    expect(listGerencias).toHaveBeenCalledWith(expect.objectContaining({ ordering: 'rotulo_ordem' }));
  }, 20000);

  test('editar: código interno desabilitado e "Nome na tela" gravável', async () => {
    const user = userEvent.setup();
    renderPage();
    const editBtns = await screen.findAllByRole('button', { name: /editar/i }, { timeout: 15000 });
    await user.click(editBtns[0]!);
    const dialog = await screen.findByRole('dialog', {}, { timeout: 10000 });

    expect(within(dialog).getByLabelText('Código interno')).toBeDisabled();
    expect(within(dialog).getByLabelText('Rótulo nas planilhas')).toHaveValue('ACerta');
    const nomeNaTela = within(dialog).getByLabelText('Nome na tela');
    expect(nomeNaTela).toHaveValue('Superativar');
    // continua com 1 combobox só (Select de setor_canônico)
    expect(within(dialog).getAllByRole('combobox')).toHaveLength(1);

    await user.clear(nomeNaTela);
    await user.type(nomeNaTela, 'Superativar Novo');
    await user.click(screen.getByRole('button', { name: /salvar/i }));
    await waitFor(
      () => expect(updateGerencia).toHaveBeenCalledWith(4, expect.objectContaining({ nome_exibicao: 'Superativar Novo' })),
      { timeout: 10000 },
    );
    expect(updateGerencia).not.toHaveBeenCalledWith(4, expect.objectContaining({ nome: expect.anything() }));
  }, 30000);

  test('o diálogo de exclusão cita o rótulo', async () => {
    // Modal.confirm (API estática do antd v5) não monta de forma confiável sob React 19 no
    // jsdom (ver PreAgendaPage.publish.test.tsx) — espia a chamada em vez de renderizar.
    // Com projetos ativos (3), excluir avisa que não pode e oferece Desativar (C2b); o restante está em
    // GerenciasPage.salvar.test.tsx.
    const infoSpy = vi.spyOn(Modal, 'confirm').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() }));
    const user = userEvent.setup();
    renderPage();
    const delBtns = await screen.findAllByRole('button', { name: /excluir/i }, { timeout: 15000 });
    await user.click(delBtns[0]!);
    expect(infoSpy).toHaveBeenCalledWith(
      expect.objectContaining({ title: 'Não é possível excluir', content: expect.stringContaining('"Superativar"') }),
    );
    infoSpy.mockRestore();
  }, 30000);
});
