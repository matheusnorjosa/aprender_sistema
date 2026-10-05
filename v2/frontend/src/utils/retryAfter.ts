import { TIMING } from '../constants/timing';

/**
 * Quanto esperar depois de um 429 (muitas requisições), em ms; `null` se o erro não é 429.
 *
 * O `fetchAPI` anota `retryAfter` no erro a partir do cabeçalho `Retry-After` (o
 * DRF manda; o 429 do nginx não). Sem o cabeçalho vale `TIMING.POLL_PAUSA_429_PADRAO_MS`.
 */
export function pausaDo429Ms(error: unknown): number | null {
  const erro = error as { status?: number; retryAfter?: number } | null | undefined;
  if (erro?.status !== 429) return null;
  const segundos = erro.retryAfter;
  return segundos && segundos > 0 ? segundos * 1000 : TIMING.POLL_PAUSA_429_PADRAO_MS;
}
