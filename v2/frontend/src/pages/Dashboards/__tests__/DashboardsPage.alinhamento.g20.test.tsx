/**
 * G20 — Dashboard Geral: sem o botão "Exportar para CSV" (não fazia nada), fluxo com rótulo legível
 * (não o código NAO_SUPER cru) e textos acentuados.
 */
import { render, screen } from '@testing-library/react';
import { describe, expect, test, vi } from 'vitest';

import DashboardsPage from '../DashboardsPage';

vi.mock('../../../api/dashboard', () => ({
  getDashboardOverview: vi.fn().mockResolvedValue({
    kpis: { eventos_futuros: 1, eventos_aprovados: 2, total_formadores: 3, aprovacoes_pendentes: 4 },
    por_fluxo: [
      { fluxo: 'NAO_SUPER', quantidade: 5 },
      { fluxo: 'SUPER', quantidade: 2 },
    ],
    por_gerencia: [{ gerencia: 'Vidas', quantidade: 7, porcentagem: 100 }],
    top_coordenadores: [],
  }),
}));

describe('DashboardsPage (G20)', { timeout: 20000 }, () => {
  test('não mostra o botão Exportar para CSV', async () => {
    render(<DashboardsPage />);
    await screen.findByText('Dashboards e Análises');
    expect(screen.queryByRole('button', { name: /exportar/i })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /atualizar/i })).toBeInTheDocument();
  });

  test('mostra o rótulo legível do fluxo, não o código', async () => {
    render(<DashboardsPage />);
    expect(await screen.findByText('Não Superintendência')).toBeInTheDocument();
    expect(screen.getByText('Superintendência')).toBeInTheDocument();
    expect(screen.queryByText('NAO_SUPER')).not.toBeInTheDocument();
    expect(screen.queryByText('SUPER')).not.toBeInTheDocument();
  });

  test('textos acentuados', async () => {
    render(<DashboardsPage />);
    await screen.findByText('Dashboards e Análises');
    expect(screen.getByText('Aprovações Pendentes')).toBeInTheDocument();
    expect(screen.getByText(/Eventos por Fluxo \(últimos 30 dias\)/)).toBeInTheDocument();
    expect(screen.getByText(/Eventos por Gerência \(últimos 30 dias\)/)).toBeInTheDocument();
  });
});
