/**
 * Tests: RemoteSelect Component
 *
 * Cobertura:
 * - Renderização inicial
 * - Estado disabled
 * - Props passadas corretamente
 */

import { render, screen, waitFor } from '@testing-library/react'
import { describe, test, expect, vi, beforeEach } from 'vitest'
import RemoteSelect, { type OptionItem } from '../RemoteSelect'

interface TestItem extends OptionItem {
  nome: string;
}

describe('RemoteSelect', () => {
  const mockFetchOptions = vi.fn()
  const mockRenderLabel = (item: TestItem) => item.nome

  const mockOptions: TestItem[] = [
    { id: 1, nome: 'Fortaleza' },
    { id: 2, nome: 'Sobral' },
    { id: 3, nome: 'Juazeiro do Norte' },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    mockFetchOptions.mockResolvedValue(mockOptions)
  })

  // ============================================================================
  // TESTES DE RENDERIZAÇÃO
  // ============================================================================

  test('deve renderizar com placeholder', async () => {
    render(
      <RemoteSelect
        fetchOptions={mockFetchOptions}
        renderLabel={mockRenderLabel}
        placeholder="Selecione um município"
      />
    )

    await waitFor(() => {
      expect(mockFetchOptions).toHaveBeenCalled()
    })

    expect(screen.getByText('Selecione um município')).toBeInTheDocument()
  })

  test('deve renderizar com placeholder padrão', async () => {
    render(
      <RemoteSelect
        fetchOptions={mockFetchOptions}
        renderLabel={mockRenderLabel}
      />
    )

    await waitFor(() => {
      expect(mockFetchOptions).toHaveBeenCalled()
    })

    expect(screen.getByText('Buscar...')).toBeInTheDocument()
  })

  // ============================================================================
  // TESTES DE CARREGAMENTO INICIAL
  // ============================================================================

  test('deve carregar opções no mount', async () => {
    render(
      <RemoteSelect
        fetchOptions={mockFetchOptions}
        renderLabel={mockRenderLabel}
      />
    )

    await waitFor(() => {
      expect(mockFetchOptions).toHaveBeenCalledWith({ search: '' })
    })
  })

  test('não deve carregar opções quando disabled', () => {
    render(
      <RemoteSelect
        fetchOptions={mockFetchOptions}
        renderLabel={mockRenderLabel}
        disabled={true}
      />
    )

    // fetchOptions não deve ser chamado quando disabled
    expect(mockFetchOptions).not.toHaveBeenCalled()
  })

  // ============================================================================
  // TESTES DE ESTADO DISABLED
  // ============================================================================

  test('deve estar desabilitado quando disabled=true', () => {
    render(
      <RemoteSelect
        fetchOptions={mockFetchOptions}
        renderLabel={mockRenderLabel}
        disabled={true}
      />
    )

    // O select do Ant Design adiciona classe ant-select-disabled
    const selectWrapper = document.querySelector('.ant-select-disabled')
    expect(selectWrapper).toBeInTheDocument()
  })

  // ============================================================================
  // TESTES DE ERRO
  // ============================================================================

  test('deve lidar com erro no fetchOptions graciosamente', async () => {
    const failingFetch = vi.fn().mockRejectedValue(new Error('Network error'))

    render(
      <RemoteSelect
        fetchOptions={failingFetch}
        renderLabel={mockRenderLabel}
      />
    )

    await waitFor(() => {
      expect(failingFetch).toHaveBeenCalled()
    })

    // Componente não deve quebrar
    expect(screen.getByText('Buscar...')).toBeInTheDocument()
  })
})
