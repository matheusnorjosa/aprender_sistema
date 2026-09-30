/**
 * Largura de tela nos testes (Programa C, C1).
 *
 * O jsdom não tem layout nem media query: o `matchMedia` de antes respondia `false` para
 * tudo, e toda coluna com `responsive` (ResponsiveTable) sumiria nos testes. Este mock
 * avalia `min-width` e `max-width` contra uma largura, 1280 px por padrão (desktop, com a
 * sidebar aberta), e `window.innerWidth` acompanha (o `useResponsive` lê dele).
 *
 * `definirLarguraTela(px)` muda a largura e avisa quem escuta (o `useBreakpoint` do AntD e
 * o evento `resize`). Chamada depois do render, embrulhe em `act`. O setup volta ao padrão
 * antes de cada teste.
 */
import { vi } from 'vitest';

export const LARGURA_PADRAO = 1280;

type Ouvinte = (evento: { matches: boolean; media: string }) => void;

let largura = LARGURA_PADRAO;
const escutadas = new Map<string, Set<Ouvinte>>();

const CONDICAO = /^\(\s*(min|max)-width\s*:\s*(\d+(?:\.\d+)?)px\s*\)$/;

/** `true` se a query casa com `px`. Só entende largura (`min`/`max`, com `and`); o resto é `false`. */
export function avaliarMidia(query: string, px: number): boolean {
  const partes = query
    .split(/\s+and\s+/i)
    .map((p) => p.trim())
    .filter((p) => !/^(only\s+)?(screen|all)$/i.test(p));
  if (partes.length === 0) return false;
  return partes.every((parte) => {
    const casou = CONDICAO.exec(parte);
    if (!casou) return false;
    const limite = Number(casou[2]);
    return casou[1] === 'min' ? px >= limite : px <= limite;
  });
}

function ouvintesDe(query: string): Set<Ouvinte> {
  let ouvintes = escutadas.get(query);
  if (!ouvintes) {
    ouvintes = new Set();
    escutadas.set(query, ouvintes);
  }
  return ouvintes;
}

function criarListaDeMidia(query: string): MediaQueryList {
  const ouvintes = ouvintesDe(query);
  const lista = {
    media: query,
    get matches() {
      return avaliarMidia(query, largura);
    },
    onchange: null,
    addListener: (fn: Ouvinte) => ouvintes.add(fn),
    removeListener: (fn: Ouvinte) => ouvintes.delete(fn),
    addEventListener: (_tipo: string, fn: Ouvinte) => ouvintes.add(fn),
    removeEventListener: (_tipo: string, fn: Ouvinte) => ouvintes.delete(fn),
    dispatchEvent: () => false,
  };
  return lista as unknown as MediaQueryList;
}

export const matchMediaDeTeste = vi.fn(criarListaDeMidia);

/** Muda a largura da tela do teste: `innerWidth`, media queries e evento `resize`. */
export function definirLarguraTela(px: number): void {
  const anterior = largura;
  largura = px;
  Object.defineProperty(window, 'innerWidth', { configurable: true, writable: true, value: px });
  for (const [query, ouvintes] of escutadas) {
    const agora = avaliarMidia(query, px);
    if (agora === avaliarMidia(query, anterior)) continue;
    for (const ouvinte of [...ouvintes]) ouvinte({ matches: agora, media: query });
  }
  window.dispatchEvent(new Event('resize'));
}
