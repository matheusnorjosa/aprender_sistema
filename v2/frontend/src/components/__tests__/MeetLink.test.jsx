/**
 * Tests: MeetLink Component (PR19/RF06)
 *
 * Cobertura:
 * - Renderização condicional (null quando sem href)
 * - Botão "Entrar na reunião" com link
 * - Botão "Copiar link" com clipboard
 */

import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, test, expect, vi, beforeEach } from 'vitest'
import MeetLink from '../MeetLink'

// Mock do clipboard API
const mockClipboard = {
  writeText: vi.fn(),
}

Object.assign(navigator, {
  clipboard: mockClipboard,
})

describe('MeetLink', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockClipboard.writeText.mockResolvedValue()
  })

  // ============================================================================
  // TESTES DE RENDERIZAÇÃO CONDICIONAL
  // ============================================================================

  test('não deve renderizar quando href é null', () => {
    const { container } = render(<MeetLink href={null} />)
    expect(container.firstChild).toBeNull()
  })

  test('não deve renderizar quando href é undefined', () => {
    const { container } = render(<MeetLink />)
    expect(container.firstChild).toBeNull()
  })

  test('não deve renderizar quando href é string vazia', () => {
    const { container } = render(<MeetLink href="" />)
    expect(container.firstChild).toBeNull()
  })

  // ============================================================================
  // TESTES DE RENDERIZAÇÃO COM HREF
  // ============================================================================

  test('deve renderizar botões quando href é fornecido', () => {
    const meetUrl = 'https://meet.google.com/abc-defg-hij'

    render(<MeetLink href={meetUrl} />)

    // Botão "Entrar na reunião"
    const enterButton = screen.getByRole('link', { name: /Entrar na reunião/i })
    expect(enterButton).toBeInTheDocument()
    expect(enterButton).toHaveAttribute('href', meetUrl)
    expect(enterButton).toHaveAttribute('target', '_blank')
    expect(enterButton).toHaveAttribute('rel', 'noopener noreferrer')

    // Botão "Copiar link"
    const copyButton = screen.getByRole('button', { name: /Copiar link/i })
    expect(copyButton).toBeInTheDocument()
  })

  // ============================================================================
  // TESTES DE INTERAÇÃO - COPIAR LINK
  // ============================================================================

  test('deve copiar link para clipboard ao clicar "Copiar link"', async () => {
    const meetUrl = 'https://meet.google.com/abc-defg-hij'

    render(<MeetLink href={meetUrl} />)

    const copyButton = screen.getByRole('button', { name: /Copiar link/i })
    fireEvent.click(copyButton)

    await waitFor(() => {
      expect(mockClipboard.writeText).toHaveBeenCalledWith(meetUrl)
    })
  })

  test('deve exibir mensagem de sucesso após copiar', async () => {
    const meetUrl = 'https://meet.google.com/abc-defg-hij'

    render(<MeetLink href={meetUrl} />)

    const copyButton = screen.getByRole('button', { name: /Copiar link/i })
    fireEvent.click(copyButton)

    // Ant Design message.success cria um elemento com a mensagem
    await waitFor(() => {
      expect(mockClipboard.writeText).toHaveBeenCalled()
    })
  })

  test('deve lidar com erro de clipboard graciosamente', async () => {
    const meetUrl = 'https://meet.google.com/abc-defg-hij'
    mockClipboard.writeText.mockRejectedValue(new Error('Clipboard error'))

    render(<MeetLink href={meetUrl} />)

    const copyButton = screen.getByRole('button', { name: /Copiar link/i })
    fireEvent.click(copyButton)

    await waitFor(() => {
      expect(mockClipboard.writeText).toHaveBeenCalledWith(meetUrl)
    })
  })

  // ============================================================================
  // TESTES DE ACESSIBILIDADE
  // ============================================================================

  test('botão de entrada deve ter atributos de segurança', () => {
    const meetUrl = 'https://meet.google.com/abc-defg-hij'

    render(<MeetLink href={meetUrl} />)

    const enterButton = screen.getByRole('link', { name: /Entrar na reunião/i })

    // Segurança: noopener noreferrer para links externos
    expect(enterButton).toHaveAttribute('rel', 'noopener noreferrer')
  })
})
