/**
 * Validation constants - Character limits, min/max values
 *
 * Issue #438: Criar estrutura de constantes frontend
 */

export const VALIDATION = {
  // Character limits
  MAX_CHARS_SHORT: 50,
  MAX_CHARS_MEDIUM: 100,
  MAX_CHARS_LONG: 300,
  MAX_CHARS_TEXT: 500,
  MAX_CHARS_DESCRIPTION: 1000,

  // Numeric limits (ConfiguracoesPage)
  SESSION_COOKIE_AGE_MIN: 300,
  SESSION_COOKIE_AGE_MAX: 86400,
  TRAVEL_BUFFER_MIN: 30,
  TRAVEL_BUFFER_MAX: 480,
  BATCH_SIZE_MIN: 50,
  BATCH_SIZE_MAX: 1000,
} as const;
