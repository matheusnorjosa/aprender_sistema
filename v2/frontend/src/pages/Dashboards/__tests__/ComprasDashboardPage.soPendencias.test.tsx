/**
 * /dashboards/compras para quem tem só a policy das pendências (decisão do dono, 09/11/2026).
 *
 * O Controle tem `view_compras_pendencias` (a API das pendências já o atende) e não tem
 * `view_compras_dashboard`. A tela não pede o dashboard agregado (o 403 derrubava a página
 * inteira), não mostra os blocos agregados e mostra só as pendências, com os filtros, que
 * leem `/options/*` (abertos a quem está logado). Quem tem o dashboard vê o mesmo de antes.
 */
import { describe, expect, test, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';

import { ComAcesso } from '../../../test/comAcesso';
import { atorRbac, type NomeDoAtor } from '../../../test/atoresRbac';

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
    total_com_compra: 1,
    total_com_evento: 0,
    total_pendentes: 1,
    percentual_pendentes: 100,
    pendentes: [
      {
        municipio_id: 1,
        municipio: 'Iguatu',
        uf: 'CE',
        projeto_id: 2,
        projeto: 'Projeto Ficticio',
        total_itens: 5,
        total_compras: 1,
        ultima_compra: '2026-10-01',
      },
    ],
  }),
  getProdutosOptions: vi.fn().mockResolvedValue([{ id: 7, nome: 'Kit Ficticio' }]),
  getProjetosOptions: vi.fn().mockResolvedValue([]),
}));

import ComprasDashboardPage from '../ComprasDashboardPage';
import { getComprasDashboard, getComprasPendencias } from '../../../api/datModule';

function renderComo(ator: NomeDoAtor): void {
  const { user, policies } = atorRbac(ator);
  render(
    <MemoryRouter>
      <ComAcesso policies={policies} superusuario={user.is_superuser}>
        <ComprasDashboardPage />
      </ComAcesso>
    </MemoryRouter>,
  );
}

describe('ComprasDashboardPage: quem vê só as pendências', { timeout: 25000 }, () => {
  beforeEach(() => vi.clearAllMocks());

  test('Controle: não pede o dashboard e vê só as pendências, com o título delas', async () => {
    renderComo('Controle');

    expect(await screen.findByText('Iguatu', {}, { timeout: 15000 })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 2, name: 'Pendências de compras' })).toBeInTheDocument();
    expect(screen.getByText('Municípios pendentes de agendamento')).toBeInTheDocument();

    expect(vi.mocked(getComprasDashboard)).not.toHaveBeenCalled();
    expect(vi.mocked(getComprasPendencias)).toHaveBeenCalled();
    expect(screen.queryByText('Dashboard de Compras')).not.toBeInTheDocument();
    expect(screen.queryByText('Municípios atendidos')).not.toBeInTheDocument();
    expect(screen.queryByText('Quantidade por Coleção')).not.toBeInTheDocument();
    expect(screen.queryByText('Quem compra mais (Municípios)')).not.toBeInTheDocument();
  });

  test('Controle: os filtros chegam às pendências', async () => {
    renderComo('Controle');
    await screen.findByText('Iguatu', {}, { timeout: 15000 });

    const select = screen
      .getByText('Produto', { selector: '.ant-select-selection-placeholder' })
      .closest('.ant-select');
    fireEvent.mouseDown(select!.querySelector('.ant-select-selector')!);
    fireEvent.click(await screen.findByTitle('Kit Ficticio'));

    await waitFor(() =>
      expect(vi.mocked(getComprasPendencias)).toHaveBeenLastCalledWith(expect.objectContaining({ produto_id: 7 })),
    );
    expect(vi.mocked(getComprasDashboard)).not.toHaveBeenCalled();
  });

  test.each(['DAT', 'Diretoria'] as const)('%s (tem o dashboard): vê o mesmo de antes', async (ator) => {
    renderComo(ator);

    expect(await screen.findByText('Iguatu', {}, { timeout: 15000 })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 2, name: 'Dashboard de Compras' })).toBeInTheDocument();
    expect(vi.mocked(getComprasDashboard)).toHaveBeenCalled();
    expect(screen.getByText('Municípios atendidos')).toBeInTheDocument();
    expect(screen.getByText('Quantidade por Coleção')).toBeInTheDocument();
    expect(screen.getByText('Municípios pendentes de agendamento')).toBeInTheDocument();
    expect(screen.queryByText('Pendências de compras')).not.toBeInTheDocument();
  });
});
