/**
 * Limpeza do Cache Storage do Service Worker (Issue #1461).
 *
 * Até a v4, o SW (`public/sw.js`) mantinha caches de API nomeados `aprender-v2-api-*`, com
 * respostas que dependem de quem está logado. Desde o SEG-54 ele não guarda nem serve
 * resposta de API, e apaga esses caches ao ativar. Esta limpeza fica para as sobras: um SW
 * antigo ainda em execução pode regravar o cache depois da ativação do novo. Roda no logout
 * e a cada carregamento da página (`main.tsx`). Os caches de assets estáticos permanecem.
 */

/** Prefixo dos caches de API do SW (espelha `API_CACHE_PREFIX` em public/sw.js). */
const API_CACHE_PREFIX = 'aprender-v2-api-';

/**
 * Remove todos os caches de API do SW. No-op seguro quando o Cache Storage não
 * está disponível (SSR, navegador sem suporte, jsdom) ou quando a API falha —
 * nem o logout nem o carregamento devem travar por causa disso.
 */
export async function clearApiCaches(): Promise<void> {
  if (typeof caches === 'undefined') return;
  try {
    const keys = await caches.keys();
    await Promise.all(
      keys.filter((name) => name.startsWith(API_CACHE_PREFIX)).map((name) => caches.delete(name)),
    );
  } catch {
    // Cache Storage indisponível/erro — segue o logout sem bloquear.
  }
}
