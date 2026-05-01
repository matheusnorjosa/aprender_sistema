/**
 * AppRoutes — gate da rota /solicitacoes/aprovacoes.
 *
 * PR 10 hardening RBAC (2026-04-30): a rota Aprovações depende exclusivamente
 * da policy pública `access_solicitation_approvals`. Sem a policy, o
 * componente <Forbidden /> é renderizado — mesmo que o user tenha legacy
 * `can_approve_super=true` ou pertença a Superintendência/Controle por
 * setor sem a Função correta.
 */

import { MemoryRouter } from 'react-router-dom';
import { render, screen } from '@testing-library/react';
import { describe, expect, test, vi } from 'vitest';

import { AppRoutes } from '../AppRoutes';
import type { CurrentUser } from '../../types';
import type { Permissions } from '../../hooks/usePermissions';

// ApprovalsPage faz fetch de policies/solicitações dentro do effect; mockamos
// as APIs envolvidas para evitar 404 / fetch real durante o render do teste.
vi.mock('../../api/solicitacoes', () => ({
  listSolicitacoes: vi.fn().mockResolvedValue({ results: [], count: 0 }),
  approveSolicitacao: vi.fn(),
  rejectSolicitacao: vi.fn(),
  previewSolicitacao: vi.fn(),
  approveSolicitacoesBatch: vi.fn(),
  rejectSolicitacoesBatch: vi.fn(),
}));
vi.mock('../../api/me', () => ({
  getMyPolicies: vi.fn().mockResolvedValue([]),
}));

const BASE_USER: CurrentUser = {
  id: 1,
  username: 'tester',
  email: 'tester@test.com',
  first_name: 'Test',
  last_name: 'User',
  name: 'Test User',
  groups: [],
  setores: [],
  funcoes: [],
  is_superuser: false,
  is_superintendencia: false,
  can_approve_super: false,
  permissions: [],
};

const EMPTY_PERMISSIONS: Permissions = {
  isAdmin: false,
  isCoordenador: false,
  isFormador: false,
  isGerente: false,
  inSuperintendencia: false,
  inGerencia: false,
  inDAT: false,
  inControle: false,
  inDiretoria: false,
  canApproveSuper: false,
  canCoordenador: false,
  canControle: false,
  canDAT: false,
  canAcoesInternas: false,
  canDashboardOverview: false,
  canDashboardEquipe: false,
  canDashboardGcal: false,
  canDashboardCompras: false,
  canMapaBrasil: false,
  canDashboardsMenu: false,
  canDisponibilidade: false,
  canSeeAllSectors: false,
};

describe('AppRoutes — /solicitacoes/aprovacoes depende de access_solicitation_approvals', () => {
  test('user com a policy → renderiza ApprovalsPage', async () => {
    render(
      <MemoryRouter initialEntries={['/solicitacoes/aprovacoes']}>
        <AppRoutes
          user={BASE_USER}
          permissions={{ ...EMPTY_PERMISSIONS, isGerente: true, inSuperintendencia: true }}
          policies={['access_solicitation_approvals']}
        />
      </MemoryRouter>,
    );

    expect(
      await screen.findByRole('heading', { level: 2, name: /Aprovações/i }, { timeout: 5000 }),
    ).toBeInTheDocument();
  });

  test('user sem a policy → Forbidden mesmo com legacy canApproveSuper=true', async () => {
    render(
      <MemoryRouter initialEntries={['/solicitacoes/aprovacoes']}>
        <AppRoutes
          user={{ ...BASE_USER, can_approve_super: true }}
          permissions={{
            ...EMPTY_PERMISSIONS,
            canApproveSuper: true,
            inSuperintendencia: true,
            isGerente: true,
          }}
          policies={[]}
        />
      </MemoryRouter>,
    );

    expect(await screen.findByText(/Recurso indisponível/i)).toBeInTheDocument();
  });

  test('Controle puro sem a policy → Forbidden', async () => {
    render(
      <MemoryRouter initialEntries={['/solicitacoes/aprovacoes']}>
        <AppRoutes
          user={{ ...BASE_USER, groups: ['Controle'], setores: ['Controle'] }}
          permissions={{ ...EMPTY_PERMISSIONS, inControle: true, canControle: true }}
          policies={[]}
        />
      </MemoryRouter>,
    );

    expect(await screen.findByText(/Recurso indisponível/i)).toBeInTheDocument();
  });

  test('DAT sem a policy → Forbidden', async () => {
    render(
      <MemoryRouter initialEntries={['/solicitacoes/aprovacoes']}>
        <AppRoutes
          user={{ ...BASE_USER, groups: ['DAT'], setores: ['DAT'] }}
          permissions={{ ...EMPTY_PERMISSIONS, inDAT: true, canDAT: true, canCoordenador: true }}
          policies={[]}
        />
      </MemoryRouter>,
    );

    expect(await screen.findByText(/Recurso indisponível/i)).toBeInTheDocument();
  });

  test('Gerente pedagógico (Vidas) sem a policy → Forbidden', async () => {
    render(
      <MemoryRouter initialEntries={['/solicitacoes/aprovacoes']}>
        <AppRoutes
          user={{ ...BASE_USER, groups: ['Gerente', 'Vidas'], setores: ['Vidas'], funcoes: ['Gerente'] }}
          permissions={{ ...EMPTY_PERMISSIONS, isGerente: true, inGerencia: true }}
          policies={[]}
        />
      </MemoryRouter>,
    );

    expect(await screen.findByText(/Recurso indisponível/i)).toBeInTheDocument();
  });
});
