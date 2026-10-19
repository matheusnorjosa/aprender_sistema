/**
 * Tests: ComboBox Component (PR16)
 *
 * Cobertura:
 * - Renderização inicial
 * - Carregamento de opções
 * - Seleção de item
 */

import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, test, expect, vi, beforeEach } from 'vitest'
import { Button, Form } from 'antd'
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

  // ============================================================================
  // ITEM 36 (19/10/2026): rótulo, texto solto e falha ao carregar
  // ============================================================================

  test('dentro do Form.Item, o rótulo nomeia o campo e o erro chega ao leitor de tela', async () => {
    render(
      <Form>
        <Form.Item label="Município" name="municipio" rules={[{ required: true, message: 'Selecione um município' }]}>
          <ComboBox lookupFunction={mockLookupFunction} />
        </Form.Item>
        <Button htmlType="submit">Enviar</Button>
      </Form>
    )
    const campo = screen.getByRole('combobox', { name: 'Município' })
    fireEvent.click(screen.getByRole('button', { name: 'Enviar' }))
    const erro = await screen.findByText('Selecione um município')
    await waitFor(() => expect(campo).toHaveAttribute('aria-invalid', 'true'))
    const descritores = (campo.getAttribute('aria-describedby') ?? '').split(' ')
    expect(descritores.some((id) => id && document.getElementById(id)?.contains(erro))).toBe(true)
  })

  test('texto digitado sem escolher uma opção volta para o valor guardado ao sair do campo', async () => {
    const onChange = vi.fn()
    render(
      <ComboBox lookupFunction={mockLookupFunction} value={{ id: 1, label: 'Fortaleza' }} onChange={onChange} />
    )
    await waitFor(() => expect(mockLookupFunction).toHaveBeenCalled())
    const campo = screen.getByRole('combobox')
    fireEvent.change(campo, { target: { value: 'Caucaia' } })
    expect(campo).toHaveValue('Caucaia')
    fireEvent.blur(campo)
    await waitFor(() => expect(campo).toHaveValue('Fortaleza'))
    expect(onChange).not.toHaveBeenCalled()
  })

  test('falha ao carregar mostra o motivo e "Tentar de novo", não "Nenhum resultado"', async () => {
    const lookup = vi.fn().mockRejectedValueOnce(new Error('Servidor indisponível.')).mockResolvedValue(mockOptions)
    render(<ComboBox lookupFunction={lookup} oQueCarrega="os municípios" />)
    expect(await screen.findByText('Não foi possível carregar os municípios.')).toBeInTheDocument()
    expect(screen.getByText('Servidor indisponível.')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Tentar de novo: carregar os municípios' }))
    await waitFor(() => expect(screen.queryByText('Não foi possível carregar os municípios.')).not.toBeInTheDocument())
    expect(lookup).toHaveBeenCalledTimes(2)
  })
})
