/**
 * Dispersão do ICA de um semestre sobre as faixas de cor: um traço do menor ao maior ICA e uma marca
 * na média. Decorativo (`aria-hidden`): quem usa escreve ao lado "de 58 a 169 · desvio 31,2" e põe a
 * tabela com os números. Larguras em %, sem rolagem.
 */
import type { JSX } from 'react';

import type { Estrato } from '../../calculo';
import { COR_DIVISA, COR_ESTRATO, DIVISAS_DAS_FAIXAS } from '../estilos';

interface FaixaDispersaoProps {
  menor: number;
  maior: number;
  media: number;
  /** Fim da escala (o mesmo para todos os semestres do gráfico). */
  escalaMax: number;
}

const pct = (valor: number, escala: number): string => `${Math.min(100, Math.max(0, (valor / escala) * 100))}%`;

export function FaixaDispersao({ menor, maior, media, escalaMax }: FaixaDispersaoProps): JSX.Element {
  const faixas: { de: number; ate: number; estrato: Estrato }[] = [
    { de: 0, ate: 80, estrato: 'capacidade' },
    { de: 80, ate: 110, estrato: 'adequada' },
    { de: 110, ate: 130, estrato: 'atencao' },
    { de: 130, ate: escalaMax, estrato: 'sobrecarga' },
  ];
  return (
    <div aria-hidden="true" className="relative h-6 w-full overflow-hidden rounded-sm">
      {faixas.map((f) => (
        <div
          key={f.estrato}
          className="absolute inset-y-0"
          style={{ left: pct(f.de, escalaMax), width: pct(f.ate - f.de, escalaMax), background: COR_ESTRATO[f.estrato].fundo }}
        />
      ))}
      {DIVISAS_DAS_FAIXAS.map((v) => (
        <div key={v} data-parte="divisa" className="absolute inset-y-0 w-px" style={{ left: pct(v, escalaMax), background: COR_DIVISA }} />
      ))}
      <div
        data-parte="intervalo"
        className="absolute top-1/2 h-1 -translate-y-1/2 bg-[#1f1f1f]"
        style={{ left: pct(menor, escalaMax), width: pct(maior - menor, escalaMax) }}
      />
      <div data-parte="menor" className="absolute inset-y-1 w-0.5 bg-[#1f1f1f]" style={{ left: pct(menor, escalaMax) }} />
      <div data-parte="maior" className="absolute inset-y-1 w-0.5 bg-[#1f1f1f]" style={{ left: pct(maior, escalaMax) }} />
      <div
        data-parte="media"
        className="absolute top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white bg-[#1f1f1f]"
        style={{ left: pct(media, escalaMax) }}
      />
    </div>
  );
}
