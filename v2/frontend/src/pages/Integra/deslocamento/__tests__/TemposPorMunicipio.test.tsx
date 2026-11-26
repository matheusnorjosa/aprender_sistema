/**
 * Deslocamento — tempos por município (dados REAIS do relatório): o resumo da página 1 no topo, a
 * tabela dos 92 com filtro por estado, faixa e meio de transporte, e o celular sem rolagem horizontal.
 */
import { act, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, test } from 'vitest';

import { definirLarguraTela } from '../../../../test/larguraTela';
import { renderTelaDeslocamento } from './telaDeslocamento';

async function abrir(): Promise<void> {
  renderTelaDeslocamento('/integra/deslocamento');
  await screen.findByRole('heading', { level: 1, name: 'Tempos de deslocamento' });
}

function itensDoResumo(): string[] {
  // Rodada 5: o resumo traz as correções do dono (decisões 53 e 54), então não se chama mais "do relatório".
  return within(screen.getByRole('list', { name: 'Resumo, com as correções do dono' }))
    .getAllByRole('listitem')
    .map((li) => li.textContent ?? '');
}

function linhas(): HTMLElement[] {
  const tabela = screen.getByRole('table', { name: 'Tempo de cada município' });
  return within(tabela)
    .getAllByRole('row')
    .filter((tr) => tr.getAttribute('data-row-key') !== null);
}

