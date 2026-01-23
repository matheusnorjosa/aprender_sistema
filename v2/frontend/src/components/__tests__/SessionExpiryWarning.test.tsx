/**
 * Tests: SessionExpiryWarning Component (CP5 - Issue #164)
 *
 * Cobertura:
 * - Renderização condicional (showWarning)
 * - Botões de ação (renovar, logout)
 * - Callbacks
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, test, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import SessionExpiryWarning from '../SessionExpiryWarning'

// Mock useNavigate
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

describe('SessionExpiryWarning', () => {
  const defaultProps = {
    showWarning: true,
    timeLeft: 180, // 3 minutos
    renewSession: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  // ============================================================================
  // TESTES DE RENDERIZAÇÃO
  // ============================================================================

  test('não deve renderizar modal quando showWarning é false', () => {
    render(
      <MemoryRouter>
        <SessionExpiryWarning {...defaultProps} showWarning={false} />
      </MemoryRouter>
    )

    expect(screen.queryByText('Sua sessão está prestes a expirar')).not.toBeInTheDocument()
  })

  test('deve renderizar modal quando showWarning é true', () => {
    render(
      <MemoryRouter>
        <SessionExpiryWarning {...defaultProps} />
      </MemoryRouter>
    )

    expect(screen.getByText('Sua sessão está prestes a expirar')).toBeInTheDocument()
    expect(screen.getByText('Tempo restante:')).toBeInTheDocument()
    expect(screen.getByText('Deseja continuar conectado?')).toBeInTheDocument()
  })

  test('deve exibir botões de ação', () => {
    render(
      <MemoryRouter>
        <SessionExpiryWarning {...defaultProps} />
      </MemoryRouter>
    )

    expect(screen.getByRole('button', { name: /Continuar logado/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Sair agora/i })).toBeInTheDocument()
  })

  // ============================================================================
  // TESTES DE INTERAÇÃO
  // ============================================================================

  test('deve chamar renewSession ao clicar "Continuar logado"', async () => {
    const mockRenewSession = vi.fn().mockResolvedValue(true)

    render(
      <MemoryRouter>
        <SessionExpiryWarning {...defaultProps} renewSession={mockRenewSession} />
      </MemoryRouter>
    )

    const renewButton = screen.getByRole('button', { name: /Continuar logado/i })
    fireEvent.click(renewButton)

    await waitFor(() => {
      expect(mockRenewSession).toHaveBeenCalledTimes(1)
    })
  })

  test('deve navegar para /login se renewSession falhar', async () => {
    const mockRenewSession = vi.fn().mockResolvedValue(false)

    render(
      <MemoryRouter>
        <SessionExpiryWarning {...defaultProps} renewSession={mockRenewSession} />
      </MemoryRouter>
    )

    const renewButton = screen.getByRole('button', { name: /Continuar logado/i })
    fireEvent.click(renewButton)

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/login')
    })
  })

  test('deve navegar para /logout ao clicar "Sair agora"', () => {
    render(
      <MemoryRouter>
        <SessionExpiryWarning {...defaultProps} />
      </MemoryRouter>
    )

    const logoutButton = screen.getByRole('button', { name: /Sair agora/i })
    fireEvent.click(logoutButton)

    expect(mockNavigate).toHaveBeenCalledWith('/logout')
  })

  // ============================================================================
  // TESTES DE ACESSIBILIDADE
  // ============================================================================

  test('modal não deve ser fechável pelo usuário (maskClosable=false)', () => {
    render(
      <MemoryRouter>
        <SessionExpiryWarning {...defaultProps} />
      </MemoryRouter>
    )

    // Modal está presente e não tem botão de fechar (closable=false)
    expect(screen.getByText('Sua sessão está prestes a expirar')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /close/i })).not.toBeInTheDocument()
  })
})
