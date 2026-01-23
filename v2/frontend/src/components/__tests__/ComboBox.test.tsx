/**
 * Tests: ComboBox Component (PR16)
 *
 * Cobertura:
 * - Renderização inicial
 * - Carregamento de opções
 * - Seleção de item
 */

import { render, screen, waitFor } from '@testing-library/react'
import { describe, test, expect, vi, beforeEach } from 'vitest'
import ComboBox from '../ComboBox'

describe('ComboBox', () => {
  const mockOptions = [
    { id: 1, label: 'Fortaleza' },
    { id: 2, label: 'Sobral' },
    { id: 3, label: 'Juazeiro do Norte' },
  ]

  const mockLookupFunction = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    mockLookupFunction.mockResolvedValue(mockOptions)
  })

  // ============================================================================
  // TESTES DE RENDERIZAÇÃO
  // ============================================================================

  test('deve renderizar o componente AutoComplete', async () => {
    render(
      <ComboBox
        lookupFunction={mockLookupFunction}
        placeholder="Selecione um município"
      />
    )

    await waitFor(() => {
      expect(mockLookupFunction).toHaveBeenCalled()
    })

    // AutoComplete renderiza como ant-select
    const selectElement = document.querySelector('.ant-select')
    expect(selectElement).toBeInTheDocument()
  })

  test('deve exibir placeholder', async () => {
    render(
      <ComboBox
        lookupFunction={mockLookupFunction}
        placeholder="Selecione um município"
      />
    )

    await waitFor(() => {
      expect(mockLookupFunction).toHaveBeenCalled()
    })

    // Placeholder aparece em um span
    expect(screen.getByText('Selecione um município')).toBeInTheDocument()
  })

  test('deve carregar opções iniciais no mount', async () => {
    render(<ComboBox lookupFunction={mockLookupFunction} />)

    await waitFor(() => {
      expect(mockLookupFunction).toHaveBeenCalledWith('')
    })
  })

  // ============================================================================
  // TESTES DE VALOR CONTROLADO
  // ============================================================================

  test('deve exibir label do value fornecido', async () => {
    const selectedValue = { id: 1, label: 'Fortaleza' }

    render(
      <ComboBox
        lookupFunction={mockLookupFunction}
        value={selectedValue}
      />
    )

    await waitFor(() => {
      expect(mockLookupFunction).toHaveBeenCalled()
    })

    // O input deve ter o valor "Fortaleza"
    const input = document.querySelector('.ant-select-selection-search-input')
    expect(input).toHaveValue('Fortaleza')
  })

  test('deve limpar input quando value é null', async () => {
    const { rerender } = render(
      <ComboBox
        lookupFunction={mockLookupFunction}
        value={{ id: 1, label: 'Fortaleza' }}
      />
    )

    await waitFor(() => {
      expect(mockLookupFunction).toHaveBeenCalled()
    })

    rerender(
      <ComboBox
        lookupFunction={mockLookupFunction}
        value={null}
      />
    )

    const input = document.querySelector('.ant-select-selection-search-input')
    expect(input).toHaveValue('')
  })

  // ============================================================================
  // TESTES DE ESTADO DISABLED
  // ============================================================================

  test('deve estar desabilitado quando disabled=true', async () => {
    render(
      <ComboBox
        lookupFunction={mockLookupFunction}
        disabled={true}
      />
    )

    // AutoComplete desabilitado tem classe específica
    const selectElement = document.querySelector('.ant-select-disabled')
    expect(selectElement).toBeInTheDocument()
  })

  // ============================================================================
  // TESTES DE ERRO
  // ============================================================================

  test('deve lidar com erro no lookupFunction graciosamente', async () => {
    const failingLookup = vi.fn().mockRejectedValue(new Error('Network error'))

    render(<ComboBox lookupFunction={failingLookup} />)

    await waitFor(() => {
      expect(failingLookup).toHaveBeenCalled()
    })

    // Componente não deve quebrar
    const selectElement = document.querySelector('.ant-select')
    expect(selectElement).toBeInTheDocument()
  })
})
