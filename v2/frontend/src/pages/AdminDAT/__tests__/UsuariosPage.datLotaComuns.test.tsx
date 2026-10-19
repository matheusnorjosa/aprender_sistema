/**
 * O DAT lota nas gerências comuns (decisão do dono de 17/10/2026).
 *
 * - Quem tem a policy `manage_lotacao_comum` (o DAT) edita Gerência, Função e Equipe administrativa.
 * - A lista de gerências esconde do DAT as reservadas (`lotacao_reservada`: DAT, Controle, Diretoria).
 * - Conta com vínculo reservado (`lotacao_reservada` do usuário) e a própria conta: campos travados com o
 *   motivo, e o Salvar não envia a lotação.
 * - Sem a policy, nada muda: campos travados e lotação fora do payload.
 */
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';

import { ComAcesso } from '../../../test/comAcesso';
import {
  buildUsuarioPayload,
  lotacaoObrigatoria,
  motivoDaLotacaoTravada,
  type UsuarioFormValues,
} from '../usuario_form_helpers';

const { USUARIOS, GERENCIAS } = vi.hoisted(() => {
  const gerencia = (id: number, nome: string, rotulo: string, reservada: boolean) => ({
    id, nome, nome_setor: rotulo, nome_exibicao: rotulo, rotulo, setor_canonico: rotulo,
    setor_canonico_confianca: '', gerente: null, gerente_nome: '', ativo: true, descricao: '',
    projetos_count: 0, created_at: '', updated_at: '', lotacao_reservada: reservada,
  });
  const usuario = (id: number, nome: string, extra: Record<string, unknown>) => ({
    id, username: `teste.${id}`, email: `teste.${id}@example.invalid`, first_name: nome, last_name: 'Teste',
    cpf_masked: `***.***.000-${id}`, is_active: true, is_superuser: false, groups: [], group_ids_display: [],
    gerencia_atual: null, equipe_administrativa: false, lotacao_reservada: false, ...extra,
  });
  return {
    GERENCIAS: [gerencia(7, 'GERENCIA VIDAS', 'Vidas', false), gerencia(4, 'GERENCIA DAT', 'DAT', true)],
    USUARIOS: [
      usuario(31, 'Comum', {
        groups: ['Formador'], group_ids_display: [2],
        gerencia_atual: { gerencia_id: 7, rotulo: 'Vidas', nome_setor: 'Vidas', setor_canonico: 'Vidas', papel: 'FORMADOR' },
      }),
      usuario(32, 'Reservada', {
        gerencia_atual: { gerencia_id: 4, rotulo: 'DAT', nome_setor: 'DAT', setor_canonico: 'DAT', papel: 'EQUIPE' },
        equipe_administrativa: true, lotacao_reservada: true,
      }),
      usuario(99, 'Propria', {}),
    ],
  };
});

vi.mock('../../../api/auth', () => ({
  checkAuth: vi.fn().mockResolvedValue({ authenticated: true, user: { id: 99, is_superuser: false } }),
}));
vi.mock('../../../api/ops', () => ({ importUsuarios: vi.fn() }));
vi.mock('../../../api/adminDAT', () => ({
  listUsers: vi.fn().mockResolvedValue({ results: USUARIOS, count: 3, next: null, previous: null }),
  createUser: vi.fn().mockResolvedValue({}),
  updateUser: vi.fn().mockResolvedValue({}),
  deleteUser: vi.fn(),
  resetUserPassword: vi.fn(),
  listGroups: vi.fn().mockResolvedValue({
    results: [{ id: 2, name: 'Formador' }], count: 1, next: null, previous: null,
  }),
  getRBACMeta: vi.fn().mockResolvedValue({
    setor_groups: ['DAT', 'Vidas'], funcao_groups: ['Formador'], categories: [], setores_produto: [],
  }),
  listGerencias: vi.fn().mockResolvedValue({ results: GERENCIAS, count: 2, next: null, previous: null }),
}));

import { updateUser } from '../../../api/adminDAT';
import UsuariosPage from '../UsuariosPage';

