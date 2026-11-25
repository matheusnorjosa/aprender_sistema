/**
 * O link de volta da ficha do município. A ficha abre de seis telas do Semáforo: quem abre passa no `state`
 * do link o endereço de onde veio (com a busca, ex.: `?gestora=`), e a ficha volta para lá com o nome da
 * tela. Sem origem conhecida (endereço digitado, recarga da página), volta ao Comitê.
 */
import { useLocation } from 'react-router';

const RAIZ = '/integra/semaforo';

/** As telas que abrem a ficha e o rótulo do link de volta para cada uma. */
const ROTULOS: Readonly<Record<string, string>> = {
  [RAIZ]: 'Voltar ao início do Semáforo',
  [`${RAIZ}/comite`]: 'Voltar ao Comitê',
  [`${RAIZ}/gestora`]: 'Voltar ao painel da gestora',
  [`${RAIZ}/pesquisa`]: 'Voltar à pesquisa do articulador',
  [`${RAIZ}/lider`]: 'Voltar aos indicadores da Líder',
  [`${RAIZ}/relatorio-mensal`]: 'Voltar ao relatório mensal',
};

export interface EstadoDaFicha {
  voltar: string;
}

/** O `state` do link que abre a ficha: o endereço da tela atual. */
export function useEstadoDaFicha(): EstadoDaFicha {
  const { pathname, search } = useLocation();
  return { voltar: `${pathname}${search}` };
}

/** Para onde a ficha volta e com que rótulo. O `state` vem do histórico: só vale uma das telas acima. */
export function voltarDaFicha(estado: unknown): { para: string; rotulo: string } {
  const voltar = (estado as { voltar?: unknown } | null)?.voltar;
  if (typeof voltar === 'string') {
    const rotulo = ROTULOS[(voltar.split('?')[0] ?? '').replace(/\/$/, '')];
    if (rotulo) return { para: voltar, rotulo };
  }
  return { para: `${RAIZ}/comite`, rotulo: 'Voltar ao Comitê' };
}
