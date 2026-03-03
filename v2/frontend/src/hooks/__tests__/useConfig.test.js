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

const { getSystemConfigMock, updateSystemConfigMock } = vi.hoisted(() => ({
  getSystemConfigMock: vi.fn(),
  updateSystemConfigMock: vi.fn(),
}))

vi.mock('../../api/systemConfig', () => ({
  getSystemConfig: getSystemConfigMock,
  updateSystemConfig: updateSystemConfigMock,
}))

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
    getSystemConfigMock.mockResolvedValueOnce(mockConfigData)

    const { result } = renderHook(() => useConfig())

    expect(result.current.loading).toBe(true)
  })

  test('deve carregar config com sucesso', async () => {
    getSystemConfigMock.mockResolvedValueOnce(mockConfigData)

    const { result } = renderHook(() => useConfig())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.config).toEqual(mockConfigData)
    expect(getSystemConfigMock).toHaveBeenCalledTimes(1)
  })

  test('deve lidar com erro de carregamento', async () => {
    getSystemConfigMock.mockRejectedValueOnce(new Error('HTTP 500: Internal Server Error'))

    const { result } = renderHook(() => useConfig())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.config).toBeNull()
  })

  test('deve lidar com erro de rede', async () => {
    getSystemConfigMock.mockRejectedValueOnce(new Error('Network error'))

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
    getSystemConfigMock.mockResolvedValueOnce(mockConfigData)

    const { result } = renderHook(() => useConfig())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // Mock para saveConfig
    const updatedConfig = { ...mockConfigData, buffer_deslocamento_minutos: 90 }
    updateSystemConfigMock.mockResolvedValueOnce(updatedConfig)

    let saveResult
    await act(async () => {
      saveResult = await result.current.saveConfig(updatedConfig)
    })

    expect(saveResult).toBe(true)
    expect(result.current.config).toEqual(updatedConfig)
    expect(updateSystemConfigMock).toHaveBeenCalledWith(updatedConfig)
  })

  test('saveConfig deve retornar false em erro', async () => {
    // Mock para load inicial
    getSystemConfigMock.mockResolvedValueOnce(mockConfigData)

    const { result } = renderHook(() => useConfig())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // Mock para saveConfig com erro
    updateSystemConfigMock.mockRejectedValueOnce({
      response: {
        data: { buffer_deslocamento_minutos: ['Valor inválido'] },
      },
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
    getSystemConfigMock.mockResolvedValueOnce(mockConfigData)

    const { result } = renderHook(() => useConfig())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // Mock para reload
    const updatedConfig = { ...mockConfigData, buffer_deslocamento_minutos: 120 }
    getSystemConfigMock.mockResolvedValueOnce(updatedConfig)

    await act(async () => {
      await result.current.reload()
    })

    expect(result.current.config).toEqual(updatedConfig)
    expect(getSystemConfigMock).toHaveBeenCalledTimes(2)
  })
})
