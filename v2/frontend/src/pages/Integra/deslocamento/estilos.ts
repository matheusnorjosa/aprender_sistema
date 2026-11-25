/**
 * Cores e rótulos das telas do Deslocamento.
 *
 * As cores das faixas são as dos estratos do ICA (`COR_ESTRATO`), já conferidas em contraste (texto 4,5:1
 * no fundo claro; barra 3:1 no branco): Próximo = verde, Médio = azul, Longo = âmbar, Muito longo = vermelho.
 * A cor nunca aparece sozinha: o nome da faixa vai sempre escrito.
 */
import { FAIXAS_DESLOCAMENTO, type FaixaDeslocamento } from '../dados/deslocamento';
import type { MeioDeslocamento } from '../dados/tipos';
import { COR_ESTRATO, type CorEstrato } from '../ica/componentes/estilos';

export const COR_FAIXA: Record<FaixaDeslocamento, CorEstrato> = {
  proximo: COR_ESTRATO.adequada,
  medio: COR_ESTRATO.capacidade,
  longo: COR_ESTRATO.atencao,
  muito_longo: COR_ESTRATO.sobrecarga,
};

export const ROTULO_MEIO: Record<MeioDeslocamento, string> = {
  carro: 'Carro',
  aviao: 'Avião',
};

export function rotuloDaFaixa(faixa: FaixaDeslocamento): string {
  return FAIXAS_DESLOCAMENTO.find((f) => f.faixa === faixa)?.rotulo ?? faixa;
}
