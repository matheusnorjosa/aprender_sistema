/**
 * Request utilities: deduplication and cancellation.
 */

const inFlight = new Map<string, Promise<unknown>>();

/**
 * Deduplicate concurrent fetches by key.
 * If a fetch with the same key is already in flight, returns the existing promise
 * instead of starting a new request.
 *
 * @param key - Unique identifier for the request (e.g. 'unread-count', 'alerts-summary')
 * @param fetchFn - Function that performs the actual fetch
 * @returns The result of the fetch
 */
export function deduplicatedFetch<T>(key: string, fetchFn: () => Promise<T>): Promise<T> {
  const existing = inFlight.get(key);
  if (existing) return existing as Promise<T>;

  const promise = fetchFn().finally(() => { inFlight.delete(key); });
  inFlight.set(key, promise);
  return promise;
}

/**
 * Create an AbortController for use in React effects.
 * Call abort() in the effect cleanup to cancel pending requests.
 */
export function createAbortController(): { signal: AbortSignal; abort: () => void } {
  const controller = new AbortController();
  return { signal: controller.signal, abort: () => controller.abort() };
}
