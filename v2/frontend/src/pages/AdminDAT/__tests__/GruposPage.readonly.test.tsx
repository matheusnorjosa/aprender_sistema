/**
 * P0-1 Tier-0 (D-1=2a): GruposPage é READ-ONLY para não-superuser.
 *
 * Toda escrita da GruposPage (criar/editar/excluir grupo, matriz de permissões
 * funcionais, sync de membros) vira superuser-only. O co-deploy exige que a UI
 * pare de OFERECER escrita antes de o backend (PR-B) passar a rejeitar — senão
 * um DAT clica em Salvar e leva 403 (+ risco de escrita parcial: grupo criado,
 * membros barrados).
 *
 * C2 (Programa C): sem ações, a coluna Ações sai da tabela e o aviso "Somente
 * superusuário" aparece uma vez, acima dela (antes repetia em cada linha e tomava largura).
 */

import { describe, expect, test, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';

vi.mock('../../../api/auth', () => ({ checkAuth: vi.fn() }));
vi.mock('../../../api/adminDAT', () => ({
  listGroups: vi.fn().mockResolvedValue({
    results: [{ id: 1, name: 'DAT', group_type: 'setor', user_count: 2, permissoes_funcionais: [] }],
  }),
  listUsers: vi.fn().mockResolvedValue({ results: [] }),
  listPermissoesFuncionais: vi.fn().mockResolvedValue({ results: [] }),
  getRBACMeta: vi.fn().mockResolvedValue({ setor_groups: ['DAT'], funcao_groups: [], categories: [] }),
  getGroup: vi.fn(),
  createGroup: vi.fn(),
  updateGroup: vi.fn(),
  deleteGroup: vi.fn(),
  syncGroupMembers: vi.fn(),
}));

import GruposPage from '../GruposPage';
import { checkAuth } from '../../../api/auth';

function renderPage(): void {
  render(
    <MemoryRouter>
      <GruposPage />
    </MemoryRouter>,
  );
}

describe('GruposPage — read-only para não-superuser (P0-1 Tier-0)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('não-superuser: sem "Novo Grupo" nem ações; o aviso "Somente superusuário" aparece uma vez', async () => {
    vi.mocked(checkAuth).mockResolvedValue({ user: { is_superuser: false } } as never);
    renderPage();

    await waitFor(() => expect(screen.getByText(/Grupos RBAC/)).toBeInTheDocument());
    await screen.findByText('DAT', {}, { timeout: 10000 });
    await waitFor(() => expect(screen.getAllByText(/Somente superusuário/)).toHaveLength(1));

    expect(screen.queryByRole('button', { name: /Novo Grupo/ })).toBeNull();
    expect(screen.queryByRole('button', { name: /^(Editar|Excluir|Mais ações)/ })).toBeNull();
    expect(screen.queryByRole('columnheader', { name: 'Ações' })).toBeNull();
  }, 20000);

  test('superuser: botão "Novo Grupo" e ações Editar/Excluir presentes', async () => {
    vi.mocked(checkAuth).mockResolvedValue({ user: { is_superuser: true } } as never);
    renderPage();

    await screen.findByRole('button', { name: /Novo Grupo/ }, { timeout: 10000 });
    await screen.findByRole('button', { name: 'Editar: DAT' }, { timeout: 10000 });

    expect(screen.queryByText(/Somente superusuário/)).toBeNull();
  }, 20000);
});
