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

import api from '../api';
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
    const [municipios, projetos, usuarios, tiposEvento] = await Promise.all([
      api.get('/api/v1/options/municipios/').catch(() => ({ data: [] })),
      api.get('/api/v1/options/projetos/').catch(() => ({ data: [] })),
      api.get('/api/v1/options/usuarios/').catch(() => ({ data: [] })),
      api.get('/api/v1/options/tipos-evento/').catch(() => ({ data: [] })),
    ]);

    // Index for instant search
    await searchIndex.index('municipios', municipios.data, {
      keys: ['nome', 'uf'],
      threshold: 0.2,
    });

    await searchIndex.index('projetos', projetos.data, {
      keys: ['nome', 'codigo'],
      threshold: 0.2,
    });

    await searchIndex.index('usuarios', usuarios.data, {
      keys: ['nome', 'email', 'username'],
      threshold: 0.3,
    });

    await searchIndex.index('tiposEvento', tiposEvento.data, {
      keys: ['nome'],
      threshold: 0.2,
    });

    lastLoadTime = now;

    const stats: PreloadStats = {
      municipios: municipios.data.length,
      projetos: projetos.data.length,
      usuarios: usuarios.data.length,
      tiposEvento: tiposEvento.data.length,
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
