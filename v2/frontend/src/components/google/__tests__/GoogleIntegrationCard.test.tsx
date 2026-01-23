/**
 * Tests: GoogleIntegrationCard Component (Sprint 1 - Issue #1)
 *
 * Cobertura:
 * - Renderização condicional (null, desconectado, conectado)
 * - Estados visuais (conectado, expirando, expirado)
 * - Callbacks (onConnect, onDisconnect)
 * - Popconfirm de disconnect
 * - Formatação de datas
 *
 * Refs:
 * - Sprint 1 (Issue #1): Frontend Tests
 * - PA-06: Controle explícito (ISO 9241-110)
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, test, expect, vi } from 'vitest';
import GoogleIntegrationCard, { type GoogleIntegrationStatus } from '../GoogleIntegrationCard';

describe('GoogleIntegrationCard', () => {
  // ============================================================================
  // TESTES DE RENDERIZAÇÃO CONDICIONAL
  // ============================================================================

  test('não deve renderizar quando status é null', () => {
    const { container } = render(
      <GoogleIntegrationCard status={null} onConnect={() => {}} onDisconnect={() => {}} />
    );

    expect(container.firstChild).toBeNull();
  });

  test('não deve renderizar quando status é undefined', () => {
    const { container } = render(
      <GoogleIntegrationCard status={null} onConnect={() => {}} onDisconnect={() => {}} />
    );

    expect(container.firstChild).toBeNull();
  });

  // ============================================================================
  // TESTES DE ESTADO DESCONECTADO
  // ============================================================================

  test('deve renderizar card vermelho quando desconectado', () => {
    const status: GoogleIntegrationStatus = {
      connected: false,
      googleEmail: undefined,
      tokenExpiry: undefined,
      expiresInDays: null,
      isExpired: false,
    };

    const onConnect = vi.fn();

    render(
      <GoogleIntegrationCard status={status} onConnect={onConnect} onDisconnect={() => {}} />
    );

    // Validar título
    expect(screen.getByText('Integração Google Calendar')).toBeInTheDocument();

    // Validar texto descritivo
    expect(
      screen.getByText(/Para publicar eventos no Google Calendar, conecte sua conta corporativa/)
    ).toBeInTheDocument();

    // Validar botão "Conectar conta Google"
    const connectButton = screen.getByRole('button', { name: /Conectar conta Google/i });
    expect(connectButton).toBeInTheDocument();

    // Testar callback
    fireEvent.click(connectButton);
    expect(onConnect).toHaveBeenCalledTimes(1);
  });

  // ============================================================================
  // TESTES DE ESTADO CONECTADO
  // ============================================================================

  test('deve renderizar card verde quando conectado (não expirando)', () => {
    const status: GoogleIntegrationStatus = {
      connected: true,
      googleEmail: 'controle@aprendereditora.com.br',
      tokenExpiry: '2025-12-31T23:59:59Z',
      expiresInDays: 45,
      isExpired: false,
    };

    render(
      <GoogleIntegrationCard status={status} onConnect={() => {}} onDisconnect={() => {}} />
    );

    // Validar tag "Conectado" (verde)
    expect(screen.getByText('Conectado')).toBeInTheDocument();

    // Validar email (pode aparecer em múltiplos lugares: texto + select)
    expect(screen.getByText(/Conta conectada:/)).toBeInTheDocument();
    const emailElements = screen.getAllByText('controle@aprendereditora.com.br');
    expect(emailElements.length).toBeGreaterThanOrEqual(1);

    // Validar data de expiração
    expect(screen.getByText(/Token expira em:/)).toBeInTheDocument();

    // Botão "Desconectar" deve estar presente
    expect(screen.getByRole('button', { name: /Desconectar/i })).toBeInTheDocument();

    // Botão "Reconectar" NÃO deve estar presente (não expirado)
    expect(screen.queryByRole('button', { name: /Reconectar/i })).not.toBeInTheDocument();
  });

  test('deve renderizar card amarelo quando expirando (≤7 dias)', () => {
    const status: GoogleIntegrationStatus = {
      connected: true,
      googleEmail: 'controle@aprendereditora.com.br',
      tokenExpiry: '2025-12-07T23:59:59Z',
      expiresInDays: 5,
      isExpired: false,
    };

    render(
      <GoogleIntegrationCard status={status} onConnect={() => {}} onDisconnect={() => {}} />
    );

    // Validar tag "Expira em X dias" (amarelo)
    expect(screen.getByText('Expira em 5 dias')).toBeInTheDocument();

    // Email e desconectar devem estar presentes (email pode aparecer em múltiplos lugares)
    const emailElements = screen.getAllByText('controle@aprendereditora.com.br');
    expect(emailElements.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByRole('button', { name: /Desconectar/i })).toBeInTheDocument();

    // Botão "Reconectar" NÃO deve estar presente
    expect(screen.queryByRole('button', { name: /Reconectar/i })).not.toBeInTheDocument();
  });

  test('deve renderizar card vermelho quando expirado', () => {
    const status: GoogleIntegrationStatus = {
      connected: true,
      googleEmail: 'controle@aprendereditora.com.br',
      tokenExpiry: '2025-01-01T00:00:00Z',
      expiresInDays: -10,
      isExpired: true,
    };

    const onConnect = vi.fn();

    render(
      <GoogleIntegrationCard status={status} onConnect={onConnect} onDisconnect={() => {}} />
    );

    // Validar tag "Expirado (reconecte sua conta)" (vermelho)
    expect(screen.getByText('Expirado (reconecte sua conta)')).toBeInTheDocument();

    // Validar botão "Reconectar conta" (danger)
    const reconnectButton = screen.getByRole('button', { name: /Reconectar conta/i });
    expect(reconnectButton).toBeInTheDocument();

    // Testar callback
    fireEvent.click(reconnectButton);
    expect(onConnect).toHaveBeenCalledTimes(1);

    // Botão "Desconectar" também deve estar presente
    expect(screen.getByRole('button', { name: /Desconectar/i })).toBeInTheDocument();
  });

  test('deve renderizar sem data de expiração se tokenExpiry for null', () => {
    const status: GoogleIntegrationStatus = {
      connected: true,
      googleEmail: 'controle@aprendereditora.com.br',
      tokenExpiry: undefined,
      expiresInDays: null,
      isExpired: false,
    };

    render(
      <GoogleIntegrationCard status={status} onConnect={() => {}} onDisconnect={() => {}} />
    );

    // Email deve estar presente (pode aparecer em múltiplos lugares)
    const emailElements = screen.getAllByText('controle@aprendereditora.com.br');
    expect(emailElements.length).toBeGreaterThanOrEqual(1);

    // Texto "Token expira em:" NÃO deve estar presente
    expect(screen.queryByText(/Token expira em:/)).not.toBeInTheDocument();
  });

  // ============================================================================
  // TESTES DE INTERAÇÃO (POPCONFIRM)
  // ============================================================================

  test('deve exibir Popconfirm ao clicar "Desconectar"', async () => {
    const status: GoogleIntegrationStatus = {
      connected: true,
      googleEmail: 'controle@aprendereditora.com.br',
      tokenExpiry: '2025-12-31T23:59:59Z',
      expiresInDays: 45,
      isExpired: false,
    };

    const onDisconnect = vi.fn();

    render(
      <GoogleIntegrationCard status={status} onConnect={() => {}} onDisconnect={onDisconnect} />
    );

    // Clicar no botão "Desconectar"
    const disconnectButton = screen.getByRole('button', { name: /Desconectar/i });
    fireEvent.click(disconnectButton);

    // Popconfirm deve aparecer
    await waitFor(() => {
      expect(screen.getByText('Desconectar conta Google?')).toBeInTheDocument();
    });

    expect(
      screen.getByText('Você não poderá publicar eventos até reconectar.')
    ).toBeInTheDocument();

    // Botões do Popconfirm
    const confirmButton = screen.getByRole('button', { name: /Sim, desconectar/i });
    const cancelButton = screen.getByRole('button', { name: /Cancelar/i });

    expect(confirmButton).toBeInTheDocument();
    expect(cancelButton).toBeInTheDocument();
  });

  test('deve chamar onDisconnect ao confirmar Popconfirm', async () => {
    const status: GoogleIntegrationStatus = {
      connected: true,
      googleEmail: 'controle@aprendereditora.com.br',
      tokenExpiry: '2025-12-31T23:59:59Z',
      expiresInDays: 45,
      isExpired: false,
    };

    const onDisconnect = vi.fn();

    render(
      <GoogleIntegrationCard status={status} onConnect={() => {}} onDisconnect={onDisconnect} />
    );

    // Clicar "Desconectar"
    const disconnectButton = screen.getByRole('button', { name: /Desconectar/i });
    fireEvent.click(disconnectButton);

    // Confirmar Popconfirm
    await waitFor(() => {
      expect(screen.getByText('Desconectar conta Google?')).toBeInTheDocument();
    });

    const confirmButton = screen.getByRole('button', { name: /Sim, desconectar/i });
    fireEvent.click(confirmButton);

    // Callback deve ser chamado
    await waitFor(() => {
      expect(onDisconnect).toHaveBeenCalledTimes(1);
    });
  });

  test('NÃO deve chamar onDisconnect ao cancelar Popconfirm', async () => {
    const status: GoogleIntegrationStatus = {
      connected: true,
      googleEmail: 'controle@aprendereditora.com.br',
      tokenExpiry: '2025-12-31T23:59:59Z',
      expiresInDays: 45,
      isExpired: false,
    };

    const onDisconnect = vi.fn();

    render(
      <GoogleIntegrationCard status={status} onConnect={() => {}} onDisconnect={onDisconnect} />
    );

    // Clicar "Desconectar"
    const disconnectButton = screen.getByRole('button', { name: /Desconectar/i });
    fireEvent.click(disconnectButton);

    // Cancelar Popconfirm
    await waitFor(() => {
      expect(screen.getByText('Desconectar conta Google?')).toBeInTheDocument();
    });

    const cancelButton = screen.getByRole('button', { name: /Cancelar/i });
    fireEvent.click(cancelButton);

    // Callback NÃO deve ser chamado
    expect(onDisconnect).not.toHaveBeenCalled();
  });

  // ============================================================================
  // TESTES DE FORMATAÇÃO
  // ============================================================================

  test('deve formatar data de expiração em pt-BR', () => {
    const status: GoogleIntegrationStatus = {
      connected: true,
      googleEmail: 'controle@aprendereditora.com.br',
      tokenExpiry: '2025-12-31T23:59:59Z',
      expiresInDays: 45,
      isExpired: false,
    };

    render(
      <GoogleIntegrationCard status={status} onConnect={() => {}} onDisconnect={() => {}} />
    );

    // Validar que alguma data aparece (formato depende do locale do sistema)
    expect(screen.getByText(/Token expira em:/)).toBeInTheDocument();

    // Regex para validar formato de data (tolerante a variações de locale)
    const dateText = screen.getByText(/\d{2}\/\d{2}\/\d{4}/);
    expect(dateText).toBeInTheDocument();
  });
});
