/**
 * Ensaio de 20/10/2026 (rodada 2, item 38): Enter no campo de data enviou o formulário com o
 * Tipo "Total" que vinha marcado de fábrica, sem a pessoa escolher, e criou um bloqueio
 * total por engano. O tipo agora começa vazio e é obrigatório, como o tipo de compra e os
 * demais campos de escolha do sistema: o Enter continua enviando, mas sem tipo não passa.
 */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, test, vi } from 'vitest';

import BlockForm from '../BlockForm';

vi.setConfig({ testTimeout: 30_000 });

describe('BlockForm: tipo do bloqueio sem valor de fábrica', () => {
  test('o tipo começa vazio', () => {
    render(<BlockForm onSubmit={vi.fn()} />);
    const tipo = screen.getByRole('combobox', { name: 'Tipo de Bloqueio' });
    const campo = tipo.closest('.ant-select');
    expect(campo?.querySelector('.ant-select-selection-item')).toBeNull();
    expect(screen.queryByText('Total (T)')).not.toBeInTheDocument();
  });

  test('enviar sem escolher o tipo não cria o bloqueio e pede o tipo', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<BlockForm onSubmit={onSubmit} />);

    await user.click(screen.getByRole('button', { name: 'Criar Bloqueio' }));

    expect(await screen.findByText('Escolha o tipo do bloqueio.')).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });
});
