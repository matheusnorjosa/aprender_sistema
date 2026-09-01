/**
 * H.1/#1897: coluna "Família" (projeto_geral_nome) ao lado da variante (projeto_nome) nas
 * telas DAT — o "reagrupar por família" vem de ordenar por ela. Teste representativo em Compras
 * (Ações/PlanoFormações/Formações recebem a MESMA adição mecânica: campo no record + coluna).
 */
import { describe, expect, test, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';

const { row } = vi.hoisted(() => ({
  row: {
    id: 1, projeto: 10, projeto_nome: 'NOVO LENDO 1', projeto_geral_nome: 'NOVO LENDO',
    produto: 100, produto_nome: 'Produto A', codigo_produto: 'A1',
    municipio: 20, municipio_nome: 'Fortaleza', municipio_uf: 'CE',
    quantidade: 5, quantidade_utilizada: 0, data_compra: '2026-03-01', ano_uso: 2026,
    tipo_compra: 'inicial', status_uso: null,
  },
}));

vi.mock('../../../api/datModule', () => ({
  listCompras: vi.fn().mockResolvedValue({ results: [row], count: 1, next: null, previous: null }),
  createCompra: vi.fn(),
  updateCompra: vi.fn().mockResolvedValue({}),
  deleteCompra: vi.fn(),
  getMunicipiosOptions: vi.fn().mockResolvedValue([]),
  getProjetosOptions: vi.fn().mockResolvedValue([]),
  getProdutosOptions: vi.fn().mockResolvedValue([]),
}));

import ComprasPage from '../ComprasPage';

describe('ComprasPage — coluna Família (H.1)', () => {
  beforeEach(() => vi.clearAllMocks());

  test(
    'exibe a variante (projeto_nome) E a família (projeto_geral_nome) em colunas distintas',
    async () => {
      render(
        <MemoryRouter>
          <ComprasPage />
        </MemoryRouter>,
      );
      // colunas Projeto+Família são fixed:left → AntD duplica células/headers → findAllByText
      expect((await screen.findAllByText('Família', {}, { timeout: 20000 })).length).toBeGreaterThan(0);
      // variante e família aparecem (valores distintos → provam colunas distintas)
      expect((await screen.findAllByText('NOVO LENDO 1')).length).toBeGreaterThan(0); // variante
      expect((await screen.findAllByText('NOVO LENDO')).length).toBeGreaterThan(0); // família
    },
    60000,
  );
});
