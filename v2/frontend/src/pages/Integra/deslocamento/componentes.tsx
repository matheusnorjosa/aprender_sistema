/** Etiqueta da faixa de deslocamento: a cor sempre com o nome escrito (cores em `estilos.ts`). */
import type { JSX } from 'react';

import type { FaixaDeslocamento } from '../dados/deslocamento';
import { COR_FAIXA, rotuloDaFaixa } from './estilos';

export function EtiquetaFaixa({ faixa }: { faixa: FaixaDeslocamento }): JSX.Element {
  const cor = COR_FAIXA[faixa];
  return (
    <span className="inline-block rounded px-2 py-0.5 text-sm font-semibold" style={{ background: cor.fundo, color: cor.texto }}>
      {rotuloDaFaixa(faixa)}
    </span>
  );
}
