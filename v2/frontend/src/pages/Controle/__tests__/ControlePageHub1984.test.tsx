/**
 * #1984: /controle vira um HUB (Painel de Controle) com KPIs de contagem reais
 * + atalhos de navegação — em vez da lista de compras redundante (core.Compra).
 */
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { describe, it, expect, vi } from 'vitest';

vi.mock('../../../api/datModule', () => ({
  getAcoesStats: vi.fn().mockResolvedValue({ total: 241 }),
  getComprasStats: vi.fn().mockResolvedValue({ total: 215 }),
  getPlanoFormacoesStats: vi.fn().mockResolvedValue({ total_planos: 38 }),
  listCoordenadoresDAT: vi.fn().mockResolvedValue({ count: 12, results: [], next: null, previous: null }),
}));

import ControlePage from '../ControlePage';

const renderPage = () =>
  render(
    <MemoryRouter>
      <ControlePage />
    </MemoryRouter>,
  );

describe('#1984 Painel de Controle (hub)', () => {
  it('mostra os KPIs de contagem reais vindos dos /stats/', async () => {
    renderPage();
    expect(await screen.findByText('241')).toBeInTheDocument(); // ações
    expect(await screen.findByText('215')).toBeInTheDocument(); // compras
    expect(await screen.findByText('38')).toBeInTheDocument(); // planos
    expect(await screen.findByText('12')).toBeInTheDocument(); // coordenadores
  });

  it('tem atalhos de navegação pras sub-páginas do /controle', async () => {
    renderPage();
    const acoes = await screen.findByRole('link', { name: /Ações/ });
    expect(acoes).toHaveAttribute('href', '/controle/acoes');
    expect(screen.getByRole('link', { name: /Compras/ })).toHaveAttribute('href', '/controle/compras');
    expect(screen.getByRole('link', { name: /Coordenadores/ })).toHaveAttribute('href', '/controle/coordenadores');
    expect(screen.getByRole('link', { name: /Plano Anual/ })).toHaveAttribute('href', '/controle/plano-formacoes');
  });
});
