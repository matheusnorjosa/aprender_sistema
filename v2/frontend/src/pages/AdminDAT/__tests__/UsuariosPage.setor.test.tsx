/**
 * PR A — UsuariosPage mostra o setor pela lotação (vínculo EquipeGerencia), com o nome de tela.
 *
 * - Coluna "Setor" = `gerencia_atual.rotulo` (não mais os grupos de setor).
 * - Select de lotação e resumo usam `rotulo`; sai a dica "setor: {setor_canonico}".
 */
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';

const { USUARIOS, GERENCIAS } = vi.hoisted(() => ({
  USUARIOS: [
    {
      id: 7, username: 'coord.teste', email: 'coord@example.invalid', first_name: 'Coord', last_name: 'Teste',
      cpf_masked: '***.***.000-00', is_active: true, is_superuser: false,
      groups: ['Vidas', 'Coordenador'], group_ids_display: [1, 2],
      gerencia_atual: { gerencia_id: 4, rotulo: 'Superativar', nome_setor: 'ACerta', setor_canonico: 'Superativar', papel: 'COORDENADOR' },
    },
    {
      // lotado numa gerência que foi desativada (fora da lista de ativas do Select)
      id: 8, username: 'lotado.inativa', email: 'inativa@example.invalid', first_name: 'Lotado', last_name: 'Inativa',
      cpf_masked: '***.***.000-01', is_active: true, is_superuser: false,
      groups: ['Coordenador'], group_ids_display: [2],
      gerencia_atual: { gerencia_id: 9, rotulo: 'Setor Desativado', nome_setor: 'Antigo', setor_canonico: '', papel: 'COORDENADOR' },
    },
    {
      // Controle: opera por grupo, sem vínculo EquipeGerencia
      id: 9, username: 'controle.teste', email: 'controle@example.invalid', first_name: 'Ctrl', last_name: 'Teste',
      cpf_masked: '***.***.000-02', is_active: true, is_superuser: false,
      groups: ['Controle'], group_ids_display: [3],
      gerencia_atual: null,
    },
  ],
  GERENCIAS: [
    {
      id: 4, nome: 'GERENCIA 4', nome_setor: 'ACerta', nome_exibicao: 'Superativar', rotulo: 'Superativar',
      setor_canonico: 'Superativar', setor_canonico_confianca: '', gerente: null, gerente_nome: '', ativo: true,
      descricao: '', projetos_count: 0, created_at: '', updated_at: '',
    },
  ],
}));

vi.mock('../../../api/auth', () => ({
  checkAuth: vi.fn().mockResolvedValue({ authenticated: true, user: { is_superuser: true } }),
}));
vi.mock('../../../api/ops', () => ({ importUsuarios: vi.fn() }));
vi.mock('../../../api/adminDAT', () => ({
  listUsers: vi.fn().mockResolvedValue({ results: USUARIOS, count: 3, next: null, previous: null }),
  createUser: vi.fn(),
  updateUser: vi.fn(),
  deleteUser: vi.fn(),
  resetUserPassword: vi.fn(),
  listGroups: vi.fn().mockResolvedValue({
    results: [{ id: 1, name: 'Vidas' }, { id: 2, name: 'Coordenador' }], count: 2, next: null, previous: null,
  }),
  getRBACMeta: vi.fn().mockResolvedValue({
    setor_groups: ['Vidas', 'Controle'], funcao_groups: ['Coordenador'], categories: [], setores_produto: [],
  }),
  listGerencias: vi.fn().mockResolvedValue({ results: GERENCIAS, count: 1, next: null, previous: null }),
}));

import UsuariosPage from '../UsuariosPage';

function renderPage() {
  return render(
    <MemoryRouter>
      <UsuariosPage />
    </MemoryRouter>,
  );
}

describe('UsuariosPage — setor pela lotação (PR A)', () => {
  beforeEach(() => vi.clearAllMocks());

  test('a coluna Setor mostra o rótulo da gerência do vínculo, não o grupo', async () => {
    renderPage();
    expect(await screen.findByText('Superativar', {}, { timeout: 15000 })).toBeInTheDocument();
    expect(screen.queryByText('Vidas')).not.toBeInTheDocument();
  }, 20000);

  test('o resumo do formulário usa o rótulo e não mostra a dica "setor:"', async () => {
    const user = userEvent.setup();
    renderPage();
    const editBtns = await screen.findAllByRole('button', { name: /editar/i }, { timeout: 15000 });
    await user.click(editBtns[0]!);
    const dialog = await screen.findByRole('dialog', {}, { timeout: 10000 });

    expect(within(dialog).getAllByText('Superativar').length).toBeGreaterThan(0);
    expect(within(dialog).queryByText('ACerta')).not.toBeInTheDocument();
    expect(within(dialog).queryByText(/^setor:/)).not.toBeInTheDocument();
  }, 30000);

  test('lotação atual em gerência inativa aparece no Select pelo rótulo, não pelo id', async () => {
    const user = userEvent.setup();
    renderPage();
    const editBtns = await screen.findAllByRole('button', { name: /editar/i }, { timeout: 15000 });
    await user.click(editBtns[1]!);
    const dialog = await screen.findByRole('dialog', {}, { timeout: 10000 });

    expect(within(dialog).getByTitle('Setor Desativado')).toBeInTheDocument();
  }, 30000);

  test('sem vínculo, a coluna Setor cai para os grupos de setor (Controle continua "Controle")', async () => {
    renderPage();
    expect(await screen.findByText('Controle', {}, { timeout: 15000 })).toBeInTheDocument();
  }, 20000);
});
