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
