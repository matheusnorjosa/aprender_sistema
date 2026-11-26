/**
 * Componentes de gráfico do ICA: cor sempre com nome e número, e o gráfico com texto equivalente.
 */
import { render, screen, within } from '@testing-library/react';
import { describe, expect, test } from 'vitest';

import { BarraIca, escalaDoGrafico } from '../componentes/BarraIca';
import { EtiquetaEstrato } from '../componentes/EtiquetaEstrato';
import { FaixaDispersao } from '../componentes/c2/FaixaDispersao';
import { FaixasLegenda, FaixasLegendaCurta } from '../componentes/FaixasLegenda';
import { TabelaComponentes } from '../componentes/TabelaComponentes';
import { COR_DIVISA, COR_ESTRATO, formatarNumero, formatarVariacao } from '../componentes/estilos';
import { calcularIca, PESOS_REVISADOS } from '../calculo';

/** Contraste WCAG entre duas cores #RRGGBB. */
function contraste(a: string, b: string): number {
  const lum = (hex: string): number => {
    const canais = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
    const [r, g, bl] = canais.map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4)) as [number, number, number];
    return 0.2126 * r + 0.7152 * g + 0.0722 * bl;
  };
  const [x, y] = [lum(a), lum(b)].sort((m, n) => n - m) as [number, number];
  return (x + 0.05) / (y + 0.05);
}

