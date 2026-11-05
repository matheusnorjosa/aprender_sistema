/**
 * /dat/cadastros: indicadores pelo contrato real do stats (alinhamento das telas, 05/11/2026; P#34 · A#32).
 *
 * - Os contadores das abas e os cartões liam campos que o servidor não manda (total_formar,
 *   pendentes, em_andamento, concluidos): ficavam vazios ou em 0 com qualquer volume. O stats
 *   manda total, por_plataforma, formar_completos e avaliar_completos.
 * - "Pendentes" e "Em Andamento" não têm fonte no stats: saíram.
 * - As estatísticas pedem sem `plataforma`, para as duas abas terem o número delas.
 * - "Exportar" não fazia nada (o servidor de cadastros não tem export): saiu.
 */
import { describe, expect, test, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router';

const { statsReal } = vi.hoisted(() => ({
  statsReal: {
    total: 5,
    por_plataforma: { FORMAR: 3, AVALIAR: 2 },
    formar_completos: 1,
    avaliar_completos: 2,
    por_projeto: [],
  },
}));

vi.mock('../../../api/datModule', () => ({
  listCadastros: vi.fn().mockResolvedValue({ results: [], count: 0, next: null, previous: null }),
  getCadastro: vi.fn(),
  createCadastro: vi.fn(),
  updateCadastro: vi.fn(),
  deleteCadastro: vi.fn(),
  updateCadastroEtapa: vi.fn(),
  getCadastrosStats: vi.fn().mockResolvedValue(statsReal),
  getMunicipiosOptions: vi.fn().mockResolvedValue([]),
  getProjetosGeraisOptions: vi.fn().mockResolvedValue([]),
}));

import CadastrosPage from '../CadastrosPage';
import { getCadastrosStats } from '../../../api/datModule';

function cartao(titulo: string): HTMLElement {
  const el = screen.getByText(titulo).closest('.ant-statistic');
  if (!(el instanceof HTMLElement)) throw new Error(`cartão "${titulo}" não encontrado`);
  return el;
}

describe('CadastrosPage: indicadores pelo contrato do stats', () => {
  beforeEach(() => vi.clearAllMocks());

  test(
    'abas e cartões mostram os números do servidor; sem Pendentes, Em Andamento e Exportar',
    async () => {
      render(
        <MemoryRouter>
          <CadastrosPage />
        </MemoryRouter>,
      );

      await screen.findByText('Total Cadastros', {}, { timeout: 15000 });

      expect(within(cartao('Total Cadastros')).getByText('3')).toBeInTheDocument();
      expect(within(cartao('Concluídos')).getByText('1')).toBeInTheDocument();
      expect(within(screen.getByRole('tab', { name: /FORMAR/ })).getByTitle('3')).toBeInTheDocument();
      expect(within(screen.getByRole('tab', { name: /AVALIAR/ })).getByTitle('2')).toBeInTheDocument();

      expect(screen.queryByText('Pendentes', { selector: '.ant-statistic-title' })).not.toBeInTheDocument();
      expect(screen.queryByText('Em Andamento', { selector: '.ant-statistic-title' })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /exportar/i })).not.toBeInTheDocument();

      await waitFor(() => expect(getCadastrosStats).toHaveBeenCalled());
      for (const [params] of vi.mocked(getCadastrosStats).mock.calls) {
        expect(params).not.toHaveProperty('plataforma');
      }
    },
    25000,
  );
});
