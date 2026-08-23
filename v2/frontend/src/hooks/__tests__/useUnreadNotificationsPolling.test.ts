/**
 * useUnreadNotificationsPolling — busca a contagem de notificações não lidas,
 * mostra um toast quando surgem novas e persiste a última contagem por usuário
 * no localStorage. Mesmo padrão do useGCalAlertsPolling, mas via
 * `getNotificacoesNaoLidasCount` (GET /api/notificacoes-internas/unread-count/).
 *
 * Sem fake timers: o hook busca imediatamente no mount (usePolling immediate),
 * então basta `waitFor` no estado assíncrono.
 */
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import toast from 'react-hot-toast';
import { server } from '../../test/mocks/server';
import { apiUrl } from '../../test/mocks/handlers';
import { useUnreadNotificationsPolling } from '../useUnreadNotificationsPolling';

// react-hot-toast: default export é uma função chamável (toast(...)).
vi.mock('react-hot-toast', () => ({
  default: Object.assign(vi.fn(), {
    error: vi.fn(),
    success: vi.fn(),
    dismiss: vi.fn(),
  }),
}));

const UNREAD_URL = apiUrl('/notificacoes-internas/unread-count/');

describe('useUnreadNotificationsPolling', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  test('busca a contagem e persiste no localStorage', async () => {
    server.use(http.get(UNREAD_URL, () => HttpResponse.json({ count: 5 })));

    const { result } = renderHook(() =>
      useUnreadNotificationsPolling({ enabled: true, userId: 42 }),
    );

    await waitFor(() => expect(result.current.unreadNotifications).toBe(5));
    expect(localStorage.getItem('notifLastUnread:42')).toBe('5');
    // Primeira carga (sentinela -1): não notifica.
    expect(vi.mocked(toast)).not.toHaveBeenCalled();
  });

  test('dispara toast quando surgem novas notificações', async () => {
    // Última contagem conhecida = 2 (persistida de sessão anterior).
    localStorage.setItem('notifLastUnread:7', '2');
    server.use(http.get(UNREAD_URL, () => HttpResponse.json({ count: 5 })));

    const { result } = renderHook(() =>
      useUnreadNotificationsPolling({ enabled: true, userId: 7 }),
    );

    await waitFor(() => expect(result.current.unreadNotifications).toBe(5));
    await waitFor(() => expect(vi.mocked(toast)).toHaveBeenCalledTimes(1));
    expect(vi.mocked(toast)).toHaveBeenCalledWith(
      expect.stringContaining('3 nova'),
      { icon: '🔔', duration: 5000, id: 'new-notifications' },
    );
    // Persiste a nova contagem.
    expect(localStorage.getItem('notifLastUnread:7')).toBe('5');
  });

  test('não notifica na primeira carga (sem contagem anterior)', async () => {
    server.use(http.get(UNREAD_URL, () => HttpResponse.json({ count: 9 })));

    const { result } = renderHook(() =>
      useUnreadNotificationsPolling({ enabled: true, userId: 3 }),
    );

    await waitFor(() => expect(result.current.unreadNotifications).toBe(9));
    expect(localStorage.getItem('notifLastUnread:3')).toBe('9');
    expect(vi.mocked(toast)).not.toHaveBeenCalled();
  });

  test('enabled:false não busca', async () => {
    let hits = 0;
    server.use(
      http.get(UNREAD_URL, () => {
        hits += 1;
        return HttpResponse.json({ count: 5 });
      }),
    );

    const { result } = renderHook(() =>
      useUnreadNotificationsPolling({ enabled: false, userId: 42 }),
    );

    // Aguarda um ciclo real para garantir que nenhuma busca dispara.
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(hits).toBe(0);
    expect(result.current.unreadNotifications).toBe(0);
  });
});
