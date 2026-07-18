/**
 * Tests: useGoogleIntegration Hook
 *
 * Contrato REAL do backend: o endpoint /integrations/google/status/ responde
 * SEMPRE em snake_case (apps/core/views_oauth.py:464-485). O hook normaliza
 * snake→camel via normalizeGoogleStatus (#1289) antes de expor o domínio.
 *
 * As fixtures abaixo usam o payload snake_case REAL (não camelCase inventado),
 * por isso os asserts leem o tipo de domínio camelCase pós-normalização.
 *
 * Migrated from axios mock to fetchAPI mock (Epic #1039)
 */

import { renderHook, waitFor } from '@testing-library/react';
import { act } from 'react';
import { describe, test, expect, beforeEach, vi } from 'vitest';

const fetchAPIMock = vi.hoisted(() => vi.fn());

vi.mock('../../api/config', async (importOriginal) => {
  const actual = await importOriginal();
  return { ...actual, fetchAPI: fetchAPIMock };
});

import useGoogleIntegration, { normalizeGoogleStatus } from '../useGoogleIntegration';

// Payloads REAIS do backend (snake_case) — apps/core/views_oauth.py:464-485
const RAW_CONNECTED = {
  connected: true,
  google_email: 'controle@aprendereditora.com.br',
  token_expiry: '2025-12-31T23:59:59Z',
  expires_in_days: 45,
  is_expired: false,
  default_calendar_id: null,
};
const RAW_DISCONNECTED = {
  connected: false,
  google_email: null,
  token_expiry: null,
  expires_in_days: null,
  is_expired: false,
  default_calendar_id: null,
};

describe('normalizeGoogleStatus (função pura)', () => {
  test('mapeia snake_case → camelCase (conectado)', () => {
    expect(normalizeGoogleStatus(RAW_CONNECTED)).toEqual({
      connected: true,
      googleEmail: 'controle@aprendereditora.com.br',
      tokenExpiry: '2025-12-31T23:59:59Z',
      expiresInDays: 45,
      isExpired: false,
      defaultCalendarId: null,
    });
  });

  test('mapeia snake_case → camelCase (desconectado)', () => {
    expect(normalizeGoogleStatus(RAW_DISCONNECTED)).toEqual({
      connected: false,
      googleEmail: null,
      tokenExpiry: null,
      expiresInDays: null,
      isExpired: false,
      defaultCalendarId: null,
    });
  });

  test('aplica defaults defensivos para payload parcial/ausente', () => {
    // Backend nunca omite campos, mas normalize é defensivo (rede/erro parcial).
    expect(normalizeGoogleStatus({})).toEqual({
      connected: false,
      googleEmail: null,
      tokenExpiry: null,
      expiresInDays: null,
      isExpired: false,
      defaultCalendarId: null,
    });
    expect(normalizeGoogleStatus(null)).toEqual({
      connected: false,
      googleEmail: null,
      tokenExpiry: null,
      expiresInDays: null,
      isExpired: false,
      defaultCalendarId: null,
    });
  });

  test('preserva default_calendar_id salvo (regressão de contrato)', () => {
    const raw = { ...RAW_CONNECTED, default_calendar_id: 'meu-cal@group.calendar.google.com' };
    expect(normalizeGoogleStatus(raw).defaultCalendarId).toBe('meu-cal@group.calendar.google.com');
  });
});

