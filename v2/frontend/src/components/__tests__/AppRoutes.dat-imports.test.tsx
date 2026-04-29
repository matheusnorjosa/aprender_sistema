/**
 * Tests do redirect /dat/importacao → /dat/importacoes (PR-C DAT Imports).
 *
 * Cobre apenas o redirect. Tests de guard `canDAT` em outras rotas DAT
 * permanecem responsabilidade dos arquivos próprios de cada página
 * (PR 11/12 do programa hardening RBAC fazem cobertura ampla por perfil).
 */

import { MemoryRouter } from 'react-router-dom';
import { render, screen } from '@testing-library/react';
import { describe, expect, test, vi } from 'vitest';

import { AppRoutes } from '../AppRoutes';
import type { CurrentUser } from '../../types';
import type { Permissions } from '../../hooks/usePermissions';

// Mock api/ops para evitar fetch real durante render da ImportacoesPage
vi.mock('../../api/ops', () => ({
  importAcoes: vi.fn(),
  importBloqueios: vi.fn(),
  importCadastros: vi.fn(),
  importColecoes: vi.fn(),
  importCompras: vi.fn(),
  importDeslocamentos: vi.fn(),
  importEquipeGerencia: vi.fn(),
  importEventos: vi.fn(),
  importMunicipios: vi.fn(),
  importProdutos: vi.fn(),
  importUsuarios: vi.fn(),
}));

const DAT_USER: CurrentUser = {
  id: 1,
  username: 'dat_user',
  email: 'dat@test.com',
  first_name: 'DAT',
  last_name: 'User',
  name: 'DAT User',
  groups: ['DAT'],
  setores: ['DAT'],
  funcoes: [],
  is_superuser: false,
  is_superintendencia: false,
  can_approve_super: false,
  permissions: [],
};

const DAT_PERMISSIONS: Permissions = {
  isAdmin: false,
  isCoordenador: false,
  isFormador: false,
  isGerente: false,
  inSuperintendencia: false,
  inGerencia: false,
  inDAT: true,
  inControle: false,
  inDiretoria: false,
  canApproveSuper: false,
  canCoordenador: false,
  canControle: false,
  canDAT: true,
  canAcoesInternas: false,
  canDashboardOverview: false,
  canDashboardEquipe: false,
  canDashboardGcal: false,
  canDashboardCompras: false,
  canMapaBrasil: false,
  canDashboardsMenu: false,
  canDisponibilidade: true,
  canSeeAllSectors: false,
};

describe('AppRoutes — DAT Imports redirect (PR-C)', () => {
  test('rota /dat/importacao redireciona para /dat/importacoes', async () => {
    render(
      <MemoryRouter initialEntries={['/dat/importacao']}>
        <AppRoutes user={DAT_USER} permissions={DAT_PERMISSIONS} policies={[]} />
      </MemoryRouter>,
    );

    // ImportacoesPage tem heading "DAT > Importações"
    expect(
      await screen.findByRole('heading', { level: 2, name: /DAT.*Importações/i }, { timeout: 5000 }),
    ).toBeInTheDocument();
  });

  test('rota /dat/importacoes carrega ImportacoesPage diretamente para DAT', async () => {
    render(
      <MemoryRouter initialEntries={['/dat/importacoes']}>
        <AppRoutes user={DAT_USER} permissions={DAT_PERMISSIONS} policies={[]} />
      </MemoryRouter>,
    );

    expect(
      await screen.findByRole('heading', { level: 2, name: /DAT.*Importações/i }, { timeout: 5000 }),
    ).toBeInTheDocument();
  });

  test('rota /dat/importacoes mostra Forbidden para não-DAT', async () => {
    const nonDatPerms: Permissions = { ...DAT_PERMISSIONS, canDAT: false, inDAT: false };
    const nonDatUser: CurrentUser = { ...DAT_USER, groups: ['Coordenador'], setores: ['Vidas'] };
    render(
      <MemoryRouter initialEntries={['/dat/importacoes']}>
        <AppRoutes user={nonDatUser} permissions={nonDatPerms} policies={[]} />
      </MemoryRouter>,
    );

    expect(await screen.findByText(/Recurso indisponível/i)).toBeInTheDocument();
  });
});
