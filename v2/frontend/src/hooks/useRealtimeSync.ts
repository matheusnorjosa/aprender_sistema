/**
 * Hook for real-time data synchronization across tabs and devices.
 *
 * Combines two sync strategies:
 * - **BroadcastChannel** (instant): other tabs in the same browser
 * - **HTTP Polling** (≤5s): other devices (phone ↔ computer)
 *
 * Built on top of the existing usePolling hook and syncChannel service.
 *
 * Usage:
 *   const { data, loading, lastUpdated, forceRefresh } = useRealtimeSync({
 *     channel: 'solicitacoes',
 *     fetchFn: () => listSolicitacoes(filters),
 *     pollingIntervalMs: TIMING.SYNC_POLL_INTERVAL_MS,
 *     enabled: true,
 *   });
 *
 * @module hooks/useRealtimeSync
 * @see Epic #1032, Issue #1033
 */

import { useCallback, useEffect, useRef, useState } from 'react';

import { syncChannel } from '../services/syncChannel';
import { deduplicatedFetch } from '../utils/request';
import { usePolling } from './usePolling';

export interface UseRealtimeSyncOptions<T> {
  /** BroadcastChannel name (e.g. 'solicitacoes', 'availability') */
  channel: string;
  /** Async function that fetches data from the API */
  fetchFn: () => Promise<T>;
  /** Polling interval in ms (default 5000) */
  pollingIntervalMs?: number;
  /** Enable/disable sync (e.g. based on auth state) */
  enabled?: boolean;
}

export interface UseRealtimeSyncResult<T> {
  /** Latest fetched data (null until first fetch) */
  data: T | null;
  /** True during fetch (initial or refresh) */
  loading: boolean;
  /** Timestamp of last successful fetch */
  lastUpdated: number | null;
  /** Trigger an immediate refetch */
  forceRefresh: () => void;
}

export function useRealtimeSync<T>(
  options: UseRealtimeSyncOptions<T>,
): UseRealtimeSyncResult<T> {
  const {
    channel,
    fetchFn,
    pollingIntervalMs = 5_000,
    enabled = true,
  } = options;

  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<number | null>(null);

  // Keep fetchFn ref stable to avoid stale closures
  const fetchFnRef = useRef(fetchFn);
  fetchFnRef.current = fetchFn;

  const mountedRef = useRef(true);
  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  // Core fetch with deduplication and loading state
  const doFetch = useCallback(async () => {
    if (!mountedRef.current) return;

    setLoading(true);
    try {
      const result = await deduplicatedFetch(
        `sync:${channel}`,
        () => fetchFnRef.current(),
      );
      if (mountedRef.current) {
        setData(result);
        setLastUpdated(Date.now());
      }
    } catch {
      // Silently ignore polling errors (network blips, etc.)
      // The previous data remains displayed until next successful fetch
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [channel]);

  // Strategy 1: HTTP Polling (cross-device sync)
  usePolling(doFetch, {
    enabled,
    intervalMs: pollingIntervalMs,
    events: [`${channel}:refresh`],
  });

  // Strategy 2: BroadcastChannel (cross-tab instant sync)
  useEffect(() => {
    if (!enabled) return;

    const unsub = syncChannel.subscribe(channel, () => {
      doFetch();
    });

    return unsub;
  }, [channel, enabled, doFetch]);

  const forceRefresh = useCallback(() => {
    doFetch();
  }, [doFetch]);

  return { data, loading, lastUpdated, forceRefresh };
}
