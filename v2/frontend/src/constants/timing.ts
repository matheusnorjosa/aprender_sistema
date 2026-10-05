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
  // #1452: checagem de disponibilidade no wizard. Constante própria (não reusar
  // SEARCH) para poder ajustar sem acoplar à busca; o gatilho é seleção, não digitação.
  DEBOUNCE_AVAILABILITY_CHECK_MS: 400,

  // Delays
  GCAL_DETAIL_LOAD_DELAY_MS: 2000,

  // Telas que se atualizam sozinhas (Epic #1032; liberação 2026-10). Cada tick é um ou
  // mais pedidos contra o limite por pessoa (throttle `user`, 6000/h): a 5 s a
  // Pré-agenda (3 pedidos por tick) estourava o limite antigo em ~25 min. Com a aba
  // oculta o polling para (hooks/usePolling.ts).
  LIST_POLL_INTERVAL_MS: 20_000, // listas: Aprovações e Pré-agenda
  GRADE_POLL_INTERVAL_MS: 30_000, // Grade Mensal (duas grades = 2 pedidos por tick)
  // Publicação por setor: só enquanto há publicação em voo (PENDING), 1 pedido por tick.
  PUBLICACAO_PENDENTE_POLL_MS: 5_000,
  // Pausa do polling depois de um 429 que veio sem o cabeçalho Retry-After.
  POLL_PAUSA_429_PADRAO_MS: 60_000,
} as const;
