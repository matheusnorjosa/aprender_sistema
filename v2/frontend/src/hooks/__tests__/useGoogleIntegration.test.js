/**
 * Tests: useGoogleIntegration Hook (Sprint 1 - Issue #1)
 *
 * Cobertura:
 * - fetchStatus(): Sucesso + erro
 * - disconnect(): Sucesso + erro
 * - Estado inicial
 * - useEffect (auto-fetch on mount)
 *
 * Refs:
 * - Sprint 1 (Issue #1): Frontend Tests
 */

import { renderHook, waitFor } from '@testing-library/react';
import { act } from 'react';
import { describe, test, expect, beforeEach, vi } from 'vitest';
import useGoogleIntegration from '../useGoogleIntegration';
import api from '../../api';

// Mock do módulo api
vi.mock('../../api');

describe('useGoogleIntegration', () => {
  beforeEach(() => {
    // Limpar mocks antes de cada teste
    vi.clearAllMocks();
  });

  // ============================================================================
  // TESTES DE ESTADO INICIAL
  // ============================================================================

  test('deve inicializar com estado desconectado', async () => {
    // Mock fetchStatus (será chamado no useEffect)
    api.get.mockResolvedValue({
      data: {
        connected: false,
        googleEmail: null,
        tokenExpiry: null,
        expiresInDays: null,
        isExpired: false,
      },
    });

    const { result } = renderHook(() => useGoogleIntegration());

    // Aguardar useEffect executar (auto-fetch)
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    // Estado final após fetch
    expect(result.current.status.connected).toBe(false);
    expect(result.current.error).toBe(null);
  });

  // ============================================================================
  // TESTES DE fetchStatus()
  // ============================================================================

  test('fetchStatus() deve carregar status conectado do backend', async () => {
    const mockData = {
      connected: true,
      googleEmail: 'controle@aprendereditora.com.br',
      tokenExpiry: '2025-12-31T23:59:59Z',
      expiresInDays: 45,
      isExpired: false,
    };

    api.get.mockResolvedValue({ data: mockData });

    const { result } = renderHook(() => useGoogleIntegration());

    // useEffect chama fetchStatus automaticamente
    await waitFor(() => {
      expect(result.current.status.connected).toBe(true);
    });

    expect(result.current.status.googleEmail).toBe('controle@aprendereditora.com.br');
    expect(result.current.status.tokenExpiry).toBe('2025-12-31T23:59:59Z');
    expect(result.current.status.expiresInDays).toBe(45);
    expect(result.current.status.isExpired).toBe(false);
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBe(null);

    // Validar chamada à API
    expect(api.get).toHaveBeenCalledWith('/integrations/google/status/');
    expect(api.get).toHaveBeenCalledTimes(1);
  });

  test('fetchStatus() deve carregar status desconectado', async () => {
    const mockData = {
      connected: false,
      googleEmail: null,
      tokenExpiry: null,
      expiresInDays: null,
      isExpired: false,
    };

    api.get.mockResolvedValue({ data: mockData });

    const { result } = renderHook(() => useGoogleIntegration());

    await waitFor(() => {
      expect(result.current.status.connected).toBe(false);
    });

    expect(result.current.status.googleEmail).toBe(null);
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBe(null);
  });

  test('fetchStatus() deve tratar erro do backend', async () => {
    const mockError = {
      response: {
        data: {
          error: 'Erro de autenticação',
        },
      },
    };

    api.get.mockRejectedValue(mockError);

    // Suprimir console.error durante o teste
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    const { result } = renderHook(() => useGoogleIntegration());

    await waitFor(() => {
      expect(result.current.error).toBe('Erro de autenticação');
    });

    expect(result.current.loading).toBe(false);
    expect(result.current.status.connected).toBe(false);

    consoleSpy.mockRestore();
  });

  test('fetchStatus() deve usar mensagem genérica quando erro não tem detalhes', async () => {
    api.get.mockRejectedValue(new Error('Network error'));

    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    const { result } = renderHook(() => useGoogleIntegration());

    await waitFor(() => {
      expect(result.current.error).toBe('Erro ao carregar status da integração');
    });

    expect(result.current.loading).toBe(false);

    consoleSpy.mockRestore();
  });

  // ============================================================================
  // TESTES DE disconnect()
  // ============================================================================

  test('disconnect() deve desconectar conta com sucesso', async () => {
    // Mock inicial conectado
    api.get.mockResolvedValue({
      data: {
        connected: true,
        googleEmail: 'controle@aprendereditora.com.br',
        tokenExpiry: '2025-12-31T23:59:59Z',
        expiresInDays: 45,
        isExpired: false,
      },
    });

    // Mock disconnect
    api.post.mockResolvedValue({
      data: {
        message: 'Conta Google desconectada com sucesso',
        google_email: 'controle@aprendereditora.com.br',
      },
    });

    const { result } = renderHook(() => useGoogleIntegration());

    // Aguardar fetch inicial
    await waitFor(() => {
      expect(result.current.status.connected).toBe(true);
    });

    // Chamar disconnect
    let disconnectResult;
    await act(async () => {
      disconnectResult = await result.current.disconnect();
    });

    // Validar resultado
    expect(disconnectResult).toEqual({ success: true });

    // Validar estado local atualizado
    expect(result.current.status.connected).toBe(false);
    expect(result.current.status.googleEmail).toBe(null);
    expect(result.current.status.tokenExpiry).toBe(null);
    expect(result.current.status.expiresInDays).toBe(null);
    expect(result.current.status.isExpired).toBe(false);
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBe(null);

    // Validar chamada à API
    expect(api.post).toHaveBeenCalledWith('/integrations/google/disconnect/');
    expect(api.post).toHaveBeenCalledTimes(1);
  });

  test('disconnect() deve tratar erro do backend', async () => {
    // Mock inicial conectado
    api.get.mockResolvedValue({
      data: {
        connected: true,
        googleEmail: 'controle@aprendereditora.com.br',
        tokenExpiry: '2025-12-31T23:59:59Z',
        expiresInDays: 45,
        isExpired: false,
      },
    });

    // Mock disconnect com erro
    const mockError = {
      response: {
        data: {
          error: 'Nenhuma conexão Google encontrada',
        },
      },
    };

    api.post.mockRejectedValue(mockError);

    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    const { result } = renderHook(() => useGoogleIntegration());

    // Aguardar fetch inicial
    await waitFor(() => {
      expect(result.current.status.connected).toBe(true);
    });

    // Chamar disconnect
    let disconnectResult;
    await act(async () => {
      disconnectResult = await result.current.disconnect();
    });

    // Validar resultado
    expect(disconnectResult).toEqual({
      success: false,
      error: 'Nenhuma conexão Google encontrada',
    });

    // Validar erro no estado
    expect(result.current.error).toBe('Nenhuma conexão Google encontrada');
    expect(result.current.loading).toBe(false);

    // Estado deve permanecer conectado (falha ao desconectar)
    expect(result.current.status.connected).toBe(true);

    consoleSpy.mockRestore();
  });

  test('disconnect() deve usar mensagem genérica quando erro não tem detalhes', async () => {
    // Mock inicial conectado
    api.get.mockResolvedValue({
      data: {
        connected: true,
        googleEmail: 'controle@aprendereditora.com.br',
        tokenExpiry: '2025-12-31T23:59:59Z',
        expiresInDays: 45,
        isExpired: false,
      },
    });

    // Mock disconnect com erro sem detalhes
    api.post.mockRejectedValue(new Error('Network error'));

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

  // ============================================================================
  // TESTES DE useEffect (auto-fetch on mount)
  // ============================================================================

  test('deve chamar fetchStatus() automaticamente ao montar', async () => {
    api.get.mockResolvedValue({
      data: {
        connected: false,
        googleEmail: null,
        tokenExpiry: null,
        expiresInDays: null,
        isExpired: false,
      },
    });

    renderHook(() => useGoogleIntegration());

    // useEffect deve ter chamado fetchStatus
    await waitFor(() => {
      expect(api.get).toHaveBeenCalledWith('/integrations/google/status/');
    });

    expect(api.get).toHaveBeenCalledTimes(1);
  });
});

// ============================================================================
// RESUMO DOS TESTES
// ============================================================================

// Testes do Hook (8):
// ✅ Estado inicial desconectado
// ✅ fetchStatus() - sucesso (conectado)
// ✅ fetchStatus() - sucesso (desconectado)
// ✅ fetchStatus() - erro com detalhes
// ✅ fetchStatus() - erro genérico
// ✅ disconnect() - sucesso
// ✅ disconnect() - erro com detalhes
// ✅ disconnect() - erro genérico
// ✅ useEffect auto-fetch on mount
//
// Total: 9 testes
// Cobertura esperada: ~95%
