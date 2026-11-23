/**
 * LIB-64 (23/11/2026): o superusuário editou a própria conta só para mudar o nome e recebeu "Você não pode
 * modificar seus próprios grupos.": o Salvar reenviava as funções em todo salvar.
 *
 * - Na própria conta, o campo de funções fica travado com o motivo, e o Salvar não manda `group_ids`
 *   (a gerência segue indo: a própria lotação o superusuário altera).
 * - Na conta de outra pessoa, nada muda: funções abertas e `group_ids` no payload.
 */
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';

import { ComAcesso } from '../../../test/comAcesso';
import { buildUsuarioPayload, type UsuarioFormValues } from '../usuario_form_helpers';

const { USUARIOS, GERENCIAS } = vi.hoisted(() => {
  const vidas = { gerencia_id: 7, rotulo: 'Vidas', nome_setor: 'Vidas', setor_canonico: 'Vidas', papel: 'FORMADOR' };
  const usuario = (id: number, nome: string, extra: Record<string, unknown>) => ({
    id, username: `teste.${id}`, email: `teste.${id}@example.invalid`, first_name: nome, last_name: 'Teste',
    cpf_masked: `***.***.000-${id}`, is_active: true, is_superuser: false, groups: ['Formador'],
    group_ids_display: [2], gerencia_atual: vidas, equipe_administrativa: false, lotacao_reservada: false, ...extra,
  });
  return {
    GERENCIAS: [{
      id: 7, nome: 'GERENCIA VIDAS', nome_setor: 'Vidas', nome_exibicao: 'Vidas', rotulo: 'Vidas',
      setor_canonico: 'Vidas', setor_canonico_confianca: '', gerente: null, gerente_nome: '', ativo: true,
      descricao: '', projetos_count: 0, created_at: '', updated_at: '', lotacao_reservada: false,
    }],
    USUARIOS: [usuario(31, 'Outra', {}), usuario(99, 'Propria', { is_superuser: true })],
  };
});

vi.mock('../../../api/auth', () => ({
  checkAuth: vi.fn().mockResolvedValue({ authenticated: true, user: { id: 99, is_superuser: true } }),
}));
vi.mock('../../../api/ops', () => ({ importUsuarios: vi.fn() }));
vi.mock('../../../api/adminDAT', () => ({
  listUsers: vi.fn().mockResolvedValue({ results: USUARIOS, count: 2, next: null, previous: null }),
  createUser: vi.fn().mockResolvedValue({}),
  updateUser: vi.fn().mockResolvedValue({}),
  deleteUser: vi.fn(),
  resetUserPassword: vi.fn(),
  getUserPolicies: vi.fn().mockResolvedValue([]),
  listGroups: vi.fn().mockResolvedValue({
    results: [{ id: 2, name: 'Formador' }], count: 1, next: null, previous: null,
  }),
  getRBACMeta: vi.fn().mockResolvedValue({
    setor_groups: ['Vidas'], funcao_groups: ['Formador'], categories: [], setores_produto: [],
  }),
  listGerencias: vi.fn().mockResolvedValue({ results: GERENCIAS, count: 1, next: null, previous: null }),
}));

import { updateUser } from '../../../api/adminDAT';
import UsuariosPage from '../UsuariosPage';

function renderPage() {
  return render(
    <ComAcesso policies={['manage_admin_registries']}>
      <MemoryRouter>
        <UsuariosPage />
      </MemoryRouter>
    </ComAcesso>,
  );
}

async function editar(user: ReturnType<typeof userEvent.setup>, indice: number): Promise<HTMLElement> {
  const editBtns = await screen.findAllByRole('button', { name: /editar/i }, { timeout: 15000 });
  await user.click(editBtns[indice]!);
  return screen.findByRole('dialog', {}, { timeout: 10000 });
}

const funcoesDoForm = (dialog: HTMLElement): HTMLElement =>
  within(dialog).getByRole('combobox', { name: /função \(cargo\)/i });
const gerenciaDoForm = (dialog: HTMLElement): HTMLElement =>
  within(dialog).getByRole('combobox', { name: /gerência \(onde trabalha\)/i });

const BASE: UsuarioFormValues = {
  email: 'u@example.invalid',
  first_name: 'Nome',
  is_active: true,
  is_superuser: true,
  gerencia_id: 7,
  funcao_ids: [2],
};

describe('buildUsuarioPayload — a própria conta (LIB-64)', () => {
  test('o superusuário na própria conta não manda group_ids; a gerência segue', () => {
    const payload = buildUsuarioPayload(BASE, {
      isEditing: true, cpfEditUnlocked: false, currentIsSuperuser: true, propriaConta: true,
    });
    expect(payload).not.toHaveProperty('group_ids');
    expect(payload).toMatchObject({ first_name: 'Nome', gerencia_id: 7, is_superuser: true });
  });

  test('na conta de outra pessoa, group_ids segue indo', () => {
    const payload = buildUsuarioPayload(BASE, { isEditing: true, cpfEditUnlocked: false, currentIsSuperuser: true });
    expect(payload).toMatchObject({ group_ids: [2], gerencia_id: 7 });
  });
});

describe('UsuariosPage — o superusuário na própria conta (LIB-64)', () => {
  beforeEach(() => vi.clearAllMocks());

  test('funções travadas com o motivo e o Salvar sem group_ids', async () => {
    const user = userEvent.setup();
    renderPage();
    const dialog = await editar(user, 1);

    expect(await within(dialog).findByText('Suas funções só outro superusuário altera.')).toBeInTheDocument();
    await vi.waitFor(() => expect(gerenciaDoForm(dialog)).toBeEnabled(), { timeout: 10000 });
    expect(funcoesDoForm(dialog)).toBeDisabled();
    // R4: o motivo é a descrição acessível do campo travado (o leitor de tela o ouve junto do campo).
    expect(funcoesDoForm(dialog)).toHaveAccessibleDescription('Suas funções só outro superusuário altera.');
    await user.click(within(dialog).getByRole('button', { name: /^salvar$/i }));

    await vi.waitFor(() => expect(updateUser).toHaveBeenCalled(), { timeout: 10000 });
    const payload = vi.mocked(updateUser).mock.calls[0]![1];
    expect(payload).not.toHaveProperty('group_ids');
    expect(payload).toMatchObject({ gerencia_id: 7 });
  }, 40000);

  test('na conta de outra pessoa, funções abertas e o Salvar manda group_ids', async () => {
    const user = userEvent.setup();
    renderPage();
    const dialog = await editar(user, 0);

    await vi.waitFor(() => expect(funcoesDoForm(dialog)).toBeEnabled(), { timeout: 10000 });
    expect(within(dialog).queryByText('Suas funções só outro superusuário altera.')).not.toBeInTheDocument();
    await user.click(within(dialog).getByRole('button', { name: /^salvar$/i }));

    await vi.waitFor(() => expect(updateUser).toHaveBeenCalled(), { timeout: 10000 });
    expect(vi.mocked(updateUser).mock.calls[0]![1]).toMatchObject({ group_ids: [2], gerencia_id: 7 });
  }, 40000);
});
