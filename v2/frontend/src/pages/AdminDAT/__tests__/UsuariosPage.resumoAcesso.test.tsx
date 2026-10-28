/**
 * Resumo do perfil de acesso (ensaio r3, 28/10/2026): para um Formador, o form dizia "Permissões
 * efetivas: sem permissões específicas definidas", que não diz o que a pessoa pode fazer. Agora o
 * resumo mostra o que ela vê no menu hoje, pelas policies dela no servidor
 * (`GET /usuarios-admin/{id}/policies/`, a mesma regra de `/me/policies/` que monta o menu).
 * Só o básico vira uma frase simples.
 */
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { beforeEach, describe, expect, test, vi } from 'vitest';

vi.setConfig({ testTimeout: 30_000 });

const { USUARIOS } = vi.hoisted(() => ({
  USUARIOS: [
    {
      id: 7, username: 'formador.teste', email: 'formador@example.invalid', first_name: 'Form', last_name: 'Teste',
      cpf_masked: '***.***.000-00', is_active: true, is_superuser: false,
      groups: ['Formador'], group_ids_display: [2], gerencia_atual: null,
    },
  ],
}));

vi.mock('../../../api/auth', () => ({
  checkAuth: vi.fn().mockResolvedValue({ authenticated: true, user: { is_superuser: true } }),
}));
vi.mock('../../../api/ops', () => ({ importUsuarios: vi.fn() }));
vi.mock('../../../api/adminDAT', () => ({
  listUsers: vi.fn().mockResolvedValue({ results: USUARIOS, count: 1, next: null, previous: null }),
  getUserPolicies: vi.fn(),
  createUser: vi.fn(),
  updateUser: vi.fn(),
  deleteUser: vi.fn(),
  resetUserPassword: vi.fn(),
  listGroups: vi.fn().mockResolvedValue({
    results: [{ id: 2, name: 'Formador' }], count: 1, next: null, previous: null,
  }),
  getRBACMeta: vi.fn().mockResolvedValue({
    setor_groups: [], funcao_groups: ['Formador'], categories: [], setores_produto: [],
  }),
  listGerencias: vi.fn().mockResolvedValue({ results: [], count: 0, next: null, previous: null }),
}));

import { getUserPolicies } from '../../../api/adminDAT';
import UsuariosPage from '../UsuariosPage';
import { resumoDoMenu } from '../usuario_form_helpers';

async function abrirResumo(): Promise<HTMLElement> {
  const user = userEvent.setup();
  render(
    <MemoryRouter>
      <UsuariosPage />
    </MemoryRouter>,
  );
  await user.click(await screen.findByRole('button', { name: 'Editar: Form Teste' }, { timeout: 15000 }));
  const dialog = await screen.findByRole('dialog', {}, { timeout: 10000 });
  const titulo = within(dialog).getByText('Resumo do perfil de acesso');
  const card = titulo.closest<HTMLElement>('.ant-card');
  if (!card) throw new Error('o resumo não está num card');
  return card;
}

describe('resumoDoMenu', () => {
  test('só Meus Eventos: frase simples', () => {
    expect(resumoDoMenu([])).toEqual({ itens: ['Meus Eventos'], frase: 'Vê só os próprios eventos.' });
  });

  test('Meus Eventos e Bloqueios: frase simples', () => {
    expect(resumoDoMenu(['access_availability_blocks'])).toEqual({
      itens: ['Meus Eventos', 'Bloqueios'],
      frase: 'Vê os próprios eventos e registra bloqueios.',
    });
  });

  test('mais que o básico: os itens do menu, na ordem do menu, sem frase', () => {
    expect(
      resumoDoMenu([
        'publish_setor_solicitacao',
        'create_solicitation',
        'access_monthly_availability',
        'access_availability_blocks',
        'view_team_dashboard',
        'view_map_metrics',
      ]),
    ).toEqual({
      itens: ['Meus Eventos', 'Bloqueios', 'Dashboards', 'Grade Mensal', 'Solicitações', 'Publicar na agenda'],
      frase: null,
    });
  });
});

describe('UsuariosPage — resumo do perfil de acesso', () => {
  beforeEach(() => vi.clearAllMocks());

  test('Formador só com o básico: diz em linguagem simples o que ele faz', async () => {
    vi.mocked(getUserPolicies).mockResolvedValue(['access_availability_blocks']);
    const card = await abrirResumo();

    expect(await within(card).findByText('Vê os próprios eventos e registra bloqueios.')).toBeInTheDocument();
    expect(getUserPolicies).toHaveBeenCalledWith(7);
    expect(within(card).queryByText(/sem permissões específicas/)).not.toBeInTheDocument();
  });

  test('com mais que o básico: lista o que vê no menu', async () => {
    vi.mocked(getUserPolicies).mockResolvedValue(['access_availability_blocks', 'access_monthly_availability']);
    const card = await abrirResumo();

    expect(await within(card).findByText('Grade Mensal')).toBeInTheDocument();
    expect(within(card).getByText('Bloqueios')).toBeInTheDocument();
    expect(within(card).getByText('Meus Eventos')).toBeInTheDocument();
  });

  test('falha ao carregar: diz que não deu, sem inventar o que ela vê', async () => {
    vi.mocked(getUserPolicies).mockRejectedValue(new Error('falhou'));
    const card = await abrirResumo();

    await waitFor(() =>
      expect(within(card).getByText('Não foi possível carregar agora. Feche e abra de novo para tentar.')).toBeInTheDocument(),
    );
    expect(within(card).queryByText('Meus Eventos')).not.toBeInTheDocument();
  });
});
