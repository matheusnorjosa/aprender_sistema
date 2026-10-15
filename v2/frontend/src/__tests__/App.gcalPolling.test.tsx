/**
 * PR 7 das permissões: a consulta periódica aos alertas do Google (badge do Dashboard GCal) liga
 * pela policy `access_controle_section`, não pelo setor do /me.
 *
 * Estratégia: mesma do App.boot-error — filhos pesados stubados; getMe e getMyPolicies controlados;
 * o hook de polling é um espião que guarda o `enabled` recebido.
 */
import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import type { CurrentUser } from '../types';

const { getMeMock, getMyPoliciesMock, pollingMock } = vi.hoisted(() => ({
  getMeMock: vi.fn(),
  getMyPoliciesMock: vi.fn(),
  pollingMock: vi.fn((_opts: { enabled: boolean }) => ({ alerts: { errors: 0, warnings: 0 } })),
}));

vi.mock('../api/availability', () => ({ getMe: getMeMock }));
vi.mock('../api/me', () => ({ getMyPolicies: getMyPoliciesMock }));
vi.mock('../api/auth', () => ({ logout: vi.fn().mockResolvedValue(undefined) }));

vi.mock('../components/AppSidebar', () => ({ AppSidebar: () => <div>SIDEBAR</div> }));
vi.mock('../components/AppHeader', () => ({ AppHeader: () => <div>HEADER</div> }));
vi.mock('../components/AppRoutes', () => ({
  AppRoutes: () => <div data-testid="app-routes">ROUTES</div>,
}));
vi.mock('../pages/Auth/LoginPage', () => ({ default: () => <div>LOGIN_PAGE</div> }));

vi.mock('../hooks/useSessionMonitor', () => ({
  default: () => ({ showWarning: false, timeLeft: 7200, sessionAge: 7200, renewSession: vi.fn() }),
}));
vi.mock('../components/SessionExpiryWarning', () => ({ default: () => null }));

vi.mock('../hooks/useGCalAlertsPolling', () => ({ useGCalAlertsPolling: pollingMock }));
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

/** `enabled` da última chamada, depois que as rotas montaram (acesso carregado). */
async function enabledDoPolling(): Promise<boolean | undefined> {
  render(<App />);
  await screen.findByTestId('app-routes');
  return pollingMock.mock.calls.at(-1)?.[0].enabled;
}

describe('App — consulta periódica ao Google pela policy (PR 7)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('com access_controle_section: liga', async () => {
    getMeMock.mockResolvedValue(usuario());
    getMyPoliciesMock.mockResolvedValue(['access_controle_section']);
    expect(await enabledDoPolling()).toBe(true);
  });

  test('setor Controle no /me, sem a policy: não liga', async () => {
    getMeMock.mockResolvedValue(usuario({ setores: ['Controle'], groups: ['Controle'] }));
    getMyPoliciesMock.mockResolvedValue([]);
    expect(await enabledDoPolling()).toBe(false);
  });
});
