/**
 * Tests: useConfig Hook (Issue #187)
 *
 * Cobertura:
 * - Carregamento inicial de config
 * - Estado loading
 * - Erro no carregamento
 * - Salvar config com sucesso
 * - Erro ao salvar config
 */

import { renderHook, waitFor, act } from '@testing-library/react'
import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest'
import { useConfig } from '../useConfig'

// Mock fetch
const mockFetch = vi.fn()
globalThis.fetch = mockFetch

// Mock antd message
vi.mock('antd', () => ({
  message: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

describe('useConfig', () => {
  const mockConfigData = {
    buffer_deslocamento_minutos: 60,
    capacidade_maxima_horas: 8,
    sessao_expira_minutos: 30,
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  // ============================================================================
  // TESTES DE CARREGAMENTO INICIAL
  // ============================================================================

  test('deve iniciar com loading=true', () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockConfigData,
    })

    const { result } = renderHook(() => useConfig())

    expect(result.current.loading).toBe(true)
  })

  test('deve carregar config com sucesso', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockConfigData,
    })

    const { result } = renderHook(() => useConfig())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.config).toEqual(mockConfigData)
    expect(mockFetch).toHaveBeenCalledWith('/api/config/', {
      credentials: 'include',
    })
  })

  test('deve lidar com erro de carregamento', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
    })

    const { result } = renderHook(() => useConfig())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.config).toBeNull()
  })

  test('deve lidar com erro de rede', async () => {
    mockFetch.mockRejectedValueOnce(new Error('Network error'))

    const { result } = renderHook(() => useConfig())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.config).toBeNull()
  })

  // ============================================================================
  // TESTES DE SAVECONFIG
  // ============================================================================

  test('saveConfig deve retornar true em sucesso', async () => {
    // Mock para load inicial
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockConfigData,
    })

    const { result } = renderHook(() => useConfig())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // Mock para saveConfig
    const updatedConfig = { ...mockConfigData, buffer_deslocamento_minutos: 90 }
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => updatedConfig,
    })

    let saveResult
    await act(async () => {
      saveResult = await result.current.saveConfig(updatedConfig)
    })

    expect(saveResult).toBe(true)
    expect(result.current.config).toEqual(updatedConfig)
  })

  test('saveConfig deve retornar false em erro', async () => {
    // Mock para load inicial
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockConfigData,
    })

    const { result } = renderHook(() => useConfig())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // Mock para saveConfig com erro
    mockFetch.mockResolvedValueOnce({
      ok: false,
      json: async () => ({ buffer_deslocamento_minutos: ['Valor inválido'] }),
    })

    let saveResult
    await act(async () => {
      saveResult = await result.current.saveConfig({ buffer_deslocamento_minutos: -1 })
    })

    expect(saveResult).toBe(false)
  })

  // ============================================================================
  // TESTES DE RELOAD
  // ============================================================================

  test('reload deve recarregar config do servidor', async () => {
    // Mock para load inicial
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockConfigData,
    })

    const { result } = renderHook(() => useConfig())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // Mock para reload
    const updatedConfig = { ...mockConfigData, buffer_deslocamento_minutos: 120 }
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => updatedConfig,
    })

    await act(async () => {
      await result.current.reload()
    })

    expect(result.current.config).toEqual(updatedConfig)
    expect(mockFetch).toHaveBeenCalledTimes(2)
  })
})
