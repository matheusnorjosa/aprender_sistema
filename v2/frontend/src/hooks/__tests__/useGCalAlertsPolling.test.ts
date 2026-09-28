/**
 * Tests: useGCalAlertsPolling.
 *
 * O hook faz fetch-on-mount (usePolling immediate) de getAlertsSummary via MSW,
 * popula `alerts` e dispara toast.error só quando o nº de erros AUMENTA acima do
 * último visto (baseline), respeitando o cooldown. Persiste o baseline em
 * localStorage (storageKeys.gcalErrors).
 *
 * O 2º fetch é forçado por um evento 'visibilitychange' (usePolling escuta e
 * refaz a busca ao voltar para a aba visível), evitando fake timers.
 *
 * #2039: `google_reconnect` lista quem teve a conta Google removida pelo sistema.
 * Com count > 0 o hook mostra UM aviso (toast); só avisa de novo se o conjunto de
 * ids mudar.
 */
import { renderHook, waitFor, act } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '../../test/mocks/server';
import { apiUrl } from '../../test/mocks/handlers';
import { storageKeys } from '../../utils/storage';

vi.mock('react-hot-toast', () => ({
  default: Object.assign(vi.fn(), { error: vi.fn(), success: vi.fn() }),
}));

import toast from 'react-hot-toast';
import { useGCalAlertsPolling } from '../useGCalAlertsPolling';

const ALERTS_PATH = '/gcal/dashboard/alerts/summary/';

interface AlertsPayload {
  errors: number;
  pending: number;
  published: number;
  none: number;
  google_reconnect?: { count: number; users: { id: number; nome: string }[] };
}

function alertsHandler(payload: AlertsPayload, onHit?: () => void) {
  return http.get(apiUrl(ALERTS_PATH), () => {
    onHit?.();
    return HttpResponse.json(payload);
  });
}

describe('useGCalAlertsPolling', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  afterEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
    vi.useRealTimers();
  });

  test('enabled:false não busca alertas', async () => {
    const requestSpy = vi.fn();
    server.use(alertsHandler({ errors: 9, pending: 0, published: 0, none: 0 }, requestSpy));

    const { result } = renderHook(() => useGCalAlertsPolling({ enabled: false }));

    // Nenhum fetch é agendado quando desabilitado.
    await new Promise((resolve) => setTimeout(resolve, 30));

    expect(requestSpy).not.toHaveBeenCalled();
    expect(result.current.alerts).toEqual({ errors: 0, pending: 0, published: 0, none: 0 });
    expect(vi.mocked(toast.error)).not.toHaveBeenCalled();
  });

  test('primeira carga popula alerts sem toast (baseline)', async () => {
    server.use(alertsHandler({ errors: 0, pending: 3, published: 2, none: 1 }));

    const { result } = renderHook(() => useGCalAlertsPolling({ enabled: true }));

    // errors=0 no baseline; usa pending para confirmar que o fetch resolveu.
    await waitFor(() => expect(result.current.alerts.pending).toBe(3));

    expect(result.current.alerts.errors).toBe(0);
    expect(vi.mocked(toast.error)).not.toHaveBeenCalled();
  });

  test('aumento de erros dispara toast', async () => {
    server.use(alertsHandler({ errors: 0, pending: 3, published: 0, none: 0 }));

    const { result } = renderHook(() => useGCalAlertsPolling({ enabled: true }));
    await waitFor(() => expect(result.current.alerts.pending).toBe(3));
    expect(vi.mocked(toast.error)).not.toHaveBeenCalled();

    // Segunda carga com mais erros → toast.
    server.use(alertsHandler({ errors: 4, pending: 1, published: 0, none: 0 }));
    await act(async () => {
      document.dispatchEvent(new Event('visibilitychange'));
    });

    await waitFor(() => expect(vi.mocked(toast.error)).toHaveBeenCalledTimes(1));
    expect(vi.mocked(toast.error)).toHaveBeenCalledWith(
      expect.stringContaining('0 → 4'),
      expect.objectContaining({ duration: 5000 }),
    );
    expect(result.current.alerts.errors).toBe(4);
  });

  test('persiste o nº de erros em localStorage', async () => {
    server.use(alertsHandler({ errors: 0, pending: 3, published: 0, none: 0 }));

    const { result } = renderHook(() => useGCalAlertsPolling({ enabled: true }));
    await waitFor(() => expect(result.current.alerts.pending).toBe(3));

    server.use(alertsHandler({ errors: 7, pending: 0, published: 0, none: 0 }));
    await act(async () => {
      document.dispatchEvent(new Event('visibilitychange'));
    });

    await waitFor(() => expect(localStorage.getItem(storageKeys.gcalErrors)).toBe('7'));
    expect(result.current.alerts.errors).toBe(7);
  });
});

