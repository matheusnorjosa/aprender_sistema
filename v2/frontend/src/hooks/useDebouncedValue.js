/**
 * AS v2 - useDebouncedValue Hook (Issue #418)
 *
 * Simple hook for debouncing a value.
 * Used with instant search to delay search until typing stops.
 *
 * Usage:
 * ```jsx
 * const [query, setQuery] = useState('');
 * const debouncedQuery = useDebouncedValue(query, 150);
 *
 * useEffect(() => {
 *   if (debouncedQuery) {
 *     search(debouncedQuery);
 *   }
 * }, [debouncedQuery]);
 * ```
 */

import { useState, useEffect } from 'react';

/**
 * Debounce a value with configurable delay.
 * @param {any} value - Value to debounce
 * @param {number} delay - Delay in milliseconds (default: 300)
 * @returns {any} Debounced value
 */
export function useDebouncedValue(value, delay = 300) {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(timer);
    };
  }, [value, delay]);

  return debouncedValue;
}

export default useDebouncedValue;
