/**
 * G30 — Gerenciar Disponibilidade: o cartão "Meus Bloqueios" só divide a largura com o formulário a
 * partir de xxl (1600 px). Na metade da tela (de 992 px em diante, antes), início, fim, tipo, status,
 * motivo e ações não cabiam, e a tabela rolava para o lado (`scroll.x` 800).
 */
import { render, screen } from '@testing-library/react';
import { describe, expect, test, vi } from 'vitest';

vi.mock('../../api/availability', () => ({
  getBlocks: vi.fn().mockResolvedValue([]),
  createBlock: vi.fn(),
  deleteBlock: vi.fn(),
}));

vi.mock('../../components/BlockForm', () => ({ default: () => <div>formulario-bloqueio</div> }));

import Disponibilidade from '../Disponibilidade';

describe('Disponibilidade — largura dos cartões (G30)', { timeout: 20000 }, () => {
  test('formulário e lista ocupam a linha inteira abaixo de xxl e dividem a partir dele', async () => {
    render(<Disponibilidade />);

    for (const rotulo of ['Criar novo bloqueio', 'Lista de meus bloqueios']) {
      const coluna = screen.getByRole('article', { name: rotulo }).closest('.ant-col');
      expect(coluna).toHaveClass('ant-col-xs-24', 'ant-col-xxl-12');
      expect(coluna).not.toHaveClass('ant-col-lg-12');
    }
    expect(await screen.findByText('Nenhum bloqueio cadastrado')).toBeInTheDocument();
  });
});
