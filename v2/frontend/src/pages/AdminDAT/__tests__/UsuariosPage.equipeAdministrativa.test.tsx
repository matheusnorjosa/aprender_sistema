/**
 * Papel "Equipe administrativa" (EQUIPE) no formulário de Usuários (decisão do dono, 05/10/2026).
 *
 * - Não vem de função (grupo): o form tem uma caixa própria, hidratada de `equipe_administrativa`.
 * - O Salvar reenvia o valor hidratado (salvar sem mudar mantém o vínculo); só o superuser envia.
 * - Com a caixa marcada, a função deixa de ser obrigatória ao criar e a gerência passa a ser.
 * - O detalhe mostra o papel em pt-BR.
 * - A prévia de grupos espelha o backend: o grupo de setor só vem com função que tem papel no vínculo.
 */
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';

import {
  buildUsuarioPayload,
  gruposAposSalvar,
  lotacaoObrigatoria,
  type UsuarioFormValues,
} from '../usuario_form_helpers';

const { USUARIOS, GERENCIAS } = vi.hoisted(() => ({
  USUARIOS: [
    {
      id: 21, username: 'suporte.teste', email: 'suporte@example.invalid', first_name: 'Suporte', last_name: 'Teste',
      cpf_masked: '***.***.000-21', is_active: true, is_superuser: false,
      groups: [], group_ids_display: [],
      gerencia_atual: { gerencia_id: 4, rotulo: 'DAT', nome_setor: 'DAT', setor_canonico: 'DAT', papel: 'EQUIPE' },
      equipe_administrativa: true,
    },
  ],
  GERENCIAS: [
    {
      id: 4, nome: 'G DAT', nome_setor: 'DAT', nome_exibicao: 'DAT', rotulo: 'DAT',
      setor_canonico: 'DAT', setor_canonico_confianca: '', gerente: null, gerente_nome: '', ativo: true,
      descricao: '', projetos_count: 0, created_at: '', updated_at: '',
    },
  ],
}));

vi.mock('../../../api/auth', () => ({
  checkAuth: vi.fn().mockResolvedValue({ authenticated: true, user: { is_superuser: true } }),
}));
vi.mock('../../../api/ops', () => ({ importUsuarios: vi.fn() }));
vi.mock('../../../api/adminDAT', () => ({
  listUsers: vi.fn().mockResolvedValue({ results: USUARIOS, count: 1, next: null, previous: null }),
  createUser: vi.fn(),
  updateUser: vi.fn().mockResolvedValue({}),
  deleteUser: vi.fn(),
  resetUserPassword: vi.fn(),
  listGroups: vi.fn().mockResolvedValue({
    results: [{ id: 2, name: 'Formador' }], count: 1, next: null, previous: null,
  }),
  getRBACMeta: vi.fn().mockResolvedValue({
    setor_groups: ['DAT'], funcao_groups: ['Formador'], categories: [], setores_produto: [],
  }),
  listGerencias: vi.fn().mockResolvedValue({ results: GERENCIAS, count: 1, next: null, previous: null }),
}));

import { updateUser } from '../../../api/adminDAT';
import UsuariosPage from '../UsuariosPage';

function renderPage() {
  return render(
    <MemoryRouter>
      <UsuariosPage />
    </MemoryRouter>,
  );
}

const BASE: UsuarioFormValues = {
  username: 'u',
  email: 'u@example.invalid',
  is_active: true,
  is_superuser: false,
  gerencia_id: 4,
  funcao_ids: [],
};
const OPCOES = { isEditing: true, cpfEditUnlocked: false, currentIsSuperuser: true };

