/**
 * Timing constants - Intervals, delays, timeouts
 *
 * Issue #438: Criar estrutura de constantes frontend
 */

export const TIMING = {
  // Polling intervals (separated by domain for independent tuning)
  GCAL_POLL_INTERVAL_MS: 30_000, // 30 seconds
  NOTIF_POLL_INTERVAL_MS: 30_000, // 30 seconds

  // Cooldowns
  TOAST_COOLDOWN_MS: 120000, // 2 minutes

  // CSRF
  CSRF_TOKEN_TTL_MS: 30 * 60 * 1000, // 30 minutes

  // Debounce
  DEBOUNCE_DEFAULT_MS: 300,
  DEBOUNCE_SEARCH_MS: 400,

  // Delays
  GCAL_DETAIL_LOAD_DELAY_MS: 2000,
} as const;
