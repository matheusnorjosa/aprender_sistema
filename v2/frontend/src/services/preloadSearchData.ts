/**
 * AS v2 - Preload Search Data (Issue #418)
 *
 * Preloads frequently used data for instant search.
 * Called after successful login to populate the search index.
 *
 * Usage:
 * ```ts
 * import { preloadSearchData } from '../services/preloadSearchData';
 *
 * // After login
 * await preloadSearchData();
 * ```
 */

import { fetchAPI } from '../api/config';
import { searchIndex } from './searchIndex';

/** Stats returned from preload operation */
export interface PreloadStats {
  municipios?: number;
  projetos?: number;
  usuarios?: number;
  tiposEvento?: number;
  skipped?: boolean;
  error?: string;
}

// Cache timestamp to avoid reloading too frequently
let lastLoadTime = 0;
const MIN_RELOAD_INTERVAL = 5 * 60 * 1000; // 5 minutes

/**
 * Preload search data from API endpoints.
 * @param force - Force reload even if recently loaded
 * @returns Stats about loaded data
 */
export async function preloadSearchData(force: boolean = false): Promise<PreloadStats> {
  const now = Date.now();

  // Skip if recently loaded (unless forced)
  if (!force && lastLoadTime && now - lastLoadTime < MIN_RELOAD_INTERVAL) {
    console.log('[SearchIndex] Skipping preload - recently loaded');
    return { skipped: true };
  }

  try {
    // Load data in parallel for performance
    // Note: api instance already has baseURL '/api', so we use relative paths
    type R = Record<string, unknown>;
    const [municipios, projetos, usuarios, tiposEvento] = await Promise.all([
      fetchAPI<R[]>('/options/municipios/').catch(() => [] as R[]),
      fetchAPI<R[]>('/options/projetos/').catch(() => [] as R[]),
      fetchAPI<R[]>('/options/usuarios/').catch(() => [] as R[]),
      fetchAPI<R[]>('/options/tipos-evento/').catch(() => [] as R[]),
    ]);

    // Index for instant search
    await searchIndex.index('municipios', municipios, {
      keys: ['nome', 'uf'],
      threshold: 0.2,
    });

    await searchIndex.index('projetos', projetos, {
      keys: ['nome', 'codigo'],
      threshold: 0.2,
    });

    await searchIndex.index('usuarios', usuarios, {
      keys: ['nome', 'email', 'username'],
      threshold: 0.3,
    });

    await searchIndex.index('tiposEvento', tiposEvento, {
      keys: ['nome'],
      threshold: 0.2,
    });

    lastLoadTime = now;

    const stats: PreloadStats = {
      municipios: Array.isArray(municipios) ? municipios.length : 0,
      projetos: Array.isArray(projetos) ? projetos.length : 0,
      usuarios: Array.isArray(usuarios) ? usuarios.length : 0,
      tiposEvento: Array.isArray(tiposEvento) ? tiposEvento.length : 0,
    };

    console.log('[SearchIndex] Preloaded:', stats);
    return stats;
  } catch (error) {
    console.error('[SearchIndex] Preload failed:', error);
    return { error: error instanceof Error ? error.message : 'Unknown error' };
  }
}

/**
 * Clear search index and reset timestamp.
 */
export function clearSearchData(): void {
  searchIndex.clear();
  lastLoadTime = 0;
}

export default preloadSearchData;
