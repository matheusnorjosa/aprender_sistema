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

/** Quantos nomes o aviso de reconexão lista antes de resumir em "e mais N". */
const RECONNECT_NAMES_SHOWN = 3;

function reconnectMessage(total: number, users: { nome: string }[]): string {
  const nomes = users.slice(0, RECONNECT_NAMES_SHOWN).map((u) => u.nome).join(', ');
  const resto = total > RECONNECT_NAMES_SHOWN ? ` e mais ${total - RECONNECT_NAMES_SHOWN}` : '';
  const sujeito = total === 1 ? '1 pessoa precisa' : `${total} pessoas precisam`;
  return `${sujeito} reconectar a conta Google: ${nomes}${resto}.`;
}

/**
 * Polls GCal alerts summary and shows a toast when new errors appear.
 * Persists lastErrorsCount in localStorage to survive page reloads.
 *
 * Também avisa quem precisa reconectar a conta Google (#2039): um toast por
 * conjunto de ids — o polling seguinte com as mesmas pessoas não repete o aviso.
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
  // Ids (ordenados) do último aviso de reconexão; '' = nenhum aviso ativo.
  const reconnectKeyRef = useRef('');

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

      const reconnect = data.google_reconnect;
      const reconnectKey =
        reconnect && reconnect.count > 0
          ? reconnect.users.map((u) => u.id).sort((a, b) => a - b).join(',')
          : '';
      if (reconnect && reconnectKey && reconnectKey !== reconnectKeyRef.current) {
        toast(reconnectMessage(reconnect.count, reconnect.users), {
          icon: '⚠️',
          duration: 10000,
          id: 'gcal-google-reconnect',
        });
      }
      reconnectKeyRef.current = reconnectKey;
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
