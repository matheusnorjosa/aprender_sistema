/**
 * Cores das faixas do Deslocamento: as do relatório da Coordenação Pedagógica (selos da página 2), com WCAG AA.
 * Decisão do dono (26/11/2026): a cor do documento que falha como texto vira só preenchimento, e o texto ganha um
 * tom escuro.
 */
import { describe, expect, test } from 'vitest';

import { COR_FAIXA } from '../estilos';

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

describe('Deslocamento — cores das faixas', () => {
  test('são as do relatório: Próximo e Médio em verde, Longo em âmbar, Muito longo em vermelho', () => {
    expect(COR_FAIXA).toEqual({
      proximo: { fundo: '#E3F4E7', texto: '#1E7B3A', forte: '#1E7B3A' },
      medio: { fundo: '#97D3A6', texto: '#145A2A', forte: '#145A2A' },
      // #9A6A00 (texto do relatório) dá 4,20:1 no fundo: vira a barra; o texto fica num âmbar escuro.
      longo: { fundo: '#FDF0D6', texto: '#7A5300', forte: '#9A6A00' },
      muito_longo: { fundo: '#F9E0DE', texto: '#B02E24', forte: '#B02E24' },
    });
  });

  test('texto 4,5:1 no fundo do selo; barra 3:1 no trilho cinza e no branco', () => {
    for (const cor of Object.values(COR_FAIXA)) {
      expect(contraste(cor.texto, cor.fundo), `${cor.texto} sobre ${cor.fundo}`).toBeGreaterThanOrEqual(4.5);
      for (const trilho of ['#F0F0F0', '#FFFFFF']) {
        expect(contraste(cor.forte, trilho), `${cor.forte} sobre ${trilho}`).toBeGreaterThanOrEqual(3);
      }
    }
  });
});