function renderPage(policies: readonly string[] = ['manage_admin_registries', 'manage_lotacao_comum']) {
  return render(
    <ComAcesso policies={policies}>
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

const gerenciaDoForm = (dialog: HTMLElement): HTMLElement =>
  within(dialog).getByRole('combobox', { name: /gerência \(onde trabalha\)/i });

const BASE: UsuarioFormValues = {
  username: 'u',
  email: 'u@example.invalid',
  is_active: true,
  is_superuser: false,
  gerencia_id: 7,
  funcao_ids: [2],
  equipe_administrativa: false,
};

describe('buildUsuarioPayload — o DAT lota nas comuns', () => {
  test('com lotaComum envia funções, gerência e equipe, mas não is_superuser', () => {
    const payload = buildUsuarioPayload(BASE, {
      isEditing: true, cpfEditUnlocked: false, currentIsSuperuser: false, lotaComum: true,
    });
    expect(payload).toMatchObject({ group_ids: [2], gerencia_id: 7, equipe_administrativa: false });
    expect(payload).not.toHaveProperty('is_superuser');
  });

  test('sem lotaComum o DAT segue sem enviar a lotação', () => {
    const payload = buildUsuarioPayload(BASE, { isEditing: true, cpfEditUnlocked: false, currentIsSuperuser: false });
    expect(payload).not.toHaveProperty('group_ids');
    expect(payload).not.toHaveProperty('gerencia_id');
    expect(payload).not.toHaveProperty('equipe_administrativa');
  });
});

describe('lotacaoObrigatoria — o DAT lota nas comuns', () => {
  test('ao criar, o DAT que lota preenche gerência e função como o superusuário', () => {
    expect(
      lotacaoObrigatoria({ currentIsSuperuser: false, lotaComum: true, isEditing: false, temLotacao: false }),
    ).toEqual({ gerencia: true, funcao: true });
  });
});

describe('motivoDaLotacaoTravada', () => {
  const dat = { currentIsSuperuser: false, podeLotarComum: true, propria: false, reservada: false };

  test('conta comum: o DAT edita', () => {
    expect(motivoDaLotacaoTravada(dat)).toBeNull();
  });

  test('a própria conta e a conta reservada travam com o motivo', () => {
    expect(motivoDaLotacaoTravada({ ...dat, propria: true })).toMatch(/sua própria lotação/i);
    expect(motivoDaLotacaoTravada({ ...dat, reservada: true })).toMatch(/a lotação dela só o superusuário altera/i);
  });

  test('superusuário e quem não tem a policy não recebem motivo', () => {
    expect(motivoDaLotacaoTravada({ ...dat, currentIsSuperuser: true, reservada: true })).toBeNull();
    expect(motivoDaLotacaoTravada({ ...dat, podeLotarComum: false, reservada: true })).toBeNull();
  });
});

describe('UsuariosPage — o DAT lota nas gerências comuns', () => {
  beforeEach(() => vi.clearAllMocks());

  test('conta comum: os campos abrem e o Salvar envia a lotação', async () => {
    const user = userEvent.setup();
    renderPage();
    const dialog = await editar(user, 0);

    await vi.waitFor(() => expect(gerenciaDoForm(dialog)).toBeEnabled(), { timeout: 10000 });
    await user.click(within(dialog).getByRole('button', { name: /^salvar$/i }));

    await vi.waitFor(() => expect(updateUser).toHaveBeenCalled(), { timeout: 10000 });
    expect(vi.mocked(updateUser).mock.calls[0]![1]).toMatchObject({ gerencia_id: 7, group_ids: [2] });
  }, 40000);

  test('a lista de gerências esconde as reservadas', async () => {
    const user = userEvent.setup();
    renderPage();
    const dialog = await editar(user, 0);

    await vi.waitFor(() => expect(gerenciaDoForm(dialog)).toBeEnabled(), { timeout: 10000 });
    await user.click(gerenciaDoForm(dialog));
    const opcao = (titulo: string): Element | null =>
      document.querySelector(`.ant-select-item-option[title="${titulo}"]`);
    await vi.waitFor(() => expect(opcao('Vidas')).not.toBeNull(), { timeout: 10000 });
    expect(opcao('DAT')).toBeNull();
  }, 40000);

  test('conta com vínculo reservado: campos travados, o motivo e o Salvar sem a lotação', async () => {
    const user = userEvent.setup();
    renderPage();
    const dialog = await editar(user, 1);

    expect(await within(dialog).findByText(/a lotação dela só o superusuário altera/i)).toBeInTheDocument();
    expect(gerenciaDoForm(dialog)).toBeDisabled();
    await user.click(within(dialog).getByRole('button', { name: /^salvar$/i }));

    await vi.waitFor(() => expect(updateUser).toHaveBeenCalled(), { timeout: 10000 });
    const payload = vi.mocked(updateUser).mock.calls[0]![1];
    expect(payload).not.toHaveProperty('gerencia_id');
    expect(payload).not.toHaveProperty('group_ids');
  }, 40000);

  test('a própria conta: campos travados com o motivo', async () => {
    const user = userEvent.setup();
    renderPage();
    const dialog = await editar(user, 2);

    expect(await within(dialog).findByText(/sua própria lotação só o superusuário altera/i)).toBeInTheDocument();
    expect(gerenciaDoForm(dialog)).toBeDisabled();
  }, 40000);

  test('sem a policy, os campos seguem travados', async () => {
    const user = userEvent.setup();
    renderPage(['manage_admin_registries']);
    const dialog = await editar(user, 0);

    expect((await within(dialog).findAllByText('Vidas', {}, { timeout: 10000 })).length).toBeGreaterThan(0);
    expect(gerenciaDoForm(dialog)).toBeDisabled();
    expect(within(dialog).queryByText(/só o superusuário altera/i)).not.toBeInTheDocument();
  }, 40000);
});
