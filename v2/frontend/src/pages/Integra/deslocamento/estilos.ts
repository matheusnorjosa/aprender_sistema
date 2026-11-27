/**
 * Cores e rótulos das telas do Deslocamento.
 *
 * As cores das faixas são as dos selos do relatório da Coordenação Pedagógica (decisão do dono, 26/11/2026):
 * Próximo e Médio em verde, Longo em âmbar, Muito longo em vermelho. Contraste em `__tests__/estilos.test.ts`
 * (texto 4,5:1 no fundo do selo; barra 3:1 no trilho). O âmbar do relatório (#9A6A00) dá 4,20:1 como texto: fica na
 * barra, e o texto do selo usa um tom escuro. A cor nunca aparece sozinha: o nome da faixa vai sempre escrito.
 */
import { FAIXAS_DESLOCAMENTO, type FaixaDeslocamento } from '../dados/deslocamento';
import type { MeioDeslocamento } from '../dados/tipos';
import type { CorEstrato } from '../ica/componentes/estilos';

export const COR_FAIXA: Record<FaixaDeslocamento, CorEstrato> = {
  proximo: { fundo: '#E3F4E7', texto: '#1E7B3A', forte: '#1E7B3A' },
  medio: { fundo: '#97D3A6', texto: '#145A2A', forte: '#145A2A' },
  longo: { fundo: '#FDF0D6', texto: '#7A5300', forte: '#9A6A00' },
  muito_longo: { fundo: '#F9E0DE', texto: '#B02E24', forte: '#B02E24' },
};

export const ROTULO_MEIO: Record<MeioDeslocamento, string> = {
  carro: 'Carro',
  aviao: 'Avião',
};

export function rotuloDaFaixa(faixa: FaixaDeslocamento): string {
  return FAIXAS_DESLOCAMENTO.find((f) => f.faixa === faixa)?.rotulo ?? faixa;
}
