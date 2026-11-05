/**
 * Página Inicial — números honestos (P#3, B#5, A#17).
 *
 * - Se /api/stats/home/ falha, a tela avisa e oferece "Tentar de novo"; nenhum número vira 0.
 * - `upcoming_events: null` (pessoa sem escopo de eventos) esconde "Eventos Futuros".
 * - O cartão do superusuário fala de usuários e lotação (permissão é código, só leitura).
 */
import { MemoryRouter } from 'react-router';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';

import { getHomeStats } from '../../../api/stats';
import { ATORES_RBAC } from '../../../test/atoresRbac';
import { ComAcesso } from '../../../test/comAcesso';
import HomePage from '../HomePage';

vi.mock('../../../api/stats', () => ({ getHomeStats: vi.fn() }));
vi.mock('../../../utils/logger', () => ({ default: { error: vi.fn() } }));

const mockGetHomeStats = vi.mocked(getHomeStats);
const SUPERUSER = ATORES_RBAC.find((a) => a.ator === 'Superuser')!;
const MSG_ERRO = 'Não foi possível carregar os números da Página Inicial. Os atalhos continuam funcionando.';

function renderSuperuser(): ReturnType<typeof render> {
  return render(
    <MemoryRouter>
      <ComAcesso policies={SUPERUSER.policies} superusuario>
        <HomePage />
      </ComAcesso>
    </MemoryRouter>,
  );
}

function valorDoKpi(titulo: string): string | null | undefined {
  const tituloEl = screen.getByText(titulo, { selector: '.ant-statistic-title' });
  return tituloEl.closest('.ant-statistic')?.querySelector('.ant-statistic-content')?.textContent;
}

describe('Página Inicial — números', { timeout: 20000 }, () => {
  beforeEach(() => {
    mockGetHomeStats.mockReset();
  });

  test('falha ao carregar: avisa, não mostra 0 nem badge e tenta de novo', async () => {
    mockGetHomeStats.mockRejectedValueOnce(new Error('500'));
    const { container } = renderSuperuser();

    expect(await screen.findByText(MSG_ERRO)).toBeInTheDocument();
    expect(valorDoKpi('Aprovações Pendentes')).toBe('—');
    expect(valorDoKpi('Minhas Solicitações')).toBe('—');
    expect(valorDoKpi('Eventos Futuros')).toBe('—');
    expect(container.querySelector('.ant-badge')).toBeNull();
    // Os atalhos seguem lá.
    expect(screen.getByRole('heading', { name: 'Solicitações de Aprovação', level: 5 })).toBeInTheDocument();

    mockGetHomeStats.mockResolvedValueOnce({ pending_approvals: 3, my_requests: 2, upcoming_events: 5 });
    fireEvent.click(screen.getByRole('button', { name: 'Tentar de novo' }));

    await waitFor(() => expect(screen.queryByText(MSG_ERRO)).not.toBeInTheDocument());
    expect(await screen.findByText('Eventos Futuros')).toBeInTheDocument();
    expect(valorDoKpi('Aprovações Pendentes')).toBe('3');
    expect(valorDoKpi('Eventos Futuros')).toBe('5');
    expect(mockGetHomeStats).toHaveBeenCalledTimes(2);
  });

  test('upcoming_events null esconde "Eventos Futuros"', async () => {
    mockGetHomeStats.mockResolvedValueOnce({ pending_approvals: 1, my_requests: 0, upcoming_events: null });
    renderSuperuser();

    await screen.findByText('Aprovações Pendentes', { selector: '.ant-statistic-title' });
    expect(screen.queryByText('Eventos Futuros')).not.toBeInTheDocument();
  });

  test('cartão do superusuário: usuários e lotação', async () => {
    mockGetHomeStats.mockResolvedValueOnce({ pending_approvals: 0, my_requests: 0, upcoming_events: 0 });
    renderSuperuser();

    expect(await screen.findByText('Gerenciar usuários e lotação.')).toBeInTheDocument();
    expect(screen.queryByText(/permissões/)).not.toBeInTheDocument();
  });
});
