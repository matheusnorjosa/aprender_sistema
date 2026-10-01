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
 *
 * Auditoria UX 30/09, rodada 2: o backend responde 403 (não 401) sem sessão, e 403 também
 * é falta de permissão. Antes de tirar alguém do sistema, o App pergunta ao servidor
 * (`GET /api/me/`): sem sessão → login com o motivo, sem POST de logout; sessão viva →
 * fica onde está.
 */

import { render, screen, waitFor, act } from '@testing-library/react';
import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';
import type { CurrentUser } from '../types';
import { apagarAvisoDoLogin, lerAvisoDoLogin } from '../utils/storage';

const { getMeMock, apiLogoutMock } = vi.hoisted(() => ({ getMeMock: vi.fn(), apiLogoutMock: vi.fn() }));

// Camada de dados
vi.mock('../api/availability', () => ({ getMe: getMeMock }));
vi.mock('../api/me', () => ({ getMyPolicies: vi.fn().mockResolvedValue([]) }));
vi.mock('../api/auth', () => ({ logout: apiLogoutMock }));

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
  gerencias: [],
  is_superuser: true,
  is_superintendencia: false,
  can_approve_super: true,
  permissions: [],
};

const locationOriginal = window.location;
const reloadMock = vi.fn();

describe('App — sessão expirada global (Issue #1376)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: { ...locationOriginal, reload: reloadMock },
    });
  });

  afterEach(() => {
    Object.defineProperty(window, 'location', { configurable: true, value: locationOriginal });
    apagarAvisoDoLogin();
  });

  test('auth:expired e o servidor confirma que não há sessão: login com o motivo, sem POST de logout', async () => {
    getMeMock
      .mockResolvedValueOnce(fakeUser)
      .mockRejectedValue({ status: 403, response: { status: 403, data: { code: 'NOT_AUTHENTICATED' } } });

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

    // Pergunta ao servidor (GET /api/me/) e, sem sessão, recarrega para o login com o motivo.
    await waitFor(() => expect(reloadMock).toHaveBeenCalledTimes(1));
    expect(getMeMock).toHaveBeenCalledTimes(2);
    expect(apiLogoutMock).not.toHaveBeenCalled();
    expect(lerAvisoDoLogin()).toBe('Sua sessão expirou. Entre de novo.');
  });

  test('auth:expired com a sessão viva no servidor não tira a pessoa do sistema', async () => {
    getMeMock.mockResolvedValue(fakeUser);

    render(<App />);
    await screen.findByTestId('app-routes');
    await act(async () => {});

    await act(async () => {
      window.dispatchEvent(new Event('auth:expired'));
    });

    await waitFor(() => expect(getMeMock).toHaveBeenCalledTimes(2));
    expect(screen.getByTestId('app-routes')).toBeInTheDocument();
    expect(screen.queryByText('LOGIN_PAGE')).not.toBeInTheDocument();
    expect(reloadMock).not.toHaveBeenCalled();
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
