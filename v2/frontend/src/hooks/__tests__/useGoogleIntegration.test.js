/**
 * Tests: useGoogleIntegration Hook
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

import useGoogleIntegration from '../useGoogleIntegration';

describe('useGoogleIntegration', () => {
  beforeEach(() => {
    fetchAPIMock.mockReset();
  });

  test('deve inicializar com estado desconectado', async () => {
    fetchAPIMock.mockResolvedValue({
      connected: false, googleEmail: null, tokenExpiry: null, expiresInDays: null, isExpired: false,
    });

    const { result } = renderHook(() => useGoogleIntegration());

    await waitFor(() => {
      expect(fetchAPIMock).toHaveBeenCalledWith('/integrations/google/status/');
      expect(result.current.loading).toBe(false);
    });
    expect(result.current.status.connected).toBe(false);
  });

  test('fetchStatus() deve carregar status conectado do backend', async () => {
    fetchAPIMock.mockResolvedValue({
      connected: true,
      googleEmail: 'controle@aprendereditora.com.br',
      tokenExpiry: '2025-12-31T23:59:59Z',
      expiresInDays: 45,
      isExpired: false,
    });

    const { result } = renderHook(() => useGoogleIntegration());

    await waitFor(() => { expect(result.current.status.connected).toBe(true); });
    expect(result.current.status.googleEmail).toBe('controle@aprendereditora.com.br');
    expect(fetchAPIMock).toHaveBeenCalledWith('/integrations/google/status/');
  });

  test('fetchStatus() deve carregar status desconectado', async () => {
    fetchAPIMock.mockResolvedValue({
      connected: false, googleEmail: null, tokenExpiry: null, expiresInDays: null, isExpired: false,
    });

    const { result } = renderHook(() => useGoogleIntegration());

    await waitFor(() => {
      expect(fetchAPIMock).toHaveBeenCalledWith('/integrations/google/status/');
      expect(result.current.loading).toBe(false);
    });
    expect(result.current.status.connected).toBe(false);
    expect(result.current.loading).toBe(false);
  });

  test('fetchStatus() deve tratar erro do backend', async () => {
    fetchAPIMock.mockRejectedValue({ response: { data: { error: 'Erro de autenticação' } } });
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    const { result } = renderHook(() => useGoogleIntegration());

    await waitFor(() => { expect(result.current.error).toBe('Erro de autenticação'); });
    expect(result.current.loading).toBe(false);
    consoleSpy.mockRestore();
  });

  test('fetchStatus() deve usar mensagem genérica quando erro não tem detalhes', async () => {
    fetchAPIMock.mockRejectedValue(new Error('Network error'));
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    const { result } = renderHook(() => useGoogleIntegration());

    await waitFor(() => { expect(result.current.error).toBe('Erro ao carregar status da integração'); });
    consoleSpy.mockRestore();
  });

  test('disconnect() deve desconectar conta com sucesso', async () => {
    // Initial fetch returns connected
    fetchAPIMock.mockResolvedValueOnce({
      connected: true, googleEmail: 'controle@aprendereditora.com.br',
      tokenExpiry: '2025-12-31T23:59:59Z', expiresInDays: 45, isExpired: false,
    });
    // disconnect POST returns success
    fetchAPIMock.mockResolvedValueOnce({ message: 'Conta Google desconectada com sucesso' });

    const { result } = renderHook(() => useGoogleIntegration());
    await waitFor(() => { expect(result.current.status.connected).toBe(true); });

    let disconnectResult;
    await act(async () => { disconnectResult = await result.current.disconnect(); });

    expect(disconnectResult).toEqual({ success: true });
    expect(result.current.status.connected).toBe(false);
  });

  test('disconnect() deve tratar erro do backend', async () => {
    fetchAPIMock.mockResolvedValueOnce({
      connected: true, googleEmail: 'controle@aprendereditora.com.br',
      tokenExpiry: '2025-12-31T23:59:59Z', expiresInDays: 45, isExpired: false,
    });
    fetchAPIMock.mockRejectedValueOnce({ response: { data: { error: 'Nenhuma conexão Google encontrada' } } });
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    const { result } = renderHook(() => useGoogleIntegration());
    await waitFor(() => { expect(result.current.status.connected).toBe(true); });

    let disconnectResult;
    await act(async () => { disconnectResult = await result.current.disconnect(); });

    expect(disconnectResult).toEqual({ success: false, error: 'Nenhuma conexão Google encontrada' });
    expect(result.current.status.connected).toBe(true);
    consoleSpy.mockRestore();
  });

  test('disconnect() deve usar mensagem genérica quando erro não tem detalhes', async () => {
    fetchAPIMock.mockResolvedValueOnce({
      connected: true, googleEmail: 'controle@aprendereditora.com.br',
      tokenExpiry: '2025-12-31T23:59:59Z', expiresInDays: 45, isExpired: false,
    });
    fetchAPIMock.mockRejectedValueOnce(new Error('Network error'));
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    const { result } = renderHook(() => useGoogleIntegration());
    await waitFor(() => { expect(result.current.status.connected).toBe(true); });

    let disconnectResult;
    await act(async () => { disconnectResult = await result.current.disconnect(); });

    expect(disconnectResult.success).toBe(false);
    expect(result.current.error).toBe('Erro ao desconectar conta Google');
    consoleSpy.mockRestore();
  });

  test('deve chamar fetchStatus() automaticamente ao montar', async () => {
    fetchAPIMock.mockResolvedValue({
      connected: false, googleEmail: null, tokenExpiry: null, expiresInDays: null, isExpired: false,
    });

    renderHook(() => useGoogleIntegration());

    await waitFor(() => {
      expect(fetchAPIMock).toHaveBeenCalledWith('/integrations/google/status/');
    });
  });
});
