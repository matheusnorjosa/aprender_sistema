/** Deslocamento — como o tempo é calculado: as regras, as faixas, os limites e o que falta confirmar. */
import { screen, within } from '@testing-library/react';
import { describe, expect, test } from 'vitest';

import { OBSERVACOES_DESLOCAMENTO, REGRAS_DO_CALCULO } from '../../dados/deslocamento';
import { renderTelaDeslocamento } from './telaDeslocamento';

async function abrir(): Promise<void> {
  renderTelaDeslocamento('/integra/deslocamento/regras');
  await screen.findByRole('heading', { level: 1, name: 'Como o tempo é calculado' });
}

describe('Deslocamento — como o tempo é calculado', { timeout: 20000 }, () => {
  test('as 8 regras do relatório, cada uma com o tempo e o critério', async () => {
    await abrir();
    const lista = screen.getByRole('list', { name: 'Regras do cálculo' });
    const itens = within(lista).getAllByRole('listitem');
    expect(itens).toHaveLength(REGRAS_DO_CALCULO.length);
    expect(itens).toHaveLength(8);
    expect(itens[0]).toHaveTextContent('Traslado e antecedência no aeroporto de Fortaleza');
    expect(itens[0]).toHaveTextContent('Tempo: 2h00');
    expect(itens[7]).toHaveTextContent('Ida e volta');
    expect(itens[7]).toHaveTextContent('Não inclui pernoite nem o tempo de trabalho no município.');
  });

  test('as faixas, com nome e limite escritos', async () => {
    await abrir();
    const faixas = within(screen.getByRole('list', { name: 'Faixas de ida e volta' })).getAllByRole('listitem');
    expect(faixas.map((li) => li.textContent)).toEqual([
      'Próximo: até 3h de ida e volta',
      'Médio: até 10h de ida e volta',
      'Longo: até 18h de ida e volta',
      'Muito longo: acima de 18h de ida e volta',
    ]);
  });

  test('os limites e observações do relatório', async () => {
    await abrir();
    const lista = screen.getByRole('list', { name: 'Limites e observações' });
    expect(within(lista).getAllByRole('listitem')).toHaveLength(OBSERVACOES_DESLOCAMENTO.length);
    expect(lista).toHaveTextContent(/São estimativas, não horários reais/);
  });

  test('o que o relatório ainda precisa confirmar (divergências dele mesmo)', async () => {
    await abrir();
    const lista = screen.getByRole('list', { name: 'Para confirmar com quem fez o relatório' });
    const itens = within(lista).getAllByRole('listitem');
    expect(itens).toHaveLength(3);
    expect(lista).toHaveTextContent(/16 municípios.*o grupo listado soma 23/);
    expect(lista).toHaveTextContent(/Craíbas-AL.*18h00.*Muito longo/);
    expect(lista).toHaveTextContent(/coluna Ida.*17h45.*coluna Ida e volta.*17h48/);
    expect(lista).toHaveTextContent(/Qual coluna o ICA usa para o município sem localidade\?/);
    expect(lista).not.toHaveTextContent(/cada tempo foi arredondado para 5 minutos/);
  });
});
