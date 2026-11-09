/**
 * /dashboards/compras: o cartão "Municípios pendentes de agendamento" segue os mesmos filtros
 * dos KPIs (alinhamento das telas, 05/11/2026; B#23). Antes, Ano de Uso, Produto e Tipo mudavam
 * os KPIs e não a lista de pendências, sem aviso; o servidor agora aceita os mesmos filtros.
 */
import { describe, expect, test, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';

import { ComAcesso } from '../../../test/comAcesso';

const { dashboard } = vi.hoisted(() => ({
  dashboard: {
    kpis: {
      municipios_atendidos: 1,
      total_municipios_referencia: 10,
      cobertura_percentual: 10,
      total_itens: 5,
      total_entregue: 0,
      total_disponivel: 5,
      produtos_diferentes: 1,
      colecoes_diferentes: 1,
    },
    por_colecao: [],
    top_produtos: [],
    top_municipios: [],
    top_frequencia: [],
    por_ano: [],
    por_tipo_compra: [],
  },
}));

vi.mock('../../../api/datModule', () => ({
  getComprasDashboard: vi.fn().mockResolvedValue(dashboard),
  getComprasPendencias: vi.fn().mockResolvedValue({
    total_com_compra: 0,
    total_com_evento: 0,
    total_pendentes: 0,
    percentual_pendentes: 0,
    pendentes: [],
  }),
  getProdutosOptions: vi.fn().mockResolvedValue([{ id: 7, nome: 'Kit Ficticio' }]),
  getProjetosOptions: vi.fn().mockResolvedValue([]),
}));

import ComprasDashboardPage from '../ComprasDashboardPage';
import { getComprasDashboard, getComprasPendencias } from '../../../api/datModule';

function escolher(placeholder: string, opcao: string): void {
  const select = screen.getByText(placeholder, { selector: '.ant-select-selection-placeholder' }).closest('.ant-select');
  fireEvent.mouseDown(select!.querySelector('.ant-select-selector')!);
  fireEvent.click(screen.getByTitle(opcao));
}

describe('ComprasDashboardPage: pendências com os filtros do painel', () => {
  beforeEach(() => vi.clearAllMocks());

  test(
    'Produto e Tipo de Compra chegam às pendências como chegam ao dashboard',
    async () => {
      render(
        <MemoryRouter>
          <ComAcesso policies={['view_compras_dashboard', 'view_compras_pendencias']}>
            <ComprasDashboardPage />
          </ComAcesso>
        </MemoryRouter>,
      );
      await screen.findByText('Municípios pendentes de agendamento', {}, { timeout: 15000 });

      escolher('Produto', 'Kit Ficticio');
      await screen.findByText('Municípios pendentes de agendamento', {}, { timeout: 15000 });
      escolher('Tipo de Compra', 'Compra adicional 1');

      await waitFor(() =>
        expect(vi.mocked(getComprasPendencias)).toHaveBeenLastCalledWith(
          expect.objectContaining({ produto_id: 7, tipo_compra: 'adicional_1' }),
        ),
      );
      expect(vi.mocked(getComprasPendencias).mock.lastCall?.[0]).toEqual(
        vi.mocked(getComprasDashboard).mock.lastCall?.[0],
      );
    },
    25000,
  );
});
