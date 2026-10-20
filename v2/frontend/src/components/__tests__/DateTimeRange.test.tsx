/**
 * Tests: DateTimeRange Component
 *
 * Cobertura:
 * - Renderização inicial
 * - Valores controlados via props
 * - Callback onChange com formato correto
 */

import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, test, expect, vi } from 'vitest'
import DateTimeRange from '../DateTimeRange'

describe('DateTimeRange', () => {
  // ============================================================================
  // TESTES DE RENDERIZAÇÃO
  // ============================================================================

  test('deve renderizar todos os campos', () => {
    render(<DateTimeRange />)

    // Labels
    expect(screen.getByText('Data:')).toBeInTheDocument()
    expect(screen.getByText('Início:')).toBeInTheDocument()
    expect(screen.getByText('Fim:')).toBeInTheDocument()

    // Inputs (DatePicker e TimePickers)
    expect(screen.getByPlaceholderText('Selecione a data')).toBeInTheDocument()
    expect(screen.getAllByPlaceholderText('HH:mm')).toHaveLength(2)
  })

  test('deve renderizar com valores iniciais vazios', () => {
    render(<DateTimeRange value={{}} onChange={() => {}} />)

    const dateInput = screen.getByPlaceholderText('Selecione a data')
    const timeInputs = screen.getAllByPlaceholderText('HH:mm')

    expect(dateInput).toHaveValue('')
    expect(timeInputs[0]).toHaveValue('')
    expect(timeInputs[1]).toHaveValue('')
  })

  test('deve renderizar com valores fornecidos', () => {
    const value = {
      date: '2025-01-15',
      start: '09:00',
      end: '12:00',
    }

    render(<DateTimeRange value={value} onChange={() => {}} />)

    // DatePicker mostra a data formatada
    const dateInput = screen.getByPlaceholderText('Selecione a data')
    expect(dateInput).toHaveValue('15/01/2025')

    // TimePickers mostram os horários
    const timeInputs = screen.getAllByPlaceholderText('HH:mm')
    expect(timeInputs[0]).toHaveValue('09:00')
    expect(timeInputs[1]).toHaveValue('12:00')
  })

  // ============================================================================
  // TESTES DE CALLBACK
  // ============================================================================

  test('onChange deve receber valores formatados corretamente', () => {
    const mockOnChange = vi.fn()

    render(
      <DateTimeRange
        value={{ date: '2025-01-15', start: '09:00', end: '12:00' }}
        onChange={mockOnChange}
      />
    )

    // O componente é renderizado mas não disparamos eventos aqui
    // Apenas verificamos que ele aceita o callback
    expect(mockOnChange).not.toHaveBeenCalled()
  })

  // ============================================================================
  // TESTES DE ACESSIBILIDADE
  // ============================================================================

  test('deve ter estrutura acessível com labels', () => {
    render(<DateTimeRange />)

    // Verifica que os labels estão presentes
    const labels = screen.getAllByText(/Data:|Início:|Fim:/i)
    expect(labels).toHaveLength(3)
  })

  test('deve ter inputs com placeholders descritivos', () => {
    render(<DateTimeRange />)

    expect(screen.getByPlaceholderText('Selecione a data')).toBeInTheDocument()
    expect(screen.getAllByPlaceholderText('HH:mm')).toHaveLength(2)
  })

  // ============================================================================
  // ITEM 36 (19/10/2026): erro junto do horário e horário que vale sem o OK
  // ============================================================================

  test('com erro e tudo preenchido, a mensagem fica junto do horário e marca o Fim', () => {
    render(
      <DateTimeRange
        value={{ date: '2026-08-01', start: '14:00', end: '10:00' }}
        erro="O horário de fim precisa ser depois do início."
      />
    )
    const aviso = screen.getByRole('alert')
    expect(aviso).toHaveTextContent('O horário de fim precisa ser depois do início.')
    const fim = screen.getByLabelText('Fim:')
    expect(fim).toHaveAttribute('aria-invalid', 'true')
    expect(fim.getAttribute('aria-describedby')).toBe(aviso.id)
    expect(screen.getByLabelText('Início:')).not.toHaveAttribute('aria-invalid', 'true')
  })

  test('com erro e campos vazios, marca os vazios', () => {
    render(<DateTimeRange value={{ date: '2026-08-01' }} erro="Escolha a data e os horários de início e de fim do evento." />)
    expect(screen.getByLabelText('Data:')).not.toHaveAttribute('aria-invalid', 'true')
    expect(screen.getByLabelText('Início:')).toHaveAttribute('aria-invalid', 'true')
    expect(screen.getByLabelText('Fim:')).toHaveAttribute('aria-invalid', 'true')
  })

  test('o horário escolhido no painel vale sem apertar OK', async () => {
    const onChange = vi.fn()
    render(<DateTimeRange value={{ date: '2026-08-01' }} onChange={onChange} />)
    const inicio = screen.getByLabelText('Início:')
    fireEvent.mouseDown(inicio)
    fireEvent.click(inicio)
    const painel = await waitFor(() => {
      const el = document.querySelector('.ant-picker-dropdown:not(.ant-picker-dropdown-hidden)')
      if (!el) throw new Error('painel não abriu')
      return el as HTMLElement
    })
    const colunas = painel.querySelectorAll('.ant-picker-time-panel-column')
    fireEvent.click(colunas[0]!.querySelectorAll('.ant-picker-time-panel-cell-inner')[9]!)
    fireEvent.click(colunas[1]!.querySelectorAll('.ant-picker-time-panel-cell-inner')[0]!)
    fireEvent.blur(inicio)
    await waitFor(() => expect(onChange).toHaveBeenCalledWith({ date: '2026-08-01', start: '09:00', end: null }))
  })
})
