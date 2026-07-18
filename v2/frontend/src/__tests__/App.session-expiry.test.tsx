/**
 * Integração: tratamento global de sessão expirada (Issue #1376).
 *
 * Cobre o critério de aceite central: uma chamada API que retorna 401 pós-login
 * (emitida por `fetchAPI` como evento global `auth:expired`) deve levar o App a
 * limpar a sessão e retornar o usuário à tela de login — de forma GLOBAL, não
 * por-tela. E o guard: um `auth:expired` sem usuário logado (load inicial / rota
 * pública) NÃO deve causar loop.
 *
 * Estratégia: os filhos pesados (sidebar/header/rotas/login) são stubados para
 * isolar a máquina de estados de auth do App e o novo listener `auth:expired`.
 */

import { render, screen, waitFor, act } from '@testing-library/react';
import { describe, test, expect, vi, beforeEach } from 'vitest';
import type { CurrentUser } from '../types';

const getMeMock = vi.hoisted(() => vi.fn());

// Camada de dados
vi.mock('../api/availability', () => ({ getMe: getMeMock }));
vi.mock('../api/me', () => ({ getMyPolicies: vi.fn().mockResolvedValue([]) }));
vi.mock('../api/auth', () => ({ logout: vi.fn().mockResolvedValue(undefined) }));

// Filhos pesados → stubs
vi.mock('../components/AppSidebar', () => ({ AppSidebar: () => <div>SIDEBAR</div> }));
vi.mock('../components/AppHeader', () => ({ AppHeader: () => <div>HEADER</div> }));
vi.mock('../components/AppRoutes', () => ({
  AppRoutes: () => <div data-testid="app-routes">ROUTES</div>,
}));
vi.mock('../pages/Auth/LoginPage', () => ({ default: () => <div>LOGIN_PAGE</div> }));

// Monitor proativo de sessão (dead code religado) — stub para evitar timers/listeners
vi.mock('../hooks/useSessionMonitor', () => ({
  default: () => ({ showWarning: false, timeLeft: 7200, sessionAge: 7200, renewSession: vi.fn() }),
}));
vi.mock('../components/SessionExpiryWarning', () => ({ default: () => null }));

// Pollings / preload → no-op
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

describe('App — sessão expirada global (Issue #1376)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('usuário logado volta ao login quando auth:expired dispara (401 global)', async () => {
    getMeMock.mockResolvedValue(fakeUser);

    render(<App />);

    // Layout autenticado montado.
    await screen.findByTestId('app-routes');
    expect(screen.queryByText('LOGIN_PAGE')).not.toBeInTheDocument();

    // Assenta os passive effects antes de disparar o evento. O commit do DOM
    // (app-routes visível) pode preceder o flush do effect que sincroniza
    // `userRef.current` (App.tsx). Sem esta barreira, o handler `auth:expired`
    // às vezes vê `userRef.current === null`, cai no early-return e a transição
    // para o login nunca ocorre → `findByText('LOGIN_PAGE')` estoura o timeout
    // de forma intermitente (flaky #1577). Determinístico, sem tocar produção.
    await act(async () => {});

    // Simula 401 emitido por qualquer chamada da UI → fetchAPI dispara o evento.
    await act(async () => {
      window.dispatchEvent(new Event('auth:expired'));
    });

    // Tratamento global: sessão limpa → tela de login.
    await screen.findByText('LOGIN_PAGE');
    expect(screen.queryByTestId('app-routes')).not.toBeInTheDocument();
  });

  test('auth:expired antes do login NÃO causa loop (sem usuário → permanece no login)', async () => {
    getMeMock.mockRejectedValue({ status: 401, response: { status: 401 } });

    render(<App />);

    await screen.findByText('LOGIN_PAGE');

    act(() => {
      window.dispatchEvent(new Event('auth:expired'));
    });

    // Continua no login, sem crash/loop.
    await waitFor(() => {
      expect(screen.getByText('LOGIN_PAGE')).toBeInTheDocument();
    });
    expect(screen.queryByTestId('app-routes')).not.toBeInTheDocument();
  });
});
