/**
 * AS v2 - Search Index Service (Issue #418)
 *
 * Client-side search index using Fuse.js for instant search.
 * Provides fuzzy matching with configurable threshold.
 *
 * Usage:
 * ```js
 * import { searchIndex } from '../services/searchIndex';
 *
 * // Index data
 * await searchIndex.index('municipios', data, { keys: ['nome', 'uf'] });
 *
 * // Search
 * const results = searchIndex.search('municipios', 'Fort', 10);
 * ```
 */

import Fuse from 'fuse.js';

class SearchIndex {
  constructor() {
    this.indices = {};
    this.data = {};
  }

  /**
   * Index data for a specific key.
   * @param {string} key - Index identifier (e.g., 'municipios')
   * @param {Array} data - Array of objects to index
   * @param {Object} options - Fuse.js options
   */
  async index(key, data, options = {}) {
    this.data[key] = data;
    this.indices[key] = new Fuse(data, {
      keys: options.keys || ['nome', 'titulo', 'descricao'],
      threshold: options.threshold || 0.3,
      includeScore: true,
      includeMatches: true,
      minMatchCharLength: 2,
    });
  }

  /**
   * Search in a specific index.
   * @param {string} key - Index identifier
   * @param {string} query - Search query
   * @param {number} limit - Max results
   * @returns {Array} Search results with score and matches
   */
  search(key, query, limit = 10) {
    const index = this.indices[key];
    if (!index || !query || query.length < 2) return [];

    return index
      .search(query)
      .slice(0, limit)
      .map((result) => ({
        ...result.item,
        _score: result.score,
        _matches: result.matches,
      }));
  }

  /**
   * Search across all indexed data.
   * @param {string} query - Search query
   * @param {number} limitPerIndex - Max results per index
   * @returns {Object} Results grouped by index key
   */
  searchAll(query, limitPerIndex = 5) {
    const results = {};
    for (const key of Object.keys(this.indices)) {
      const indexResults = this.search(key, query, limitPerIndex);
      if (indexResults.length > 0) {
        results[key] = indexResults;
      }
    }
    return results;
  }

  /**
   * Get raw data for an index.
   * @param {string} key - Index identifier
   * @returns {Array} Original data array
   */
  getData(key) {
    return this.data[key] || [];
  }

  /**
   * Check if index exists.
   * @param {string} key - Index identifier
   * @returns {boolean}
   */
  hasIndex(key) {
    return !!this.indices[key];
  }

  /**
   * Get count of indexed items.
   * @param {string} key - Index identifier
   * @returns {number}
   */
  getCount(key) {
    return this.data[key]?.length || 0;
  }

  /**
   * Clear index(es).
   * @param {string} [key] - Optional specific index to clear. If omitted, clears all.
   */
  clear(key) {
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
