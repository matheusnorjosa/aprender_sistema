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

  test('decisões 53 a 56: o que o dono decidiu onde o relatório se contradiz ou não diz', async () => {
    await abrir();
    // As três divergências do relatório foram decididas em 25/11: a seção "para confirmar" vira "o que o dono decidiu".
    expect(screen.queryByRole('list', { name: 'Para confirmar com quem fez o relatório' })).not.toBeInTheDocument();
    const lista = screen.getByRole('list', { name: 'O que o dono decidiu sobre o relatório' });
    expect(within(lista).getAllByRole('listitem').map((li) => li.textContent)).toEqual([
      'Só por terra: valem os 23 municípios do grupo que o relatório lista (17 do Ceará, 2 da Paraíba e 4 avulsos), não os 16 da página 1 (decisão 53).',
      'Craíbas-AL (18h00 de ida e volta) fica em Longo, pelo limite do próprio relatório, e não em Muito longo, como a tabela escreve (decisão 54).',
      // Rodada 3: a decisão 55 respondeu pelo município sem localidade; o local conhecido fora do relatório é leitura.
      'O tempo do meio é a mediana que o relatório escreve, 17h45. O ICA usa esse tempo, marcado como estimado, para o município sem localidade definida (decisão 55). O protótipo usa o mesmo tempo para o local de formação que não está no relatório, como Mauriti-CE do Amigos do Bem (ponto em Para validar).',
      'Amigos do Bem não tem município fixo: o tempo é o do local de cada formação, que pode ser em AL, CE ou PE (decisão 56).',
    ]);
    expect(lista).not.toHaveTextContent('17h48');
  });
});
