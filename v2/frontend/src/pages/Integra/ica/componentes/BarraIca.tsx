/**
 * Barra horizontal do ICA sobre as faixas de cor, com a linha vertical da média (100) e um traço fino
 * em cada divisa (80, 110, 130). Onde não houver a `FaixasLegenda`, ponha a `FaixasLegendaCurta`.
 *
 * Feita em CSS (sem biblioteca de gráfico) e decorativa (`aria-hidden`): quem a usa põe ao lado o
 * texto "170 · Sobrecarga" (EtiquetaEstrato) e a tabela com os números. Larguras em %, então a
 * barra acompanha a largura da tela sem rolar.
 */
import type { JSX } from 'react';

import type { Estrato } from '../calculo';
import { COR_DIVISA, COR_ESTRATO, DIVISAS_DAS_FAIXAS } from './estilos';

interface BarraIcaProps {
  ica: number;
  estrato: Estrato;
  /** Fim da escala (o mesmo para todas as barras de um gráfico). Ver `escalaDoGrafico`. */
  escalaMax: number;
  /** Barra mais baixa (ex.: antes e depois lado a lado no simulador). */
  fina?: boolean;
}

/** Fim da escala: pelo menos 200 e sempre acima do maior ICA, de 10 em 10. */
// Função pura usada junto com o componente pelas telas (o Fast Refresh só recarrega a página inteira).
// eslint-disable-next-line react-refresh/only-export-components
export function escalaDoGrafico(icas: readonly number[]): number {
  const maior = Math.max(0, ...icas);
  return Math.max(200, Math.ceil((maior + 1) / 10) * 10);
}

const pct = (valor: number, escala: number): string => `${Math.min(100, Math.max(0, (valor / escala) * 100))}%`;

export function BarraIca({ ica, estrato, escalaMax, fina = false }: BarraIcaProps): JSX.Element {
  const faixas: { de: number; ate: number; estrato: Estrato }[] = [
    { de: 0, ate: 80, estrato: 'capacidade' },
    { de: 80, ate: 110, estrato: 'adequada' },
    { de: 110, ate: 130, estrato: 'atencao' },
    { de: 130, ate: escalaMax, estrato: 'sobrecarga' },
  ];
  return (
    <div aria-hidden="true" className={`relative w-full overflow-hidden rounded-sm ${fina ? 'h-4' : 'h-6'}`}>
      {faixas.map((f) => (
        <div
          key={f.estrato}
          className="absolute inset-y-0"
          style={{ left: pct(f.de, escalaMax), width: pct(f.ate - f.de, escalaMax), background: COR_ESTRATO[f.estrato].fundo }}
        />
      ))}
      {/* As cores vizinhas das faixas quase não se distinguem: um traço marca cada divisa. */}
      {DIVISAS_DAS_FAIXAS.map((v) => (
        <div key={v} data-parte="divisa" className="absolute inset-y-0 w-px" style={{ left: pct(v, escalaMax), background: COR_DIVISA }} />
      ))}
      <div
        data-parte="barra"
        className={`absolute left-0 rounded-r-sm ${fina ? 'inset-y-1' : 'inset-y-1.5'}`}
        style={{ width: pct(ica, escalaMax), background: COR_ESTRATO[estrato].forte }}
      />
      <div data-parte="media" className="absolute inset-y-0 w-0.5 bg-[#1f1f1f]" style={{ left: pct(100, escalaMax) }} />
    </div>
  );
}
