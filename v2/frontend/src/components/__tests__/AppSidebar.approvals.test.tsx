/**
 * AppSidebar — visibilidade do item "Aprovações" por perfil.
 *
 * PR 10 hardening RBAC (2026-04-30): a fonte exclusiva de autorização para
 * Aprovações no frontend é a policy pública `access_solicitation_approvals`
 * (Gerente da Superintendência OU Assistente Administrativo do Controle).
 * Legacy `can_approve_super` deixou de ser consultado.
 *
 * Cada cenário monta `permissions` e `policies` espelhando o que
 * `usePermissions(user)` + `GET /api/me/policies/` retornariam para o ator.
 */

import { MemoryRouter } from 'react-router-dom';
import { render, screen } from '@testing-library/react';
import { describe, expect, test } from 'vitest';

import { AppSidebar } from '../AppSidebar';
import type { Permissions } from '../../hooks/usePermissions';

const COLORS = { sidebarBackground: '#001529', borderLight: '#303030' };

const SIDEBAR_PROPS = {
  gcalErrorCount: 0,
  unreadNotifications: 0,
  isMobile: false,
  sidebarCollapsed: false,
  toggleSidebar: () => {},
  colors: COLORS,
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

function renderSidebar(permissions: Permissions, policies: readonly string[]): void {
  render(
    <MemoryRouter>
      <AppSidebar permissions={permissions} policies={policies} {...SIDEBAR_PROPS} />
    </MemoryRouter>,
  );
}

describe('AppSidebar — item "Aprovações" depende exclusivamente de access_solicitation_approvals', () => {
  test('Gerente da Superintendência (policy presente) → mostra Aprovações', () => {
    renderSidebar(
      { ...EMPTY_PERMISSIONS, isGerente: true, inSuperintendencia: true, canSeeAllSectors: true },
      ['access_solicitation_approvals'],
    );
    expect(screen.getByRole('link', { name: /Aprovações/i })).toBeInTheDocument();
  });

  test('Assistente Administrativo do Controle (policy presente) → mostra Aprovações', () => {
    renderSidebar(
      { ...EMPTY_PERMISSIONS, inControle: true, canControle: true },
      ['access_solicitation_approvals'],
    );
    expect(screen.getByRole('link', { name: /Aprovações/i })).toBeInTheDocument();
  });

  test('Controle puro (sem policy) → NÃO mostra Aprovações', () => {
    renderSidebar(
      { ...EMPTY_PERMISSIONS, inControle: true, canControle: true },
      [],
    );
    expect(screen.queryByRole('link', { name: /Aprovações/i })).not.toBeInTheDocument();
  });

  test('DAT (sem policy) → NÃO mostra Aprovações', () => {
    renderSidebar(
      { ...EMPTY_PERMISSIONS, inDAT: true, canDAT: true, canCoordenador: true },
      [],
    );
    expect(screen.queryByRole('link', { name: /Aprovações/i })).not.toBeInTheDocument();
  });

  test('Gerente pedagógico (Vidas/Fluir, sem policy) → NÃO mostra Aprovações', () => {
    renderSidebar(
      { ...EMPTY_PERMISSIONS, isGerente: true, inGerencia: true },
      [],
    );
    expect(screen.queryByRole('link', { name: /Aprovações/i })).not.toBeInTheDocument();
  });

  test('Coordenador → NÃO mostra Aprovações', () => {
    renderSidebar(
      { ...EMPTY_PERMISSIONS, isCoordenador: true, canCoordenador: true },
      [],
    );
    expect(screen.queryByRole('link', { name: /Aprovações/i })).not.toBeInTheDocument();
  });

  test('Apoio de Coordenação → NÃO mostra Aprovações', () => {
    renderSidebar(
      // Apoio é tratado como isCoordenador no usePermissions.
      { ...EMPTY_PERMISSIONS, isCoordenador: true, canCoordenador: true },
      [],
    );
    expect(screen.queryByRole('link', { name: /Aprovações/i })).not.toBeInTheDocument();
  });

  test('Formador → NÃO mostra Aprovações', () => {
    renderSidebar(
      { ...EMPTY_PERMISSIONS, isFormador: true },
      [],
    );
    expect(screen.queryByRole('link', { name: /Aprovações/i })).not.toBeInTheDocument();
  });

  test('Diretoria → NÃO mostra Aprovações', () => {
    renderSidebar(
      { ...EMPTY_PERMISSIONS, inDiretoria: true, canDashboardOverview: true, canDashboardsMenu: true },
      ['view_overview_dashboard', 'view_compras_dashboard', 'view_map_metrics'],
    );
    expect(screen.queryByRole('link', { name: /Aprovações/i })).not.toBeInTheDocument();
  });

  test('legacy canApproveSuper=true em Permissions → NÃO basta sem a policy', () => {
    // Garante que o frontend não consulta mais `permissions.canApproveSuper`.
    // Mesmo com a flag legacy true, sem a policy o item não renderiza.
    renderSidebar(
      { ...EMPTY_PERMISSIONS, canApproveSuper: true, inSuperintendencia: true, isGerente: true, canSeeAllSectors: true },
      [], // policy ausente
    );
    expect(screen.queryByRole('link', { name: /Aprovações/i })).not.toBeInTheDocument();
  });
});
