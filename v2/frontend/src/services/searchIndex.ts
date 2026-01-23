/**
 * AS v2 - Search Index Service (Issue #418)
 *
 * Client-side search index using Fuse.js for instant search.
 * Provides fuzzy matching with configurable threshold.
 *
 * Usage:
 * ```ts
 * import { searchIndex } from '../services/searchIndex';
 *
 * // Index data
 * await searchIndex.index('municipios', data, { keys: ['nome', 'uf'] });
 *
 * // Search
 * const results = searchIndex.search('municipios', 'Fort', 10);
 * ```
 */

import Fuse, { type IFuseOptions, type FuseResult, type FuseResultMatch } from 'fuse.js';

/** Options for indexing data */
export interface IndexOptions {
  keys?: string[];
  threshold?: number;
}

/** Search result with score and matches */
export type SearchResult<T> = T & {
  _score: number | undefined;
  _matches: readonly FuseResultMatch[] | undefined;
};

/** Generic record type for indexed data */
type IndexableRecord = Record<string, unknown>;

class SearchIndex {
  private indices: Record<string, Fuse<IndexableRecord>>;
  private data: Record<string, IndexableRecord[]>;

  constructor() {
    this.indices = {};
    this.data = {};
  }

  /**
   * Index data for a specific key.
   * @param key - Index identifier (e.g., 'municipios')
   * @param data - Array of objects to index
   * @param options - Fuse.js options
   */
  async index<T extends IndexableRecord>(
    key: string,
    data: T[],
    options: IndexOptions = {}
  ): Promise<void> {
    this.data[key] = data;

    const fuseOptions: IFuseOptions<T> = {
      keys: options.keys || ['nome', 'titulo', 'descricao'],
      threshold: options.threshold || 0.3,
      includeScore: true,
      includeMatches: true,
      minMatchCharLength: 2,
    };

    this.indices[key] = new Fuse(data, fuseOptions) as Fuse<IndexableRecord>;
  }

  /**
   * Search in a specific index.
   * @param key - Index identifier
   * @param query - Search query
   * @param limit - Max results
   * @returns Search results with score and matches
   */
  search<T extends IndexableRecord>(
    key: string,
    query: string,
    limit: number = 10
  ): SearchResult<T>[] {
    const index = this.indices[key];
    if (!index || !query || query.length < 2) return [];

    const results = index.search(query) as FuseResult<T>[];

    return results
      .slice(0, limit)
      .map((result) => ({
        ...result.item,
        _score: result.score,
        _matches: result.matches,
      }));
  }

  /**
   * Search across all indexed data.
   * @param query - Search query
   * @param limitPerIndex - Max results per index
   * @returns Results grouped by index key
   */
  searchAll<T extends IndexableRecord>(
    query: string,
    limitPerIndex: number = 5
  ): Record<string, SearchResult<T>[]> {
    const results: Record<string, SearchResult<T>[]> = {};

    for (const key of Object.keys(this.indices)) {
      const indexResults = this.search<T>(key, query, limitPerIndex);
      if (indexResults.length > 0) {
        results[key] = indexResults;
      }
    }

    return results;
  }

  /**
   * Get raw data for an index.
   * @param key - Index identifier
   * @returns Original data array
   */
  getData<T extends IndexableRecord>(key: string): T[] {
    return (this.data[key] as T[]) || [];
  }

  /**
   * Check if index exists.
   * @param key - Index identifier
   */
  hasIndex(key: string): boolean {
    return !!this.indices[key];
  }

  /**
   * Get count of indexed items.
   * @param key - Index identifier
   */
  getCount(key: string): number {
    return this.data[key]?.length || 0;
  }

  /**
   * Clear index(es).
   * @param key - Optional specific index to clear. If omitted, clears all.
   */
  clear(key?: string): void {
    if (key) {
      delete this.indices[key];
      delete this.data[key];
    } else {
      this.indices = {};
      this.data = {};
    }
  }
}

// Singleton instance
export const searchIndex = new SearchIndex();
export default searchIndex;
