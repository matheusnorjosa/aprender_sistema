/**
 * Tests do redirect /dat/importacao → /dat/importacoes (PR-C DAT Imports).
 *
 * Cobre o redirect e o gate das telas de importação (só superusuário). Tests de guard em outras rotas DAT
 * permanecem responsabilidade dos arquivos próprios de cada página
 * (PR 11/12 do programa hardening RBAC fazem cobertura ampla por perfil).
 */

import { MemoryRouter } from 'react-router';
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
  gerencias: [],
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
  isGestorPorVinculo: false,
  canSeeAllSectors: false,
};

// O DAT em produção possui a policy pública `manage_admin_registries`, que abre as demais rotas
// /dat/*. As telas de importação não: desde 02/10/2026 (decisão do dono) só o superusuário as abre.
const DAT_POLICIES = ['manage_admin_registries'];
const SUPERUSUARIO: CurrentUser = { ...DAT_USER, groups: [], setores: [], is_superuser: true };
const PERMISSOES_SUPERUSUARIO: Permissions = { ...DAT_PERMISSIONS, isAdmin: true, inDAT: false };

describe('AppRoutes — DAT Imports redirect (PR-C)', () => {
  test('rota /dat/importacao redireciona para /dat/importacoes', async () => {
    render(
      <MemoryRouter initialEntries={['/dat/importacao']}>
        <AppRoutes user={SUPERUSUARIO} permissions={PERMISSOES_SUPERUSUARIO} policies={DAT_POLICIES} />
      </MemoryRouter>,
    );

    // ImportacoesPage tem heading "DAT > Importações"
    expect(
      await screen.findByRole('heading', { level: 2, name: /DAT.*Importações/i }, { timeout: 5000 }),
    ).toBeInTheDocument();
  });

  test('rota /dat/importacoes carrega ImportacoesPage diretamente para o superusuário', async () => {
    render(
      <MemoryRouter initialEntries={['/dat/importacoes']}>
        <AppRoutes user={SUPERUSUARIO} permissions={PERMISSOES_SUPERUSUARIO} policies={DAT_POLICIES} />
      </MemoryRouter>,
    );

    expect(
      await screen.findByRole('heading', { level: 2, name: /DAT.*Importações/i }, { timeout: 5000 }),
    ).toBeInTheDocument();
  });

  test.each(['/dat/importacoes', '/dat/importacao'])('rota %s mostra Forbidden para o DAT', async (rota) => {
    render(
      <MemoryRouter initialEntries={[rota]}>
        <AppRoutes user={DAT_USER} permissions={DAT_PERMISSIONS} policies={DAT_POLICIES} />
      </MemoryRouter>,
    );

    expect(await screen.findByText(/Recurso indisponível/i)).toBeInTheDocument();
    expect(screen.queryByRole('heading', { level: 2, name: /DAT.*Importações/i })).not.toBeInTheDocument();
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
