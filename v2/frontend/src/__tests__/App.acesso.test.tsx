/**
 * PR 7 das permissões: o App monta o AcessoContext com o que carrega de /me e /me/policies.
 * Os testes de menu, rotas e páginas montam o contexto à mão (ComAcesso); este prova a ligação
 * App → contexto, inclusive `ehSuperusuario` (Importações, bloco Administração, Informações Técnicas).
 *
 * Estratégia: mesma do App.gcalPolling — filhos pesados stubados; AppRoutes vira um leitor de useAcesso().
 */
import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { useAcesso } from '../contexts/AcessoContext';
import type { CurrentUser } from '../types';

const { getMeMock, getMyPoliciesMock } = vi.hoisted(() => ({
  getMeMock: vi.fn(),
  getMyPoliciesMock: vi.fn(),
}));

vi.mock('../api/availability', () => ({ getMe: getMeMock }));
vi.mock('../api/me', () => ({ getMyPolicies: getMyPoliciesMock }));
vi.mock('../api/auth', () => ({ logout: vi.fn().mockResolvedValue(undefined) }));

vi.mock('../components/AppSidebar', () => ({ AppSidebar: () => <div>SIDEBAR</div> }));
vi.mock('../components/AppHeader', () => ({ AppHeader: () => <div>HEADER</div> }));
vi.mock('../components/AppRoutes', () => ({
  AppRoutes: function LeitorDeAcesso() {
    const { caps, ehSuperusuario } = useAcesso();
    return (
      <div data-testid="app-routes">
        {`superusuario=${String(ehSuperusuario)} travel=${String(caps.canAccessTravel)}`}
      </div>
    );
  },
}));
vi.mock('../pages/Auth/LoginPage', () => ({ default: () => <div>LOGIN_PAGE</div> }));

vi.mock('../hooks/useSessionMonitor', () => ({
  default: () => ({ showWarning: false, timeLeft: 7200, sessionAge: 7200, renewSession: vi.fn() }),
}));
vi.mock('../components/SessionExpiryWarning', () => ({ default: () => null }));

vi.mock('../hooks/useGCalAlertsPolling', () => ({
  useGCalAlertsPolling: () => ({ alerts: { errors: 0, warnings: 0 } }),
}));
vi.mock('../hooks/useUnreadNotificationsPolling', () => ({
  useUnreadNotificationsPolling: () => ({ unreadNotifications: 0 }),
}));
vi.mock('../services/preloadSearchData', () => ({
  preloadSearchData: vi.fn().mockResolvedValue(undefined),
}));

import App from '../App';

function usuario(overrides: Partial<CurrentUser> = {}): CurrentUser {
  return {
    id: 7,
    username: 'pessoa',
    email: 'pessoa@example.invalid',
    first_name: 'Pessoa',
    last_name: 'Teste',
    name: 'Pessoa Teste',
    groups: [],
    setores: [],
    funcoes: [],
    gerencias: [],
    is_superuser: false,
    is_superintendencia: false,
    can_approve_super: false,
    permissions: [],
    ...overrides,
  };
}

async function acessoNoContexto(): Promise<string | null> {
  render(<App />);
  return (await screen.findByTestId('app-routes')).textContent;
}

describe('App → AcessoContext (PR 7)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('superusuário do /me chega ao contexto como ehSuperusuario', async () => {
    getMeMock.mockResolvedValue(usuario({ is_superuser: true }));
    getMyPoliciesMock.mockResolvedValue(['access_travel']);
    expect(await acessoNoContexto()).toBe('superusuario=true travel=true');
  });

  test('pessoa comum: só as policies, sem ehSuperusuario', async () => {
    getMeMock.mockResolvedValue(usuario());
    getMyPoliciesMock.mockResolvedValue([]);
    expect(await acessoNoContexto()).toBe('superusuario=false travel=false');
  });
});
