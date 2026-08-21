import type { PaginatedResponse } from '../types/common';

/**
 * Normaliza uma resposta de lista para `T[]`.
 *
 * Vários endpoints de "options" do DAT retornam ora um array puro, ora uma
 * `PaginatedResponse` (`{ results }`), e os tipos do client nem sempre refletem
 * isso. As páginas antes faziam `(x as any).results || x || []` — este helper
 * faz o mesmo de forma type-safe (sem `any`): array → o próprio; paginado →
 * `results`; nulo/indefinido → `[]`.
 */
export function unwrapList<T>(data: T[] | PaginatedResponse<T> | null | undefined): T[] {
  if (Array.isArray(data)) return data;
  if (data && Array.isArray(data.results)) return data.results;
  return [];
}