describe('ICA — componentes de gráfico', { timeout: 20000 }, () => {
  test('etiqueta mostra o número e o nome do estrato ("170 · Sobrecarga")', () => {
    render(<EtiquetaEstrato ica={170} estrato="sobrecarga" />);
    expect(screen.getByText('170 · Sobrecarga')).toBeInTheDocument();
  });

  test('etiqueta sem número mostra só o nome; sem municípios diz isso', () => {
    const { rerender } = render(<EtiquetaEstrato estrato="capacidade" />);
    expect(screen.getByText('Capacidade disponível')).toBeInTheDocument();
    rerender(<EtiquetaEstrato ica={0} estrato="capacidade" semMunicipios />);
    expect(screen.getByText('0 · Sem municípios')).toBeInTheDocument();
  });

  test('as cores dos estratos passam AA: texto 4,5:1 no fundo e barra 3:1 em toda faixa', () => {
    const faixas = Object.values(COR_ESTRATO).map((c) => c.fundo);
    for (const cor of Object.values(COR_ESTRATO)) {
      expect(contraste(cor.texto, cor.fundo)).toBeGreaterThanOrEqual(4.5);
      for (const faixa of faixas) expect(contraste(cor.forte, faixa)).toBeGreaterThanOrEqual(3);
    }
  });

  test('legenda das faixas: nome, faixa de valores e orientação de cada estrato, e a meta', () => {
    render(<FaixasLegenda />);
    const lista = screen.getByRole('list', { name: 'Faixas do ICA' });
    const itens = within(lista).getAllByRole('listitem');
    expect(itens).toHaveLength(4);
    expect(itens[0]).toHaveTextContent('Sobrecarga');
    expect(itens[0]).toHaveTextContent('130 ou mais');
    expect(itens[3]).toHaveTextContent('Capacidade disponível');
    expect(itens[3]).toHaveTextContent('abaixo de 80');
    // Decisão 46: a palavra é "projeto", não "contrato".
    expect(itens[3]).toHaveTextContent('Primeiros nomes para novos projetos ou retomadas.');
    expect(lista).not.toHaveTextContent(/contrato/i);
    expect(screen.getByText(/Meta: todos entre 70 e 130/)).toBeInTheDocument();
  });

  test('barra: o gráfico é decorativo e a largura segue o ICA na escala', () => {
    const { container } = render(<BarraIca ica={150} estrato="sobrecarga" escalaMax={200} />);
    const grafico = container.firstElementChild as HTMLElement;
    expect(grafico).toHaveAttribute('aria-hidden', 'true');
    expect(container.querySelector('[data-parte="barra"]')).toHaveStyle({ width: '75%' });
    expect(container.querySelector('[data-parte="media"]')).toHaveStyle({ left: '50%' });
  });

  test('barra e dispersão marcam as divisas 80, 110 e 130 com traço de 3:1 em toda faixa', () => {
    for (const c of Object.values(COR_ESTRATO)) expect(contraste(COR_DIVISA, c.fundo)).toBeGreaterThanOrEqual(3);
    const graficos = [
      <BarraIca key="b" ica={150} estrato="sobrecarga" escalaMax={200} />,
      <FaixaDispersao key="d" menor={60} maior={170} media={100} escalaMax={200} />,
    ];
    for (const grafico of graficos) {
      const { container, unmount } = render(grafico);
      const divisas = [...container.querySelectorAll<HTMLElement>('[data-parte="divisa"]')];
      const posicoes = divisas.map((d) => Math.round(parseFloat(d.style.left) * 1000) / 1000);
      expect(posicoes).toEqual([40, 55, 65]);
      unmount();
    }
  });

  test('legenda curta das faixas: cada cor com nome e números, para os gráficos fora do Painel', () => {
    render(<FaixasLegendaCurta />);
    const legenda = screen.getByText(/Fundo das barras/);
    expect(legenda).toHaveTextContent(
      'Fundo das barras: abaixo de 80 Capacidade disponível · 80 a 109 Adequada · 110 a 129 Atenção · 130 ou mais Sobrecarga. Traço fino = divisa entre faixas; traço preto = 100, a média da equipe.',
    );
  });

  test('legenda curta da dispersão: os traços pretos são o menor e o maior ICA, e a bolinha é a média', () => {
    render(<FaixasLegendaCurta grafico="dispersao" />);
    const legenda = screen.getByText(/Fundo do gráfico/);
    expect(legenda).toHaveTextContent(
      'Fundo do gráfico: abaixo de 80 Capacidade disponível · 80 a 109 Adequada · 110 a 129 Atenção · 130 ou mais Sobrecarga. Traço fino = divisa entre faixas; traços pretos = menor e maior ICA; bolinha = média.',
    );
    expect(legenda).not.toHaveTextContent('traço preto = 100');
  });

  test('tabela de componentes de quem está sem municípios: fora da média, não "Capacidade disponível"', () => {
    const zero = { municipios: 0, frentes: 0, turmas: 0, professores: 0, deslocamento: 0, estados: 0 };
    const medias = { municipios: 5.44, frentes: 7.31, turmas: 16.13, professores: 678.19, deslocamento: 75.0333, estados: 2 };
    const conta = calcularIca(zero, medias, PESOS_REVISADOS);
    const { container } = render(<TabelaComponentes valores={zero} medias={medias} pesos={PESOS_REVISADOS} conta={conta} semMunicipios />);
    expect(screen.getByText('Sem municípios: ICA 0, fora da média da equipe')).toBeInTheDocument();
    expect(container).not.toHaveTextContent(/Capacidade disponível/);
  });

  test('escala do gráfico: pelo menos 200 e sempre acima do maior ICA', () => {
    expect(escalaDoGrafico([90, 120])).toBe(200);
    expect(escalaDoGrafico([231])).toBe(240);
  });

  test('tabela de componentes: valor, média, índice, peso e contribuição, e o ICA no fim', () => {
    const valores = { municipios: 8, frentes: 14, turmas: 23, professores: 1291, deslocamento: 139, estados: 3 };
    const medias = { municipios: 5.44, frentes: 7.31, turmas: 16.13, professores: 678.19, deslocamento: 75.0333, estados: 2 };
    const conta = calcularIca(valores, medias, PESOS_REVISADOS);
    render(<TabelaComponentes valores={valores} medias={medias} pesos={PESOS_REVISADOS} conta={conta} />);
    const tabela = screen.getByRole('table');
    expect(within(tabela).getByText('Municípios ativos')).toBeInTheDocument();
    expect(within(tabela).getByText('139h00')).toBeInTheDocument();
    expect(within(tabela).getByText('1.291')).toBeInTheDocument();
    expect(within(tabela).getAllByText('25%')).toHaveLength(2);
    // Peso zero (Estados na revisada) aparece como fora da conta.
    expect(within(tabela).getByText('fora da conta')).toBeInTheDocument();
    expect(screen.getByText(/ICA: 169,8 → 170 · Sobrecarga/)).toBeInTheDocument();
  });

  test('o ICA exato não é arredondado antes do inteiro: 148,4758 mostra "148,4 → 148", nunca "148,5"', () => {
    const valores = { municipios: 8, frentes: 14, turmas: 23, professores: 1291, deslocamento: 139, estados: 3 };
    const medias = { municipios: 5.44, frentes: 7.31, turmas: 16.13, professores: 678.19, deslocamento: 75.0333, estados: 2 };
    const base = calcularIca(valores, medias, PESOS_REVISADOS);
    const casos: Array<[number, number, string]> = [
      [148.4758, 148, 'ICA: 148,4 → 148 · Sobrecarga'],
      [148.4999, 148, 'ICA: 148,4 → 148 · Sobrecarga'],
      [148.5, 149, 'ICA: 148,5 → 149 · Sobrecarga'],
      // Ruído do ponto flutuante não pode derrubar a casa: 169,8 continua 169,8.
      [169.79999999999998, 170, 'ICA: 169,8 → 170 · Sobrecarga'],
    ];
    for (const [icaExato, icaExibido, texto] of casos) {
      const conta = { ...base, icaExato, icaExibido, estrato: 'sobrecarga' as const };
      const { unmount } = render(<TabelaComponentes valores={valores} medias={medias} pesos={PESOS_REVISADOS} conta={conta} />);
      expect(screen.getByText(texto)).toBeInTheDocument();
      unmount();
    }
  });

  test('números no formato brasileiro e variação com sinal', () => {
    expect(formatarNumero(1291)).toBe('1.291');
    expect(formatarNumero(30.789, 1)).toBe('30,8');
    expect(formatarVariacao(-23)).toBe('−23');
    expect(formatarVariacao(5)).toBe('+5');
    expect(formatarVariacao(0)).toBe('0');
  });
});