describe('Deslocamento — tempos por município', { timeout: 20000 }, () => {
  test('resumo no topo com os números da página 1 do relatório', async () => {
    await abrir();
    expect(itensDoResumo()).toEqual([
      '92 municípios',
      '23 por terra (carro)',
      '69 de avião (35 com conexão)',
      'Mediana: 17h45 de ida e volta',
      'Menor: 0h40 (Maracanaú-CE)',
      'Maior: 31h35 (Filadélfia-BA)',
    ]);
    // Decisão 55: o tempo do meio é o 17h45 do relatório; a tela não mostra mais a dupla 17h45/17h48.
    const mediana = screen.getByText(/O tempo do meio é a mediana do relatório/);
    expect(mediana).toHaveTextContent(
      // Rodada 3: a decisão 55 respondeu pelo município sem localidade; o local conhecido fora do relatório é leitura.
      'O tempo do meio é a mediana do relatório: 17h45. O ICA usa esse tempo, marcado como estimado, para o município sem localidade definida. O protótipo usa o mesmo tempo para o local de formação que não está no relatório (ponto em Para validar).',
    );
    expect(document.body).not.toHaveTextContent('17h48');
  });

  test('rodada 5 (decisões 53 e 54): o resumo e as faixas dizem que os números corrigidos diferem do PDF', async () => {
    await abrir();
    expect(screen.getByText(/^Com as correções do dono/)).toHaveTextContent(
      'Com as correções do dono, estes números diferem do PDF: 23 municípios só por terra, e não os 16 da página 1 (decisão 53); Craíbas-AL fica em Longo, e não em Muito longo (decisão 54), o que dá Longo 35 e Muito longo 43, onde o PDF escreve 34 e 44.',
    );
  });

  test('faixas com nome e número escritos, e a tabela ao lado do gráfico', async () => {
    await abrir();
    const grafico = screen.getByRole('figure', { name: /Municípios por faixa/ });
    expect(within(grafico).getAllByRole('listitem').map((li) => li.textContent)).toEqual([
      'Próximo (até 3h de ida e volta): 7',
      'Médio (até 10h de ida e volta): 7',
      // Decisão 54: Craíbas-AL passa de Muito longo para Longo.
      'Longo (até 18h de ida e volta): 35',
      'Muito longo (acima de 18h de ida e volta): 43',
    ]);
    const tabela = screen.getByRole('table', { name: 'Municípios por faixa' });
    expect(within(tabela).getAllByRole('columnheader').map((th) => th.textContent)).toEqual(['Faixa', 'Limite', 'Municípios']);
    expect(within(tabela).getByRole('rowheader', { name: 'Muito longo' }).closest('tr')).toHaveTextContent('43');
    expect(within(tabela).getByRole('rowheader', { name: 'Longo' }).closest('tr')).toHaveTextContent('35');
  });

  test('a tabela mostra os 92, com ida e volta, faixa e meio', async () => {
    await abrir();
    expect(linhas()).toHaveLength(92);
    expect(screen.getByRole('status')).toHaveTextContent('Mostrando 92 de 92 municípios.');
    const filadelfia = linhas().find((l) => l.textContent?.includes('Filadélfia-BA')) as HTMLElement;
    expect(filadelfia).toHaveTextContent('31h35');
    expect(filadelfia).toHaveTextContent('Muito longo');
    expect(filadelfia).toHaveTextContent('Carro');
    // Decisão 54: Craíbas-AL (18h00) aparece em Longo.
    const craibas = linhas().find((l) => l.textContent?.includes('Craíbas-AL')) as HTMLElement;
    expect(craibas).toHaveTextContent('18h00');
    expect(craibas).toHaveTextContent('Longo');
    expect(craibas).not.toHaveTextContent('Muito longo');
  });

  test('marcas do relatório: ações suspensas, travessia de barco e só por terra por decisão da gestão', async () => {
    await abrir();
    const itaparica = linhas().find((l) => l.textContent?.includes('Itaparica-BA')) as HTMLElement;
    expect(itaparica).toHaveTextContent('Ações suspensas');
    expect(itaparica).toHaveTextContent('Travessia de barco');
    const petrolina = linhas().find((l) => l.textContent?.includes('Petrolina-PE')) as HTMLElement;
    expect(petrolina).toHaveTextContent('Só por terra, por decisão da gestão');
  });

  test('filtro por estado, faixa e meio; a contagem acompanha e dá para limpar', async () => {
    const user = userEvent.setup();
    await abrir();
    await user.selectOptions(screen.getByLabelText('Estado'), 'CE');
    expect(linhas()).toHaveLength(17);
    expect(screen.getByRole('status')).toHaveTextContent('Mostrando 17 de 92 municípios.');

    await user.selectOptions(screen.getByLabelText('Faixa'), 'proximo');
    expect(linhas()).toHaveLength(7);

    await user.selectOptions(screen.getByLabelText('Estado'), '');
    await user.selectOptions(screen.getByLabelText('Faixa'), 'muito_longo');
    await user.selectOptions(screen.getByLabelText('Meio de transporte'), 'carro');
    expect(linhas().map((l) => l.textContent)).toEqual([
      expect.stringContaining('Afrânio-PE'),
      expect.stringContaining('Lagoa Grande-PE'),
      expect.stringContaining('Petrolina-PE'),
      expect.stringContaining('Filadélfia-BA'),
    ]);

    await user.click(screen.getByRole('button', { name: 'Limpar filtros' }));
    expect(linhas()).toHaveLength(92);
    expect(screen.getByLabelText('Meio de transporte')).toHaveValue('');
  });

  test('filtro sem resultado avisa em texto', async () => {
    const user = userEvent.setup();
    await abrir();
    await user.selectOptions(screen.getByLabelText('Estado'), 'SC');
    await user.selectOptions(screen.getByLabelText('Meio de transporte'), 'carro');
    expect(screen.getByRole('status')).toHaveTextContent('Nenhum município com estes filtros.');
  });

  test('a 400 px a tabela manda colunas para a linha expandida (sem rolagem horizontal)', async () => {
    await abrir();
    act(() => definirLarguraTela(400));
    const tabela = screen.getByRole('table', { name: 'Tempo de cada município' });
    expect(within(tabela).queryByRole('columnheader', { name: 'Meio' })).not.toBeInTheDocument();
    expect(within(tabela).getByRole('columnheader', { name: 'Ida e volta' })).toBeInTheDocument();
    expect(within(tabela).getByRole('button', { name: 'Expandir linha de Maracanaú-CE' })).toBeInTheDocument();
  });
});
