/**
 * Brazilian geography constants
 *
 * Issue #438, #441: Centralizar lista de UFs
 */

import type { UFCode } from '../types';

/** Select option type */
export interface UFOption {
  value: UFCode;
  label: UFCode;
}

/** All 27 Brazilian states */
export const UF_LIST: readonly UFCode[] = [
  'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO',
  'MA', 'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI',
  'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO',
] as const;

/** Northeast region (9 states) - Aprender project scope */
export const UF_NORDESTE: readonly UFCode[] = [
  'AL', 'BA', 'CE', 'MA', 'PB', 'PE', 'PI', 'RN', 'SE',
] as const;

/** UF options for Select components (all states) */
export const UF_OPTIONS: UFOption[] = UF_LIST.map(uf => ({ value: uf, label: uf }));

/** UF options for Select components (Northeast only) */
export const UF_NORDESTE_OPTIONS: UFOption[] = UF_NORDESTE.map(uf => ({ value: uf, label: uf }));
