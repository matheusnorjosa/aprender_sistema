import { useEffect, useRef } from 'react';

export interface UsePollingOptions {
  /** Whether polling is active. When false, no fetching or intervals run. */
  enabled: boolean;
  /** Polling interval in milliseconds. */
  intervalMs: number;
  /** Custom DOM events that trigger an immediate fetch (e.g. 'notificacoes:refresh'). */
  events?: string[];
}

/**
 * Generic polling hook with Page Visibility API integration.
 *
 * Features:
 * - Pauses polling when browser tab is hidden
 * - Resumes with immediate fetch when tab becomes visible
 * - Listens for custom window events to trigger immediate fetches
 * - Uses ref for fetchFn to avoid stale closures without effect restarts
 * - Guards against calls after unmount
 *
 * @param fetchFn - Async function to call on each poll tick. Use a stable
 *   closure that reads state via refs or captures current values.
 * @param options - Polling configuration.
 */
export function usePolling(
  fetchFn: () => void | Promise<void>,
  options: UsePollingOptions,
): void {
  const { enabled, intervalMs, events } = options;

  // Always call the latest fetchFn without restarting the effect
  const fetchRef = useRef(fetchFn);
  fetchRef.current = fetchFn;

  // Guard against calls after unmount
  const mountedRef = useRef(true);
  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  // Stable key for events dependency (avoids array reference instability)
  const eventsKey = events?.join(',') ?? '';

  useEffect(() => {
    if (!enabled) return;

    let intervalId: ReturnType<typeof setInterval> | null = null;

    const doFetch = () => {
      if (mountedRef.current) {
        fetchRef.current();
      }
    };

    const startPolling = () => {
      if (!intervalId) {
        intervalId = setInterval(doFetch, intervalMs);
      }
    };

    const stopPolling = () => {
      if (intervalId) {
        clearInterval(intervalId);
        intervalId = null;
      }
    };

    const handleVisibility = () => {
      if (document.hidden) {
        stopPolling();
      } else {
        doFetch();
        startPolling();
      }
    };

    // Page Visibility API
    document.addEventListener('visibilitychange', handleVisibility);

    // Initial fetch + start polling if tab is visible
    doFetch();
    if (!document.hidden) startPolling();

    // Custom events (e.g. 'notificacoes:refresh')
    const currentEvents = eventsKey ? eventsKey.split(',') : [];
    for (const event of currentEvents) {
      window.addEventListener(event, doFetch);
    }

    return () => {
      stopPolling();
      document.removeEventListener('visibilitychange', handleVisibility);
      for (const event of currentEvents) {
        window.removeEventListener(event, doFetch);
      }
    };
  }, [enabled, intervalMs, eventsKey]);
}
