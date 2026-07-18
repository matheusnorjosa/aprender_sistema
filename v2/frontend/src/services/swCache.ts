/**
 * Limpeza do Cache Storage do Service Worker (Issue #1461).
 *
 * O SW (`public/sw.js`) mantém caches de API nomeados `aprender-v2-api-*`. Como
 * eles podem conter respostas de `/api/me/*` de um usuário anterior, precisam ser
 * removidos no logout — senão, offline e em dispositivo compartilhado, a identidade
 * antiga pode ser servida do cache. Os caches de assets estáticos podem permanecer.
 */

/** Prefixo dos caches de API do SW (espelha `API_CACHE_NAME` em public/sw.js). */
const API_CACHE_PREFIX = 'aprender-v2-api-';

/**
 * Remove todos os caches de API do SW. No-op seguro quando o Cache Storage não
 * está disponível (SSR, navegador sem suporte, jsdom) ou quando a API falha —
 * o logout nunca deve travar por causa disso.
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