describe('useGCalAlertsPolling — contas Google a reconectar (#2039)', () => {
  const ANA = { id: 12, nome: 'Ana Souza' };
  const BRUNO = { id: 13, nome: 'Bruno Lima' };
  const BASE = { errors: 0, pending: 3, published: 0, none: 0 };

  function reconectar(users: { id: number; nome: string }[]): AlertsPayload {
    return { ...BASE, google_reconnect: { count: users.length, users } };
  }

  async function refetch() {
    await act(async () => {
      document.dispatchEvent(new Event('visibilitychange'));
    });
  }

  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  afterEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  test('duas pessoas: um aviso no plural com os nomes', async () => {
    server.use(alertsHandler(reconectar([ANA, BRUNO])));

    renderHook(() => useGCalAlertsPolling({ enabled: true }));

    await waitFor(() => expect(vi.mocked(toast)).toHaveBeenCalledTimes(1));
    expect(vi.mocked(toast)).toHaveBeenCalledWith(
      '2 pessoas precisam reconectar a conta Google: Ana Souza, Bruno Lima.',
      expect.anything(),
    );
  });

  test('uma pessoa: aviso no singular', async () => {
    server.use(alertsHandler(reconectar([ANA])));

    renderHook(() => useGCalAlertsPolling({ enabled: true }));

    await waitFor(() => expect(vi.mocked(toast)).toHaveBeenCalledTimes(1));
    expect(vi.mocked(toast)).toHaveBeenCalledWith(
      '1 pessoa precisa reconectar a conta Google: Ana Souza.',
      expect.anything(),
    );
  });

  test('mais de três pessoas: mostra as 3 primeiras e "e mais N"', async () => {
    server.use(
      alertsHandler(
        reconectar([
          ANA,
          BRUNO,
          { id: 14, nome: 'Carla Dias' },
          { id: 15, nome: 'Davi Reis' },
          { id: 16, nome: 'Eva Melo' },
        ]),
      ),
    );

    renderHook(() => useGCalAlertsPolling({ enabled: true }));

    await waitFor(() => expect(vi.mocked(toast)).toHaveBeenCalledTimes(1));
    expect(vi.mocked(toast)).toHaveBeenCalledWith(
      '5 pessoas precisam reconectar a conta Google: Ana Souza, Bruno Lima, Carla Dias e mais 2.',
      expect.anything(),
    );
  });

  test('mesmo conjunto no polling seguinte não repete o aviso; conjunto novo avisa de novo', async () => {
    let hits = 0;
    const contar = () => {
      hits += 1;
    };
    server.use(alertsHandler(reconectar([ANA, BRUNO]), contar));

    renderHook(() => useGCalAlertsPolling({ enabled: true }));
    await waitFor(() => expect(vi.mocked(toast)).toHaveBeenCalledTimes(1));

    // Mesmos ids (em outra ordem) → sem novo aviso.
    server.use(alertsHandler(reconectar([BRUNO, ANA]), contar));
    await refetch();
    await waitFor(() => expect(hits).toBe(2));
    expect(vi.mocked(toast)).toHaveBeenCalledTimes(1);

    // Bruno reconectou: o conjunto mudou → avisa de novo, só com a Ana.
    server.use(alertsHandler(reconectar([ANA]), contar));
    await refetch();
    await waitFor(() => expect(vi.mocked(toast)).toHaveBeenCalledTimes(2));
    expect(vi.mocked(toast)).toHaveBeenLastCalledWith(
      '1 pessoa precisa reconectar a conta Google: Ana Souza.',
      expect.anything(),
    );
  });

  test('count = 0 ou campo ausente: nenhum aviso', async () => {
    let hits = 0;
    const contar = () => {
      hits += 1;
    };
    server.use(alertsHandler(reconectar([]), contar));

    renderHook(() => useGCalAlertsPolling({ enabled: true }));
    await waitFor(() => expect(hits).toBe(1));

    // Payload antigo, sem `google_reconnect`.
    server.use(alertsHandler(BASE, contar));
    await refetch();
    await waitFor(() => expect(hits).toBe(2));

    expect(vi.mocked(toast)).not.toHaveBeenCalled();
  });
});
