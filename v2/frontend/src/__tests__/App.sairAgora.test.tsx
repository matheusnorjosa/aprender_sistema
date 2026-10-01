/**
 * Auditoria UX 30/09 (ALTA): "Sair agora" usa o logout real do App.
 *
 * Antes, o aviso navegava para '/logout' e o monitor para '/login' — rotas que não
 * existem: a tela ficava em branco e a sessão continuava aberta. O "Sair agora" segue o
 * "Sair" do cabeçalho: API de logout + limpar caches + recarregar (o login aparece
 * quando não há sessão).
 *
 * Rodada 2 (ALTA): a sessão é do navegador, o relógio local é de cada aba. Sessão que o
 * servidor já deu por encerrada NÃO faz POST de logout (o de uma aba ociosa derrubava as
 * outras): limpa os caches, guarda o motivo para o login e recarrega. E o monitor só
 * existe com usuário logado (MÉDIA: na tela de login ele também fazia POST de logout).
 */

import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';
import { message } from 'antd';
import type { CurrentUser } from '../types';
import { apagarAvisoDoLogin, lerAvisoDoLogin, storageKeys } from '../utils/storage';

const { getMeMock, apiLogoutMock, clearApiCachesMock, monitor } = vi.hoisted(() => ({
  getMeMock: vi.fn(),
  apiLogoutMock: vi.fn(),
  clearApiCachesMock: vi.fn(),
  monitor: { onExpired: undefined as undefined | (() => void) },
}));

vi.mock('../api/availability', () => ({ getMe: getMeMock }));
vi.mock('../api/me', () => ({ getMyPolicies: vi.fn().mockResolvedValue([]) }));
vi.mock('../api/auth', () => ({ logout: apiLogoutMock }));
vi.mock('../services/swCache', () => ({ clearApiCaches: clearApiCachesMock }));

vi.mock('../components/AppSidebar', () => ({ AppSidebar: () => <div>SIDEBAR</div> }));
vi.mock('../components/AppHeader', () => ({ AppHeader: () => <div>HEADER</div> }));
vi.mock('../components/AppRoutes', () => ({ AppRoutes: () => <div data-testid="app-routes">ROUTES</div> }));
vi.mock('../pages/Auth/LoginPage', () => ({ default: () => <div>LOGIN_PAGE</div> }));

// O monitor guarda o callback que o App passa; o aviso vira um botão que chama onLogout.
vi.mock('../hooks/useSessionMonitor', () => ({
  default: (onExpired: () => void) => {
    monitor.onExpired = onExpired;
    return { showWarning: true, timeLeft: 120, sessionAge: 7200, renewSession: vi.fn() };
  },
}));
vi.mock('../components/SessionExpiryWarning', () => ({
  default: ({ onLogout }: { onLogout: () => void }) => <button onClick={onLogout}>Sair agora</button>,
}));

vi.mock('../hooks/useGCalAlertsPolling', () => ({
  useGCalAlertsPolling: () => ({ alerts: { errors: 0, warnings: 0 } }),
}));
vi.mock('../hooks/useUnreadNotificationsPolling', () => ({
  useUnreadNotificationsPolling: () => ({ unreadNotifications: 0 }),
}));
vi.mock('../services/preloadSearchData', () => ({ preloadSearchData: vi.fn().mockResolvedValue(undefined) }));

import App from '../App';

const fakeUser = {
  id: 1,
  username: 'coord',
  email: 'coord@example.com',
  first_name: 'Coord',
  last_name: 'Teste',
  name: 'Coord Teste',
  groups: [],
  setores: [],
  funcoes: [],
  gerencias: [],
  is_superuser: false,
  is_superintendencia: false,
  can_approve_super: false,
  permissions: [],
} as CurrentUser;

const locationOriginal = window.location;
const reloadMock = vi.fn();

