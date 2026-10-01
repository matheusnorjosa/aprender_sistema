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
import { MemoryRouter, useLocation } from 'react-router'
import SessionExpiryWarning from '../SessionExpiryWarning'

function OndeEstou() {
  return <span data-testid="rota">{useLocation().pathname}</span>
}

describe('SessionExpiryWarning', () => {
  const defaultProps = {
    showWarning: true,
    timeLeft: 180, // 3 minutos
    renewSession: vi.fn(),
    renewError: null,
    onLogout: vi.fn(),
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

  // Auditoria UX 30/09 (ALTA): /login e /logout não são rotas — a tela ficava em branco
  // e a sessão continuava aberta. Sessão expirada é tratada pelo useSessionMonitor
  // (logout real do App); o aviso não navega para rota nenhuma.
  test('renewSession falho não navega para rota inexistente', async () => {
    const mockRenewSession = vi.fn().mockResolvedValue(false)

    render(
      <MemoryRouter initialEntries={['/dat/registros']}>
        <SessionExpiryWarning {...defaultProps} renewSession={mockRenewSession} />
        <OndeEstou />
      </MemoryRouter>
    )

    fireEvent.click(screen.getByRole('button', { name: /Continuar logado/i }))

    await waitFor(() => expect(mockRenewSession).toHaveBeenCalledTimes(1))
    expect(screen.getByTestId('rota')).toHaveTextContent('/dat/registros')
  })

  // Auditoria UX 30/09, rodada 2 (MÉDIA): "Continuar logado" com erro de rede ou 5xx era
  // clique mudo. O botão fica em loading enquanto renova e o motivo aparece no aviso.
  test('"Continuar logado" fica em loading enquanto renova', async () => {
    let terminar: (ok: boolean) => void = () => {}
    const renewSession = vi.fn(() => new Promise<boolean>((resolve) => { terminar = resolve }))

    render(
      <MemoryRouter>
        <SessionExpiryWarning {...defaultProps} renewSession={renewSession} />
      </MemoryRouter>
    )

    const botao = screen.getByRole('button', { name: /Continuar logado/i })
    fireEvent.click(botao)

    await waitFor(() => expect(botao).toHaveClass('ant-btn-loading'))
    terminar(false)
    await waitFor(() => expect(botao).not.toHaveClass('ant-btn-loading'))
  })

  test('renovação que falhou mostra o motivo e o aviso continua aberto', () => {
    render(
      <MemoryRouter>
        <SessionExpiryWarning {...defaultProps} renewError="Sem conexão com o servidor." />
      </MemoryRouter>
    )

    const erro = screen.getByRole('alert')
    expect(erro).toHaveTextContent('Não foi possível renovar a sessão')
    expect(erro).toHaveTextContent('Sem conexão com o servidor.')
    expect(screen.getByRole('button', { name: /Continuar logado/i })).toBeInTheDocument()
  })

  test('"Sair agora" usa o logout real do App (onLogout), sem navegar para /logout', () => {
    const onLogout = vi.fn()
    render(
      <MemoryRouter initialEntries={['/dat/registros']}>
        <SessionExpiryWarning {...defaultProps} onLogout={onLogout} />
        <OndeEstou />
      </MemoryRouter>
    )

    fireEvent.click(screen.getByRole('button', { name: /Sair agora/i }))

    expect(onLogout).toHaveBeenCalledTimes(1)
    expect(screen.getByTestId('rota')).toHaveTextContent('/dat/registros')
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
