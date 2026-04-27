/**
 * Tests: RequirePolicy wrapper (Epic 3, Issue #1228).
 *
 * Renderiza children se o user possui a policy/derived flag, senão
 * renderiza o fallback (default: <Forbidden />). Componente puro:
 * recebe `policies` como prop, não busca do backend.
 */

import { describe, test, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import { RequirePolicy } from '../RequirePolicy';

function renderWithRouter(ui: React.ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

function ProtectedContent() {
  return <div data-testid="protected-content">Conteúdo protegido</div>;
}

describe('<RequirePolicy>', () => {
  test('renders children when policy is in user policies', () => {
    renderWithRouter(
      <RequirePolicy policy="view_compras_dashboard" policies={['view_compras_dashboard']}>
        <ProtectedContent />
      </RequirePolicy>
    );
    expect(screen.getByTestId('protected-content')).toBeInTheDocument();
  });

  test('renders default Forbidden (403) when policy is missing', () => {
    renderWithRouter(
      <RequirePolicy policy="view_compras_dashboard" policies={['use_gcal']}>
        <ProtectedContent />
      </RequirePolicy>
    );
    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
    // Ant Design Result com status 403
    expect(screen.getByText(/recurso indisponível/i)).toBeInTheDocument();
    // OWASP guard: NUNCA mencionar permissão/role na mensagem default
    expect(screen.queryByText(/permissão/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/403/)).not.toBeInTheDocument();
  });

  test('renders custom fallback when provided', () => {
    renderWithRouter(
      <RequirePolicy
        policy="view_compras_dashboard"
        policies={[]}
        fallback={<div data-testid="custom-fallback">Custom 403</div>}
      >
        <ProtectedContent />
      </RequirePolicy>
    );
    expect(screen.getByTestId('custom-fallback')).toBeInTheDocument();
    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
  });

  test('renders children when allow=true (escape hatch para flags compostas)', () => {
    // Permite passar derived flag (ex: canAccessApprovals) em vez de policy literal.
    renderWithRouter(
      <RequirePolicy allow={true} policies={[]}>
        <ProtectedContent />
      </RequirePolicy>
    );
    expect(screen.getByTestId('protected-content')).toBeInTheDocument();
  });

  test('renders fallback when allow=false', () => {
    renderWithRouter(
      <RequirePolicy allow={false} policies={[]}>
        <ProtectedContent />
      </RequirePolicy>
    );
    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
    expect(screen.getByText(/recurso indisponível/i)).toBeInTheDocument();
    // OWASP guard: NUNCA mencionar permissão/role na mensagem default
    expect(screen.queryByText(/permissão/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/403/)).not.toBeInTheDocument();
  });

  test('renders fallback during loading=true (avoids flash of forbidden)', () => {
    // Enquanto policies ainda não chegaram do backend, NÃO mostra Forbidden —
    // mostra loader (sem children), pra evitar flash de "Sem permissão".
    renderWithRouter(
      <RequirePolicy
        policy="view_compras_dashboard"
        policies={[]}
        loading={true}
        loadingFallback={<div data-testid="loading">carregando…</div>}
      >
        <ProtectedContent />
      </RequirePolicy>
    );
    expect(screen.getByTestId('loading')).toBeInTheDocument();
    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
    expect(screen.queryByText(/recurso indisponível/i)).not.toBeInTheDocument();
  });
});
