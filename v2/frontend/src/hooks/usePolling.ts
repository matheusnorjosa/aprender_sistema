import { useCallback, useEffect, useRef, useState } from 'react';

export interface UsePollingOptions {
  /** Whether polling is active. When false, no fetching or intervals run. */
  enabled: boolean;
  /** Polling interval in milliseconds. */
  intervalMs: number;
  /** Custom DOM events that trigger an immediate fetch (e.g. 'notificacoes:refresh'). */
  events?: string[];
  /**
   * When false, skips the fetch-on-mount. The interval and the fetch-on-visible
   * (returning to a hidden tab) still run. Use it when the page already owns the
   * initial load elsewhere, to avoid a duplicate request on mount. Default true.
   */
  immediate?: boolean;
}

export interface UsePollingResult {
  /** True enquanto o polling está suspenso por `pausar` (ex.: depois de um 429). */
  pausado: boolean;
  /**
   * Suspende ticks, eventos e a busca ao voltar para a aba por `ms`. Ao fim do prazo o
   * polling retoma sozinho com uma busca. Chamar de novo troca o prazo.
   */
  pausar: (ms: number) => void;
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
 * - Nunca abre carga nova enquanto a anterior (aberta por este hook) está em voo: o
 *   tick é pulado; um evento que chega nesse meio-tempo refaz a busca uma vez no fim
 * - `pausar(ms)` suspende tudo por um prazo (429) e `pausado` permite avisar a pessoa
 *
 * @param fetchFn - Async function to call on each poll tick. Use a stable
 *   closure that reads state via refs or captures current values.
 * @param options - Polling configuration.
 */
export function usePolling(
  fetchFn: () => void | Promise<void>,
  options: UsePollingOptions,
): UsePollingResult {
  const { enabled, intervalMs, events, immediate = true } = options;

  // Always call the latest fetchFn without restarting the effect
  const fetchRef = useRef(fetchFn);
  fetchRef.current = fetchFn;
  const enabledRef = useRef(enabled);
  enabledRef.current = enabled;

  const emVooRef = useRef(false);
  const refazerRef = useRef(false);
  const pausaTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [pausado, setPausado] = useState(false);

  // Guard against calls after unmount
  const mountedRef = useRef(true);
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      if (pausaTimerRef.current) clearTimeout(pausaTimerRef.current);
      pausaTimerRef.current = null;
    };
  }, []);

  /** `porEvento`: algo mudou; se houver carga em voo, refaz uma vez quando ela terminar. */
  const buscar = useCallback((porEvento = false): void => {
    if (!mountedRef.current || pausaTimerRef.current) return;
    if (emVooRef.current) {
      if (porEvento) refazerRef.current = true;
      return;
    }
    const resultado = fetchRef.current();
    if (!(resultado instanceof Promise)) return;
    emVooRef.current = true;
    const aoTerminar = (): void => {
      emVooRef.current = false;
      if (refazerRef.current) {
        refazerRef.current = false;
        buscar();
      }
    };
    resultado.then(aoTerminar, aoTerminar);
  }, []);

  const pausar = useCallback((ms: number): void => {
    if (!mountedRef.current) return;
    if (pausaTimerRef.current) clearTimeout(pausaTimerRef.current);
    refazerRef.current = false;
    setPausado(true);
    pausaTimerRef.current = setTimeout(() => {
      pausaTimerRef.current = null;
      setPausado(false);
      // Aba oculta: quem busca é o retorno à aba (visibilitychange).
      if (enabledRef.current && !document.hidden) buscar();
    }, ms);
  }, [buscar]);

  // Stable key for events dependency (avoids array reference instability)
  const eventsKey = events?.join(',') ?? '';

  useEffect(() => {
    if (!enabled) return;

    let intervalId: ReturnType<typeof setInterval> | null = null;

    const doFetch = (): void => buscar();
    const doFetchPorEvento = (): void => buscar(true);

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

    // Initial fetch + start polling if tab is visible. `immediate: false` skips
    // only the mount fetch (the interval and fetch-on-visible still run).
    if (immediate) doFetch();
    if (!document.hidden) startPolling();

    // Custom events (e.g. 'notificacoes:refresh')
    const currentEvents = eventsKey ? eventsKey.split(',') : [];
    for (const event of currentEvents) {
      window.addEventListener(event, doFetchPorEvento);
    }

    return () => {
      stopPolling();
      document.removeEventListener('visibilitychange', handleVisibility);
      for (const event of currentEvents) {
        window.removeEventListener(event, doFetchPorEvento);
      }
    };
  }, [enabled, intervalMs, eventsKey, immediate, buscar]);

  return { pausado, pausar };
}
