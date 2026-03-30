import { useState, useEffect, useRef, useCallback } from 'react';
import toast from 'react-hot-toast';
import { deduplicatedFetch } from '../utils/request';
import { isAuthError } from '../utils/errors';
import { storageKeys, getStorageInt, setStorageInt } from '../utils/storage';
import { getAlertsSummary } from '../api/gcal';
import { usePolling } from './usePolling';
import { TIMING } from '../constants';
import logger from '../utils/logger';

interface AlertsSummary {
  errors: number;
  pending: number;
  published: number;
  none: number;
}

interface UseGCalAlertsPollingOptions {
  enabled: boolean;
}

interface UseGCalAlertsPollingReturn {
  alerts: AlertsSummary;
}

/**
 * Polls GCal alerts summary and shows a toast when new errors appear.
 * Persists lastErrorsCount in localStorage to survive page reloads.
 */
export function useGCalAlertsPolling({ enabled }: UseGCalAlertsPollingOptions): UseGCalAlertsPollingReturn {
  const [alerts, setAlerts] = useState<AlertsSummary>({ errors: 0, pending: 0, published: 0, none: 0 });
  const [lastErrorsCount, setLastErrorsCount] = useState(0);
  const [cooldownUntil, setCooldownUntil] = useState(0);

  const mountedRef = useRef(true);
  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  // Refs to avoid stale closures in polling callback
  const lastErrorsRef = useRef(lastErrorsCount);
  lastErrorsRef.current = lastErrorsCount;
  const cooldownRef = useRef(cooldownUntil);
  cooldownRef.current = cooldownUntil;

  // Load persisted value on mount
  useEffect(() => {
    setLastErrorsCount(getStorageInt(storageKeys.gcalErrors, 0));
  }, []);

  const fetchAlerts = useCallback(async () => {
    try {
      const data = await deduplicatedFetch('gcal-alerts', getAlertsSummary);
      if (!mountedRef.current) return;
      setAlerts(data);

      const now = Date.now();
      if (data.errors > lastErrorsRef.current && now > cooldownRef.current) {
        toast.error(
          `Novos erros de publicação detectados (${lastErrorsRef.current} → ${data.errors})`,
          { duration: 5000 },
        );
        setCooldownUntil(now + TIMING.TOAST_COOLDOWN_MS);
      }

      if (data.errors !== lastErrorsRef.current) {
        setLastErrorsCount(data.errors);
        setStorageInt(storageKeys.gcalErrors, data.errors);
      }
    } catch (error) {
      if (isAuthError(error)) return;
      logger.error('[Alerts] Erro ao buscar alertas:', error);
    }
  }, []);

  usePolling(fetchAlerts, {
    enabled,
    intervalMs: TIMING.GCAL_POLL_INTERVAL_MS,
  });

  return { alerts };
}
