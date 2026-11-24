/** Semáforo de Risco Municipal: por enquanto só o aviso (chega na próxima entrega, PR 3 do plano). */
import type { JSX } from 'react';

import { TelaEmConstrucao } from './TelaEmConstrucao';

export default function SemaforoEmBreve(): JSX.Element {
  return (
    <TelaEmConstrucao
      titulo="Semáforo de Risco Municipal"
      aviso="Em construção: o Semáforo chega na próxima entrega."
      comVolta
    />
  );
}
