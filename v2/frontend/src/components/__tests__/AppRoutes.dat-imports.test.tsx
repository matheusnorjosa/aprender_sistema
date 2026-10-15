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
import { ComAcesso } from '../../test/comAcesso';

// Mock api/ops para evitar fetch real durante render da ImportacoesPage
vi.mock('../../api/ops', () => ({
  importAcoes: vi.fn(),
  importBloqueios: vi.fn(),
  importCadastros: vi.fn(),
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

// O DAT em produção possui a policy pública `manage_admin_registries`, que abre as demais rotas
// /dat/*. As telas de importação não: desde 02/10/2026 (decisão do dono) só o superusuário as abre.
const DAT_POLICIES = ['manage_admin_registries'];
const SUPERUSUARIO: CurrentUser = { ...DAT_USER, groups: [], setores: [], is_superuser: true };

function renderRota(rota: string, user: CurrentUser, policies: readonly string[]): void {
  render(
    <MemoryRouter initialEntries={[rota]}>
      <ComAcesso policies={policies} superusuario={user.is_superuser}>
        <AppRoutes user={user} />
      </ComAcesso>
    </MemoryRouter>,
  );
}

describe('AppRoutes — DAT Imports redirect (PR-C)', () => {
  test('rota /dat/importacao redireciona para /dat/importacoes', async () => {
    renderRota('/dat/importacao', SUPERUSUARIO, DAT_POLICIES);

    // ImportacoesPage tem heading "DAT > Importações"
    expect(
      await screen.findByRole('heading', { level: 2, name: /DAT.*Importações/i }, { timeout: 5000 }),
    ).toBeInTheDocument();
  });

  test('rota /dat/importacoes carrega ImportacoesPage diretamente para o superusuário', async () => {
    renderRota('/dat/importacoes', SUPERUSUARIO, DAT_POLICIES);

    expect(
      await screen.findByRole('heading', { level: 2, name: /DAT.*Importações/i }, { timeout: 5000 }),
    ).toBeInTheDocument();
  });

  test.each(['/dat/importacoes', '/dat/importacao'])('rota %s mostra Forbidden para o DAT', async (rota) => {
    renderRota(rota, DAT_USER, DAT_POLICIES);

    expect(await screen.findByText(/Recurso indisponível/i)).toBeInTheDocument();
    expect(screen.queryByRole('heading', { level: 2, name: /DAT.*Importações/i })).not.toBeInTheDocument();
  });

  test('rota /dat/importacoes mostra Forbidden para não-DAT', async () => {
    const nonDatUser: CurrentUser = { ...DAT_USER, groups: ['Coordenador'], setores: ['Vidas'] };
    renderRota('/dat/importacoes', nonDatUser, []);

    expect(await screen.findByText(/Recurso indisponível/i)).toBeInTheDocument();
  });
});
