/**
 * AS v2 - useDebouncedValue Hook (Issue #418)
 *
 * Simple hook for debouncing a value.
 * Used with instant search to delay search until typing stops.
 *
 * Usage:
 * ```tsx
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
 * @param value - Value to debounce
 * @param delay - Delay in milliseconds (default: 300)
 * @returns Debounced value
 */
export function useDebouncedValue<T>(value: T, delay: number = 300): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

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
