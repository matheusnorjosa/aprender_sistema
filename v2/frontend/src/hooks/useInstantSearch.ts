/**
 * AS v2 - useInstantSearch Hook (Issue #418)
 *
 * Hook for instant search using client-side Fuse.js index.
 * Provides fast, fuzzy search without server roundtrips.
 *
 * Usage:
 * ```tsx
 * const { results, isSearching, query } = useInstantSearch('municipios', searchQuery, {
 *   debounceMs: 150,
 *   limit: 10,
 *   minLength: 2,
 * });
 * ```
 */

import { useState, useEffect } from 'react';
import { useDebouncedValue } from './useDebouncedValue';
import { searchIndex, type SearchResult } from '../services/searchIndex';

/**
 * Options for instant search
 */
export interface InstantSearchOptions {
  debounceMs?: number;
  limit?: number;
  minLength?: number;
}

/**
 * Return type for useInstantSearch
 */
export interface InstantSearchReturn<T> {
  results: SearchResult<T>[];
  isSearching: boolean;
  query: string;
  hasIndex: boolean;
}

/**
 * Options for global search
 */
export interface GlobalSearchOptions {
  debounceMs?: number;
  limitPerIndex?: number;
  minLength?: number;
}

/**
 * Return type for useGlobalSearch
 */
export interface GlobalSearchReturn {
  results: Record<string, SearchResult<unknown>[]>;
  isSearching: boolean;
  query: string;
}

/**
 * Instant search hook with debounce.
 * @param indexKey - Search index key (e.g., 'municipios')
 * @param query - Search query string
 * @param options - Search options
 */
export function useInstantSearch<T extends Record<string, unknown>>(
  indexKey: string,
  query: string,
  options: InstantSearchOptions = {}
): InstantSearchReturn<T> {
  const { debounceMs = 150, limit = 10, minLength = 2 } = options;

  const debouncedQuery = useDebouncedValue(query, debounceMs);
  const [results, setResults] = useState<SearchResult<T>[]>([]);
  const [isSearching, setIsSearching] = useState<boolean>(false);

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
      const searchResults = searchIndex.search<T>(indexKey, debouncedQuery, limit);
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
 * @param query - Search query string
 * @param options - Search options
 */
export function useGlobalSearch(
  query: string,
  options: GlobalSearchOptions = {}
): GlobalSearchReturn {
  const { debounceMs = 150, limitPerIndex = 5, minLength = 2 } = options;

  const debouncedQuery = useDebouncedValue(query, debounceMs);
  const [results, setResults] = useState<Record<string, SearchResult<unknown>[]>>({});
  const [isSearching, setIsSearching] = useState<boolean>(false);

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
