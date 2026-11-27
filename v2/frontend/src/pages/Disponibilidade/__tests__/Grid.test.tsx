/**
 * Grade Mensal enxuta (pedido do dono, 27/11/2026): sem o título repetido (a página já tem o h2),
 * quadradinho mais baixo, horas só quando há (no formato brasileiro), todo código clicável e o
 * nome da pessoa abrindo o mês dela.
 */
import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, test, vi } from 'vitest';

import Grid from '../Grid';

type Props = Parameters<typeof Grid>[0];

function desenhar(over: Partial<Props> = {}) {
  const props: Props = {
    year: 2026,
    month: 1,
    days: [1, 2, 3],
    diasVisiveis: [0, 1, 2],
    people: [
      { id: 1, name: 'Ana Formadora', ch_month: 4.5 },
      { id: 2, name: 'Bruno Formador', ch_month: 0 },
    ],
    cells: [
      ['E', '', 'D'],
      ['', 'P', ''],
    ],
    onSelect: vi.fn(),
    onSelectPessoa: vi.fn(),
    selected: null,
    ...over,
  };
  render(<Grid {...props} />);
  return props;
}

const linhaDe = (nome: string): HTMLElement =>
  screen.getByRole('button', { name: `Ver o mês de ${nome}` }).closest('tr') as HTMLElement;

describe('Grid — grade mensal enxuta', () => {
  test('não repete o título da grade: nenhum cabeçalho dentro dela', () => {
    desenhar();
    expect(screen.queryByRole('heading')).not.toBeInTheDocument();
  });

  test('horas só quando passam de zero, no formato brasileiro (4,5h), sem "0h"', () => {
    desenhar();
    expect(screen.getByText('4,5h')).toBeInTheDocument();
    expect(screen.queryByText('4.5h')).not.toBeInTheDocument();
    expect(screen.queryByText('0h')).not.toBeInTheDocument();
  });

  // Como a planilha: nome curto numa linha; o nome inteiro fica no título, no nome acessível e na gaveta.
  test('nome longo aparece curto (primeiro e último), com o nome inteiro no título', () => {
    desenhar({ people: [{ id: 3, name: 'Maria Aparecida dos Santos Figueiredo', ch_month: 2 }], cells: [['E', '', '']] });
    const botao = screen.getByRole('button', { name: 'Ver o mês de Maria Aparecida dos Santos Figueiredo' });
    expect(botao).toHaveTextContent(/^Maria Figueiredo$/);
    expect(botao).toHaveAttribute('title', 'Maria Aparecida dos Santos Figueiredo');
  });

  test('todo código é clicável, mesmo sem detalhe; célula vazia não tem botão', () => {
    const props = desenhar();
    const celulas = within(linhaDe('Ana Formadora')).getAllByRole('cell');
    // Célula 0 é o nome; 1 = dia 1 (E), 2 = dia 2 (vazio), 3 = dia 3 (D).
    expect(within(celulas[2] as HTMLElement).queryByRole('button')).toBeNull();

    fireEvent.click(within(celulas[3] as HTMLElement).getByRole('button'));
    expect(props.onSelect).toHaveBeenCalledWith(0, 2);
    const botao = within(celulas[1] as HTMLElement).getByRole('button');
    expect(botao).toHaveClass('cursor-pointer');
    expect(botao).not.toHaveClass('opacity-70');
  });

  test('quadradinho baixo como a planilha (h-4, não h-7) e com o foco visível', () => {
    desenhar();
    const botao = within(within(linhaDe('Bruno Formador')).getAllByRole('cell')[2] as HTMLElement).getByRole('button');
    expect(botao).toHaveClass('h-4');
    expect(botao).not.toHaveClass('h-7');
    expect(botao.className).toContain('focus-visible:outline');
  });

  // WCAG 2.5.3: o nome acessível começa pela letra que se vê e diz o que ela é, de quem e o dia.
  test('o código tem nome acessível: a letra, o que ela quer dizer, a pessoa e o dia', () => {
    desenhar();
    expect(screen.getByRole('button', { name: 'D, deslocamento: Ana Formadora, dia 3' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'E, 1 evento: Ana Formadora, dia 1' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^P, bloqueio parcial: Bruno Formador, dia 2$/i })).toBeInTheDocument();
  });

  test('o nome é um botão que abre o mês da pessoa', () => {
    const props = desenhar();
    fireEvent.click(screen.getByRole('button', { name: 'Ver o mês de Bruno Formador' }));
    expect(props.onSelectPessoa).toHaveBeenCalledWith(1);
    expect(props.onSelect).not.toHaveBeenCalled();
  });
});