describe('buildUsuarioPayload — equipe administrativa', () => {
  test('superuser envia o valor da caixa, marcado ou não', () => {
    expect(buildUsuarioPayload({ ...BASE, equipe_administrativa: true }, OPCOES)).toMatchObject({
      equipe_administrativa: true,
    });
    expect(buildUsuarioPayload({ ...BASE, equipe_administrativa: false }, OPCOES)).toMatchObject({
      equipe_administrativa: false,
    });
  });

  test('sem valor hidratado ou sem ser superuser, não envia (o backend mantém como está)', () => {
    expect(buildUsuarioPayload(BASE, OPCOES)).not.toHaveProperty('equipe_administrativa');
    expect(
      buildUsuarioPayload({ ...BASE, equipe_administrativa: true }, { ...OPCOES, currentIsSuperuser: false }),
    ).not.toHaveProperty('equipe_administrativa');
  });
});

describe('lotacaoObrigatoria — equipe administrativa', () => {
  test('ao criar só com a equipe, a função não é obrigatória e a gerência é', () => {
    expect(
      lotacaoObrigatoria({ currentIsSuperuser: true, isEditing: false, temLotacao: false, equipeAdministrativa: true }),
    ).toEqual({ gerencia: true, funcao: false });
  });

  test('na edição, marcar a equipe exige a gerência mesmo sem lotação', () => {
    expect(
      lotacaoObrigatoria({ currentIsSuperuser: true, isEditing: true, temLotacao: false, equipeAdministrativa: true }),
    ).toEqual({ gerencia: true, funcao: false });
  });
});

describe('gruposAposSalvar — grupo de setor só com função que tem papel', () => {
  const grupos = [
    { id: 1, name: 'Formador' },
    { id: 4, name: 'Assistente Administrativo' },
    { id: 5, name: 'Vidas' },
  ];
  const funcoes = new Set(['Formador', 'Assistente Administrativo']);
  const vidas = { id: 2, nome: 'GERENCIA 2', setor_canonico: 'Vidas' };
  const nomes = (funcaoIds: number[]): string[] =>
    gruposAposSalvar({ grupos, idsAtuais: [], funcoes, funcaoIds, gerencia: vidas, gerenciaAnterior: undefined })
      .map((g) => g.name)
      .sort();

  test('só a equipe administrativa (sem função) não dá o grupo do setor', () => {
    expect(nomes([])).toEqual([]);
  });

  test('função sem papel no vínculo não dá o grupo do setor', () => {
    expect(nomes([4])).toEqual(['Assistente Administrativo']);
  });

  test('função com papel continua dando o grupo do setor', () => {
    expect(nomes([1])).toEqual(['Formador', 'Vidas']);
  });
});

describe('UsuariosPage — equipe administrativa', () => {
  beforeEach(() => vi.clearAllMocks());

  test('o formulário mostra a caixa marcada e salvar sem mudar reenvia o papel', async () => {
    const user = userEvent.setup();
    renderPage();
    const editBtns = await screen.findAllByRole('button', { name: /editar/i }, { timeout: 15000 });
    await user.click(editBtns[0]!);
    const dialog = await screen.findByRole('dialog', {}, { timeout: 10000 });

    const caixa = within(dialog).getByRole('checkbox', { name: /equipe administrativa/i });
    expect(caixa).toBeChecked();

    await user.click(within(dialog).getByRole('button', { name: /^salvar$/i }));

    await vi.waitFor(() => expect(updateUser).toHaveBeenCalled(), { timeout: 10000 });
    expect(vi.mocked(updateUser).mock.calls[0]![1]).toMatchObject({ equipe_administrativa: true, gerencia_id: 4 });
  }, 40000);

  test('desmarcar a caixa envia o papel desligado', async () => {
    const user = userEvent.setup();
    renderPage();
    const editBtns = await screen.findAllByRole('button', { name: /editar/i }, { timeout: 15000 });
    await user.click(editBtns[0]!);
    const dialog = await screen.findByRole('dialog', {}, { timeout: 10000 });

    await user.click(within(dialog).getByRole('checkbox', { name: /equipe administrativa/i }));
    await user.click(within(dialog).getByRole('button', { name: /^salvar$/i }));

    await vi.waitFor(() => expect(updateUser).toHaveBeenCalled(), { timeout: 10000 });
    expect(vi.mocked(updateUser).mock.calls[0]![1]).toMatchObject({ equipe_administrativa: false });
  }, 40000);
});
