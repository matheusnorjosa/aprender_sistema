/**
 * Cinto M17 / #1636: editar uma compra depois de outra retinha valores do formulário
 * anterior — o <Modal> não usa `destroyOnClose`, o `onCancel` só esconde, e o `handleEdit`
 * semeava a linha SEM `form.resetFields()` antes. Campos do form que não vêm na linha
 * (ex.: Observações) sobreviviam entre edições.
 *
 * Este teste digita em Observações na compra A, cancela, abre a edição da compra B e exige
 * o campo limpo. RED no código antigo (handleEdit sem resetFields).
 */
import { describe, expect, test, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';

const { rowA, rowB } = vi.hoisted(() => ({
  rowA: {
    id: 1, projeto: 10, projeto_nome: 'Projeto A', produto: 100, produto_nome: 'Produto A',
    codigo_produto: 'A1', municipio: 20, municipio_nome: 'Fortaleza', municipio_uf: 'CE',
    quantidade: 5, quantidade_utilizada: 0, data_compra: '2026-03-01', ano_uso: 2026,
    tipo_compra: 'inicial', status_uso: null,
  },
  rowB: {
    id: 2, projeto: 11, projeto_nome: 'Projeto B', produto: 101, produto_nome: 'Produto B',
    codigo_produto: 'B1', municipio: 21, municipio_nome: 'Sobral', municipio_uf: 'CE',
    quantidade: 3, quantidade_utilizada: 0, data_compra: '2026-03-02', ano_uso: 2026,
    tipo_compra: 'inicial', status_uso: null,
  },
}));

vi.mock('../../../api/datModule', () => ({
  listCompras: vi.fn().mockResolvedValue({ results: [rowA, rowB], count: 2, next: null, previous: null }),
  createCompra: vi.fn(),
  updateCompra: vi.fn().mockResolvedValue({}),
  deleteCompra: vi.fn(),
  getMunicipiosOptions: vi.fn().mockResolvedValue([]),
  getProjetosOptions: vi.fn().mockResolvedValue([]),
  getProdutosOptions: vi.fn().mockResolvedValue([]),
}));

import ComprasPage from '../ComprasPage';

describe('Cinto M17 (#1636): editar compra reseta o form (sem carry-over)', () => {
  beforeEach(() => vi.clearAllMocks());

  // Timeout folgado: render da página inteira (Table + options + modal) em jsdom passa dos 5s.
  test(
    'valor digitado em Observações na compra A não sobrevive ao editar a compra B',
    async () => {
      const user = userEvent.setup();
      render(
        <MemoryRouter>
          <ComprasPage />
        </MemoryRouter>,
      );

      const editBtns = await screen.findAllByLabelText('Editar compra', {}, { timeout: 15000 });
      await user.click(editBtns[0]); // edita A

      const obs = await screen.findByLabelText('Observações', {}, { timeout: 10000 });
      await user.type(obs, 'OBS_DA_COMPRA_A');
      expect(obs).toHaveValue('OBS_DA_COMPRA_A');

      // cancela — o onCancel só esconde o modal, sem limpar o form
      await user.click(screen.getByRole('button', { name: /cancelar/i }));

      // reabre a edição, agora na compra B
      const editBtns2 = await screen.findAllByLabelText('Editar compra', {}, { timeout: 10000 });
      await user.click(editBtns2[1]); // edita B

      const obsB = await screen.findByLabelText('Observações', {}, { timeout: 10000 });
      expect(obsB).toHaveValue(''); // RED sem resetFields (retém OBS_DA_COMPRA_A)
    },
    30000,
  );
});
