/**
 * Brazilian geography constants
 *
 * Issue #438, #441: Centralizar lista de UFs
 */

// All 27 Brazilian states
export const UF_LIST = [
  'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO',
  'MA', 'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI',
  'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO',
];

// Northeast region (9 states) - Aprender project scope
export const UF_NORDESTE = [
  'AL', 'BA', 'CE', 'MA', 'PB', 'PE', 'PI', 'RN', 'SE',
];

// Helper to create options for Select components
export const UF_OPTIONS = UF_LIST.map(uf => ({ value: uf, label: uf }));
export const UF_NORDESTE_OPTIONS = UF_NORDESTE.map(uf => ({ value: uf, label: uf }));