describe('useGoogleIntegration', () => {
  beforeEach(() => {
    fetchAPIMock.mockReset();
  });

  test('deve inicializar com estado desconectado', async () => {
    fetchAPIMock.mockResolvedValue({ ...RAW_DISCONNECTED });

    const { result } = renderHook(() => useGoogleIntegration());

    await waitFor(() => {
      expect(fetchAPIMock).toHaveBeenCalledWith('/integrations/google/status/');
      expect(result.current.loading).toBe(false);
    });
    expect(result.current.status.connected).toBe(false);
    expect(result.current.status.defaultCalendarId).toBe(null);
  });

  test('fetchStatus() deve carregar status conectado do backend (snake→camel)', async () => {
    fetchAPIMock.mockResolvedValue({ ...RAW_CONNECTED });

    const { result } = renderHook(() => useGoogleIntegration());

    await waitFor(() => {
      expect(result.current.status.connected).toBe(true);
    });
    expect(result.current.status.googleEmail).toBe('controle@aprendereditora.com.br');
    expect(result.current.status.tokenExpiry).toBe('2025-12-31T23:59:59Z');
    expect(result.current.status.expiresInDays).toBe(45);
    expect(result.current.status.isExpired).toBe(false);
    expect(fetchAPIMock).toHaveBeenCalledWith('/integrations/google/status/');
  });

  test('fetchStatus() deve carregar status desconectado', async () => {
    fetchAPIMock.mockResolvedValue({ ...RAW_DISCONNECTED });

    const { result } = renderHook(() => useGoogleIntegration());

    await waitFor(() => {
      expect(fetchAPIMock).toHaveBeenCalledWith('/integrations/google/status/');
      expect(result.current.loading).toBe(false);
    });
    expect(result.current.status.connected).toBe(false);
    expect(result.current.status.googleEmail).toBe(null);
    expect(result.current.loading).toBe(false);
  });

  test('fetchStatus() deve preservar default_calendar_id do backend (regressão de contrato)', async () => {
    fetchAPIMock.mockResolvedValue({
      ...RAW_CONNECTED,
      default_calendar_id: 'time-dat@group.calendar.google.com',
    });

    const { result } = renderHook(() => useGoogleIntegration());

    await waitFor(() => {
      expect(result.current.status.connected).toBe(true);
    });
    expect(result.current.status.defaultCalendarId).toBe('time-dat@group.calendar.google.com');
  });

  test('fetchStatus() deve tratar erro do backend', async () => {
    fetchAPIMock.mockRejectedValue({ response: { data: { error: 'Erro de autenticação' } } });
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    const { result } = renderHook(() => useGoogleIntegration());

    await waitFor(() => {
      expect(result.current.error).toBe('Erro de autenticação');
    });
    expect(result.current.loading).toBe(false);
    consoleSpy.mockRestore();
  });

  test('fetchStatus() deve usar mensagem genérica quando erro não tem detalhes', async () => {
    fetchAPIMock.mockRejectedValue(new Error('Network error'));
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    const { result } = renderHook(() => useGoogleIntegration());

    await waitFor(() => {
      expect(result.current.error).toBe('Erro ao carregar status da integração');
    });
    consoleSpy.mockRestore();
  });

  test('disconnect() deve desconectar conta com sucesso', async () => {
    // Initial fetch returns connected
    fetchAPIMock.mockResolvedValueOnce({ ...RAW_CONNECTED });
    // disconnect POST returns success
    fetchAPIMock.mockResolvedValueOnce({ message: 'Conta Google desconectada com sucesso' });

    const { result } = renderHook(() => useGoogleIntegration());
    await waitFor(() => {
      expect(result.current.status.connected).toBe(true);
    });

    let disconnectResult;
    await act(async () => {
      disconnectResult = await result.current.disconnect();
    });

    expect(disconnectResult).toEqual({ success: true });
    expect(result.current.status.connected).toBe(false);
    expect(result.current.status.defaultCalendarId).toBe(null);
  });

  test('disconnect() deve tratar erro do backend', async () => {
    fetchAPIMock.mockResolvedValueOnce({ ...RAW_CONNECTED });
    fetchAPIMock.mockRejectedValueOnce({ response: { data: { error: 'Nenhuma conexão Google encontrada' } } });
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    const { result } = renderHook(() => useGoogleIntegration());
    await waitFor(() => {
      expect(result.current.status.connected).toBe(true);
    });

    let disconnectResult;
    await act(async () => {
      disconnectResult = await result.current.disconnect();
    });

    expect(disconnectResult).toEqual({ success: false, error: 'Nenhuma conexão Google encontrada' });
    expect(result.current.status.connected).toBe(true);
    consoleSpy.mockRestore();
  });

  test('disconnect() deve usar mensagem genérica quando erro não tem detalhes', async () => {
    fetchAPIMock.mockResolvedValueOnce({ ...RAW_CONNECTED });
    fetchAPIMock.mockRejectedValueOnce(new Error('Network error'));
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    const { result } = renderHook(() => useGoogleIntegration());
    await waitFor(() => {
      expect(result.current.status.connected).toBe(true);
    });

    let disconnectResult;
    await act(async () => {
      disconnectResult = await result.current.disconnect();
    });

    expect(disconnectResult.success).toBe(false);
    expect(result.current.error).toBe('Erro ao desconectar conta Google');
    consoleSpy.mockRestore();
  });

  test('deve chamar fetchStatus() automaticamente ao montar', async () => {
    fetchAPIMock.mockResolvedValue({ ...RAW_DISCONNECTED });

    renderHook(() => useGoogleIntegration());

    await waitFor(() => {
      expect(fetchAPIMock).toHaveBeenCalledWith('/integrations/google/status/');
    });
  });
});
