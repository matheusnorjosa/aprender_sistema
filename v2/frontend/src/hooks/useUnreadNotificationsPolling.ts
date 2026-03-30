import { useState, useEffect, useRef, useCallback } from 'react';
import toast from 'react-hot-toast';
import { deduplicatedFetch } from '../utils/request';
import { isAuthError } from '../utils/errors';
import { storageKeys, getStorageInt, setStorageInt } from '../utils/storage';
import { getNotificacoesNaoLidasCount } from '../api/acoesNotificacao';
import { usePolling } from './usePolling';
import { TIMING } from '../constants';
import logger from '../utils/logger';

// Stable events array (defined outside component to avoid re-renders)
const NOTIF_EVENTS = ['notificacoes:refresh'];

interface UseUnreadNotificationsPollingOptions {
  enabled: boolean;
  userId: number | string | undefined;
}

interface UseUnreadNotificationsPollingReturn {
  unreadNotifications: number;
}

/**
 * Polls unread notification count and shows a toast when new ones arrive.
 * Persists lastNotifCount per user in localStorage.
 */
export function useUnreadNotificationsPolling({
  enabled,
  userId,
}: UseUnreadNotificationsPollingOptions): UseUnreadNotificationsPollingReturn {
  const [unreadNotifications, setUnreadNotifications] = useState(0);
  const [lastNotifCount, setLastNotifCount] = useState(-1);
  const [cooldownUntil, setCooldownUntil] = useState(0);

  const mountedRef = useRef(true);
  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  // Refs to avoid stale closures
  const lastNotifRef = useRef(lastNotifCount);
  lastNotifRef.current = lastNotifCount;
  const cooldownRef = useRef(cooldownUntil);
  cooldownRef.current = cooldownUntil;

  // Sync with localStorage when userId changes
  useEffect(() => {
    if (!userId) return;
    setUnreadNotifications(0);
    setCooldownUntil(0);
    setLastNotifCount(getStorageInt(storageKeys.notifUnread(userId), -1));
  }, [userId]);

  const dedupKey = userId ? `unread-count:${userId}` : 'unread-count:anon';

  const fetchUnread = useCallback(async () => {
    try {
      const data = await deduplicatedFetch(dedupKey, getNotificacoesNaoLidasCount);
      if (!mountedRef.current) return;
      setUnreadNotifications(data.count);

      const now = Date.now();
      if (data.count > lastNotifRef.current && lastNotifRef.current >= 0 && now > cooldownRef.current) {
        const diff = data.count - lastNotifRef.current;
        toast(`${diff} nova${diff > 1 ? 's' : ''} notificação${diff > 1 ? 'ões' : ''}`, {
          icon: '🔔',
          duration: 5000,
          id: 'new-notifications',
        });
        setCooldownUntil(now + TIMING.TOAST_COOLDOWN_MS);
      }

      if (data.count !== lastNotifRef.current) {
        setLastNotifCount(data.count);
        if (userId) setStorageInt(storageKeys.notifUnread(userId), data.count);
      }
    } catch (error) {
      if (isAuthError(error)) return;
      logger.error('[Notifications] Polling error:', error);
    }
  }, [dedupKey, userId]);

  usePolling(fetchUnread, {
    enabled,
    intervalMs: TIMING.NOTIF_POLL_INTERVAL_MS,
    events: NOTIF_EVENTS,
  });

  return { unreadNotifications };
}
