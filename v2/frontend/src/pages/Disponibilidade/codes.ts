/**
 * Constantes de códigos de disponibilidade.
 *
 * Códigos:
 * - E: 1 evento
 * - 2: ≥2 eventos
 * - P: Bloqueio parcial
 * - T: Bloqueio total
 * - X: Evento + bloqueio
 * - D: Deslocamento
 * - D1: Evento + deslocamento
 */

/**
 * Available code types for availability grid
 */
export type AvailabilityCode = 'E' | '2' | 'P' | 'T' | 'X' | 'D' | 'D1' | '';

/**
 * Labels dos códigos (fallback quando backend não retorna legend).
 */
export const CODE_LABEL: Record<AvailabilityCode, string> = {
  E: '1 evento',
  '2': '≥2 eventos',
  P: 'Bloqueio parcial',
  T: 'Bloqueio total',
  X: 'Evento + bloqueio',
  D: 'Deslocamento',
  D1: 'Evento + deslocamento',
  '': '', // Vazio (célula sem código)
};

/**
 * Classes CSS por código (Tailwind).
 */
export const CODE_CLASS: Record<AvailabilityCode, string> = {
  E: 'bg-green-100 text-green-800 hover:bg-green-200',
  '2': 'bg-green-500 text-white hover:bg-green-600',
  P: 'bg-yellow-100 text-yellow-800 hover:bg-yellow-200',
  T: 'bg-red-100 text-red-800 hover:bg-red-200',
  X: 'bg-orange-300 text-orange-900 hover:bg-orange-400',
  D: 'bg-gray-100 text-gray-600 hover:bg-gray-200',
  D1: 'bg-blue-100 text-blue-800 hover:bg-blue-200',
  '': 'bg-white hover:bg-gray-50', // Vazio
};
