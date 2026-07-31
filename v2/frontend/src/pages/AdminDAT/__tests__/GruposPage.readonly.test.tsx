/**
 * P0-1 Tier-0 (D-1=2a): GruposPage é READ-ONLY para não-superuser.
 *
 * Toda escrita da GruposPage (criar/editar/excluir grupo, matriz de permissões
 * funcionais, sync de membros) vira superuser-only. O co-deploy exige que a UI
 * pare de OFERECER escrita antes de o backend (PR-B) passar a rejeitar — senão
 * um DAT clica em Salvar e leva 403 (+ risco de escrita parcial: grupo criado,
 * membros barrados).
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

  test('não-superuser: sem botão "Novo Grupo" e ações = "Somente superusuário"', async () => {
    vi.mocked(checkAuth).mockResolvedValue({ user: { is_superuser: false } } as never);
    renderPage();

    await waitFor(() => expect(screen.getByText(/Grupos RBAC/)).toBeInTheDocument());
    await waitFor(() => expect(screen.getByText('Somente superusuário')).toBeInTheDocument());

    expect(screen.queryByText('Novo Grupo')).toBeNull();
    expect(screen.queryByText('Editar')).toBeNull();
    expect(screen.queryByText('Excluir')).toBeNull();
  });

  test('superuser: botão "Novo Grupo" e ações Editar/Excluir presentes', async () => {
    vi.mocked(checkAuth).mockResolvedValue({ user: { is_superuser: true } } as never);
    renderPage();

    await waitFor(() => expect(screen.getByText('Novo Grupo')).toBeInTheDocument());
    await waitFor(() => expect(screen.getByText('Editar')).toBeInTheDocument());

    expect(screen.queryByText('Somente superusuário')).toBeNull();
  });
});
