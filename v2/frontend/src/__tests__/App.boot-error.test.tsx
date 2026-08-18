/**
 * #1741 (F2): no boot, `loadUser` (App.tsx) deslogava a sessão em QUALQUER erro —
 * `setUser(null)` rodava incondicionalmente no catch, então um 500/blip de rede na
 * primeira chamada `getMe()` jogava um usuário com cookie válido para a tela de login.
 *
 * Comportamento esperado: só 401/403 mandam para o login; um erro transitório mostra
 * uma tela de erro com "Tentar novamente" (sem deslogar), e o retry recupera a sessão.
 *
 * Estratégia: mesma do App.session-expiry — filhos pesados stubados; getMe controlado.
 */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, test, expect, vi, beforeEach } from 'vitest';
import type { CurrentUser } from '../types';

const getMeMock = vi.hoisted(() => vi.fn());

vi.mock('../api/availability', () => ({ getMe: getMeMock }));
vi.mock('../api/me', () => ({ getMyPolicies: vi.fn().mockResolvedValue([]) }));
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

const fakeUser: CurrentUser = {
  id: 1,
  username: 'super',
  email: 'super@example.com',
  first_name: 'Super',
  last_name: 'User',
  name: 'Super User',
  groups: [],
  setores: [],
  funcoes: [],
  is_superuser: true,
  is_superintendencia: false,
  can_approve_super: true,
  permissions: [],
};

describe('App — boot resiliente a erro transitório (#1741)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('erro 500 no boot NÃO desloga → mostra tela de erro com retry (não o login)', async () => {
    getMeMock.mockRejectedValue(Object.assign(new Error('boom'), { status: 500 }));

    render(<App />);

    await screen.findByRole('button', { name: /Tentar novamente/i });
    expect(screen.queryByText('LOGIN_PAGE')).not.toBeInTheDocument();
    expect(screen.queryByTestId('app-routes')).not.toBeInTheDocument();
  });

  test('401 no boot → vai para o login (comportamento preservado)', async () => {
    getMeMock.mockRejectedValue(Object.assign(new Error('unauth'), { status: 401 }));

    render(<App />);

    await screen.findByText('LOGIN_PAGE');
    expect(screen.queryByRole('button', { name: /Tentar novamente/i })).not.toBeInTheDocument();
  });

  test('retry após 500 recupera a sessão', async () => {
    // Contador local (não `mockXOnce`): o `retry: 2` do vitest re-executa o corpo do
    // teste e o `mockXOnce` acumularia na fila entre tentativas → flaky. `calls`
    // reinicia a cada execução do teste, mantendo o determinismo.
    let calls = 0;
    getMeMock.mockImplementation(() => {
      calls += 1;
      return calls === 1
        ? Promise.reject(Object.assign(new Error('boom'), { status: 500 }))
        : Promise.resolve(fakeUser);
    });

    render(<App />);

    const retry = await screen.findByRole('button', { name: /Tentar novamente/i });
    await userEvent.click(retry);

    await screen.findByTestId('app-routes');
    expect(screen.queryByText('LOGIN_PAGE')).not.toBeInTheDocument();
  });
});
