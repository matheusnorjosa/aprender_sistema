/**
 * AS v2 - useInstantSearch Hook (Issue #418)
 *
 * Hook for instant search using client-side Fuse.js index.
 * Provides fast, fuzzy search without server roundtrips.
 *
 * Usage:
 * ```jsx
 * const { results, isSearching, query } = useInstantSearch('municipios', searchQuery, {
 *   debounceMs: 150,
 *   limit: 10,
 *   minLength: 2,
 * });
 * ```
 */

import { useState, useEffect } from 'react';
import { useDebouncedValue } from './useDebouncedValue';
import { searchIndex } from '../services/searchIndex';

/**
 * Instant search hook with debounce.
 * @param {string} indexKey - Search index key (e.g., 'municipios')
 * @param {string} query - Search query string
 * @param {Object} options - Search options
 * @returns {Object} { results, isSearching, query, hasIndex }
 */
export function useInstantSearch(indexKey, query, options = {}) {
  const { debounceMs = 150, limit = 10, minLength = 2 } = options;

  const debouncedQuery = useDebouncedValue(query, debounceMs);
  const [results, setResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);

  useEffect(() => {
    // Check minimum length
    if (!debouncedQuery || debouncedQuery.length < minLength) {
      setResults([]);
      return;
    }

    // Check if index exists
    if (!searchIndex.hasIndex(indexKey)) {
      setResults([]);
      return;
    }

    setIsSearching(true);

    // Local search is synchronous but wrap in microtask for UI smoothness
    queueMicrotask(() => {
      const searchResults = searchIndex.search(indexKey, debouncedQuery, limit);
      setResults(searchResults);
      setIsSearching(false);
    });
  }, [debouncedQuery, indexKey, limit, minLength]);

  return {
    results,
    isSearching,
    query: debouncedQuery,
    hasIndex: searchIndex.hasIndex(indexKey),
  };
}

/**
 * Search across all indexed data.
 * @param {string} query - Search query string
 * @param {Object} options - Search options
 * @returns {Object} { results, isSearching, query }
 */
export function useGlobalSearch(query, options = {}) {
  const { debounceMs = 150, limitPerIndex = 5, minLength = 2 } = options;

  const debouncedQuery = useDebouncedValue(query, debounceMs);
  const [results, setResults] = useState({});
  const [isSearching, setIsSearching] = useState(false);

  useEffect(() => {
    if (!debouncedQuery || debouncedQuery.length < minLength) {
      setResults({});
      return;
    }

    setIsSearching(true);

    queueMicrotask(() => {
      const searchResults = searchIndex.searchAll(debouncedQuery, limitPerIndex);
      setResults(searchResults);
      setIsSearching(false);
    });
  }, [debouncedQuery, limitPerIndex, minLength]);

  return {
    results,
    isSearching,
    query: debouncedQuery,
  };
}

export default useInstantSearch;
