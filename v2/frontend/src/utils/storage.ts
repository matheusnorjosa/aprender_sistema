/**
 * Centralized localStorage helpers.
 *
 * Provides typed get/set with error handling and namespaced keys.
 */

export const storageKeys = {
  gcalErrors: 'gcalAlertsLastErrors',
  notifUnread: (userId: number | string) => `notifLastUnread:${userId}`,
} as const;

export function getStorageInt(key: string, fallback: number): number {
  try {
    const raw = localStorage.getItem(key);
    if (raw === null) return fallback;
    const parsed = parseInt(raw, 10);
    return Number.isNaN(parsed) ? fallback : parsed;
  } catch {
    return fallback;
  }
}

export function setStorageInt(key: string, value: number): void {
  try {
    localStorage.setItem(key, value.toString());
  } catch {
    // quota exceeded or private browsing — silently ignore
  }
}
