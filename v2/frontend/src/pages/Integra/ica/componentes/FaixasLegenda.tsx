/**
 * Legenda das faixas do ICA: cor, nome, faixa de valores e o que fazer, mais a meta de gestão.
 * A `FaixasLegendaCurta` é uma linha só, para os gráficos das outras telas.
 */
import type { JSX } from 'react';

import { ESTRATOS, META_ICA } from '../calculo';
import { COR_ESTRATO } from './estilos';

export function FaixasLegenda(): JSX.Element {
  return (
    <div>
      <ul aria-label="Faixas do ICA" className="m-0 grid list-none gap-2 p-0 sm:grid-cols-2 xl:grid-cols-4">
        {ESTRATOS.map((e) => (
          <li
            key={e.chave}
            className="rounded p-2 text-sm"
            style={{ background: COR_ESTRATO[e.chave].fundo, color: COR_ESTRATO[e.chave].texto }}
          >
            <span className="flex items-center gap-2 font-semibold">
              <span
                aria-hidden="true"
                className="inline-block h-3 w-3 shrink-0 rounded-sm"
                style={{ background: COR_ESTRATO[e.chave].forte }}
              />
              {e.nome}: {e.faixa}
            </span>
            <span className="mt-1 block">{e.orientacao}</span>
          </li>
        ))}
      </ul>
      <p className="mb-0 mt-2 text-sm">
        Meta: todos entre {META_ICA.minimo} e {META_ICA.maximo}. 100 é a carga média da equipe.
      </p>
    </div>
  );
}

/**
 * Uma linha: nome e números de cada cor do fundo, e o que são os traços. Nas barras (`BarraIca`) o
 * traço preto é o 100; na dispersão (`FaixaDispersao`) os traços pretos são o menor e o maior ICA.
 */
export function FaixasLegendaCurta({ grafico = 'barras' }: { grafico?: 'barras' | 'dispersao' }): JSX.Element {
  const faixas = [...ESTRATOS].reverse().map((e) => `${e.faixa} ${e.nome}`);
  return grafico === 'dispersao' ? (
    <p className="mb-2 text-sm">
      Fundo do gráfico: {faixas.join(' · ')}. Traço fino = divisa entre faixas; traços pretos = menor e maior ICA;
      bolinha = média.
    </p>
  ) : (
    <p className="mb-2 text-sm">
      Fundo das barras: {faixas.join(' · ')}. Traço fino = divisa entre faixas; traço preto = 100, a média da equipe.
    </p>
  );
}