describe('App — "Sair agora" e sessão expirada usam o logout real', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    monitor.onExpired = undefined;
    getMeMock.mockResolvedValue(fakeUser);
    apiLogoutMock.mockResolvedValue(undefined);
    clearApiCachesMock.mockResolvedValue(undefined);
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: { ...locationOriginal, reload: reloadMock },
    });
  });

  afterEach(() => {
    Object.defineProperty(window, 'location', { configurable: true, value: locationOriginal });
    apagarAvisoDoLogin();
    vi.restoreAllMocks();
  });

  test('"Sair agora" chama a API de logout, limpa os caches e recarrega', async () => {
    render(<App />);
    await screen.findByTestId('app-routes');

    fireEvent.click(screen.getByRole('button', { name: 'Sair agora' }));

    await waitFor(() => expect(reloadMock).toHaveBeenCalledTimes(1));
    expect(apiLogoutMock).toHaveBeenCalledTimes(1);
    expect(clearApiCachesMock).toHaveBeenCalledTimes(1);
  });

  // Rodada 3 (BAIXA): sem rede, o "Sair" dizia "Sessão encerrada localmente" e recarregava:
  // a sessão seguia aberta no servidor e a tela recarregada era o JSON offline do service
  // worker. Agora fica na tela, diz o motivo, e o Sair funciona quando a rede volta.
  test('"Sair agora" sem rede: não recarrega, diz o motivo, e funciona quando a rede volta', async () => {
    const erroSpy = vi.spyOn(message, 'error');
    apiLogoutMock.mockRejectedValueOnce(new TypeError('Sem conexão com o servidor.'));
    render(<App />);
    await screen.findByTestId('app-routes');

    fireEvent.click(screen.getByRole('button', { name: 'Sair agora' }));

    await waitFor(() => expect(erroSpy).toHaveBeenCalledWith('Não foi possível sair: sem conexão. Tente de novo.'));
    expect(reloadMock).not.toHaveBeenCalled();
    expect(clearApiCachesMock).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole('button', { name: 'Sair agora' }));

    await waitFor(() => expect(reloadMock).toHaveBeenCalledTimes(1));
    expect(apiLogoutMock).toHaveBeenCalledTimes(2);
  });

  test('"Sair agora" com erro do servidor (5xx): não recarrega e diz o motivo', async () => {
    apiLogoutMock.mockRejectedValueOnce(
      Object.assign(new Error('HTTP 502: Bad Gateway'), { status: 502, response: { status: 502 } }),
    );
    const erroSpy = vi.spyOn(message, 'error');
    render(<App />);
    await screen.findByTestId('app-routes');

    fireEvent.click(screen.getByRole('button', { name: 'Sair agora' }));

    await waitFor(() => expect(erroSpy).toHaveBeenCalledWith('Não foi possível sair: erro no servidor. Tente de novo.'));
    expect(reloadMock).not.toHaveBeenCalled();
  });

  test('"Sair agora" com a sessão já encerrada no servidor (403): segue para o login', async () => {
    apiLogoutMock.mockRejectedValueOnce({ status: 403, response: { status: 403, data: { code: 'NOT_AUTHENTICATED' } } });
    render(<App />);
    await screen.findByTestId('app-routes');

    fireEvent.click(screen.getByRole('button', { name: 'Sair agora' }));

    await waitFor(() => expect(reloadMock).toHaveBeenCalledTimes(1));
    expect(clearApiCachesMock).toHaveBeenCalledTimes(1);
  });

  // Rodada 4 (INFO): só 401 ou 403 com code NOT_AUTHENTICATED querem dizer "sessão já
  // encerrada" (como no fetchAPI). O 403 de CSRF com a sessão viva recarregava, o boot achava a
  // sessão e a pessoa continuava logada sem saber que o Sair falhou.
  test('"Sair agora" com 403 de CSRF (sessão viva): não recarrega e diz o motivo', async () => {
    apiLogoutMock.mockRejectedValueOnce(
      Object.assign(new Error('CSRF Failed: CSRF token missing.'), {
        status: 403,
        response: { status: 403, data: { code: 'PERMISSION_DENIED', detail: 'CSRF Failed: CSRF token missing.' } },
      }),
    );
    const erroSpy = vi.spyOn(message, 'error');
    render(<App />);
    await screen.findByTestId('app-routes');

    fireEvent.click(screen.getByRole('button', { name: 'Sair agora' }));

    await waitFor(() => expect(erroSpy).toHaveBeenCalledWith('Não foi possível sair: erro no servidor. Tente de novo.'));
    expect(reloadMock).not.toHaveBeenCalled();
    expect(clearApiCachesMock).not.toHaveBeenCalled();
  });

  test('"Sair agora" com 401: a sessão já acabou, segue para o login', async () => {
    apiLogoutMock.mockRejectedValueOnce({ status: 401, response: { status: 401, data: {} } });
    render(<App />);
    await screen.findByTestId('app-routes');

    fireEvent.click(screen.getByRole('button', { name: 'Sair agora' }));

    await waitFor(() => expect(reloadMock).toHaveBeenCalledTimes(1));
  });

  test('sessão expirada (monitor) não faz POST de logout: limpa os caches, guarda o motivo e recarrega', async () => {
    render(<App />);
    await screen.findByTestId('app-routes');
    expect(monitor.onExpired).toBeTypeOf('function');

    await act(async () => {
      monitor.onExpired?.();
    });

    await waitFor(() => expect(reloadMock).toHaveBeenCalledTimes(1));
    expect(apiLogoutMock).not.toHaveBeenCalled();
    expect(clearApiCachesMock).toHaveBeenCalledTimes(1);
    expect(lerAvisoDoLogin()).toBe('Sua sessão expirou por inatividade. Entre de novo.');
  });

  // Rodada 6 (MÉDIA): o "Sair" de uma aba não avisava as outras. As respostas do próprio logout
  // (GET /api/csrf/ e o POST) gravavam o horário comum às abas, e as outras contavam dele: seguiam
  // com cara de logadas por mais 121 min, fechavam sozinhas o aviso aberto e depois iam ao login
  // com "expirou por inatividade". Agora o "Sair" apaga esse horário, e o evento 'storage' (que o
  // navegador entrega só às OUTRAS abas) faz cada uma perguntar ao servidor na hora.
  const outraAbaSaiu = (): StorageEvent =>
    new StorageEvent('storage', { key: storageKeys.sessaoUltimaResposta, oldValue: '1', newValue: null });

  test('"Sair" bem-sucedido apaga o horário comum às abas', async () => {
    localStorage.setItem(storageKeys.sessaoUltimaResposta, String(Date.now()));
    render(<App />);
    await screen.findByTestId('app-routes');

    fireEvent.click(screen.getByRole('button', { name: 'Sair agora' }));

    await waitFor(() => expect(reloadMock).toHaveBeenCalledTimes(1));
    expect(localStorage.getItem(storageKeys.sessaoUltimaResposta)).toBeNull();
  });

  test('"Sair" sem rede não apaga o horário comum às abas: a sessão continua', async () => {
    localStorage.setItem(storageKeys.sessaoUltimaResposta, '123');
    apiLogoutMock.mockRejectedValueOnce(new TypeError('Sem conexão com o servidor.'));
    const erroSpy = vi.spyOn(message, 'error');
    render(<App />);
    await screen.findByTestId('app-routes');

    fireEvent.click(screen.getByRole('button', { name: 'Sair agora' }));

    await waitFor(() => expect(erroSpy).toHaveBeenCalled());
    expect(localStorage.getItem(storageKeys.sessaoUltimaResposta)).toBe('123');
  });

  test('outra aba saiu: pergunta ao servidor e, sem sessão, vai ao login com o motivo, sem POST de logout', async () => {
    render(<App />);
    await screen.findByTestId('app-routes');
    getMeMock.mockRejectedValueOnce({ status: 403, response: { status: 403, data: { code: 'NOT_AUTHENTICATED' } } });

    await act(async () => {
      window.dispatchEvent(outraAbaSaiu());
    });

    await waitFor(() => expect(reloadMock).toHaveBeenCalledTimes(1));
    expect(getMeMock).toHaveBeenCalledTimes(2); // o boot e a pergunta
    expect(apiLogoutMock).not.toHaveBeenCalled();
    expect(clearApiCachesMock).toHaveBeenCalledTimes(1);
    expect(lerAvisoDoLogin()).toBe('Você saiu do sistema em outra aba. Entre de novo.');
  });

  test('outra aba saiu, mas o servidor tem sessão (entrou de novo): fica na tela', async () => {
    render(<App />);
    await screen.findByTestId('app-routes');

    await act(async () => {
      window.dispatchEvent(outraAbaSaiu());
    });

    await waitFor(() => expect(getMeMock).toHaveBeenCalledTimes(2));
    expect(reloadMock).not.toHaveBeenCalled();
    expect(screen.getByTestId('app-routes')).toBeInTheDocument();
  });

  test('a resposta do servidor a outra aba (horário novo) não faz pergunta', async () => {
    render(<App />);
    await screen.findByTestId('app-routes');

    await act(async () => {
      window.dispatchEvent(new StorageEvent('storage', {
        key: storageKeys.sessaoUltimaResposta, oldValue: '1', newValue: String(Date.now()),
      }));
    });

    expect(getMeMock).toHaveBeenCalledTimes(1); // só o boot
    expect(reloadMock).not.toHaveBeenCalled();
  });

  test('na tela de login o monitor de sessão não roda e o aviso não aparece', async () => {
    getMeMock.mockRejectedValue({ status: 403, response: { status: 403 } });

    render(<App />);
    await screen.findByText('LOGIN_PAGE');

    expect(monitor.onExpired).toBeUndefined();
    expect(screen.queryByRole('button', { name: 'Sair agora' })).not.toBeInTheDocument();
  });
});
