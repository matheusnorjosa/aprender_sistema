/**
 * Pagination constants - Page sizes
 *
 * Issue #438: Criar estrutura de constantes frontend
 */

export const PAGE_SIZES = {
  TINY: 5,
  SMALL: 10,
  DEFAULT: 15,
  MEDIUM: 20,
  LARGE: 50,
  XLARGE: 100,
  ALL: 1000, // For "load all" scenarios
} as const;

export const DEFAULT_PAGE_SIZE: number = PAGE_SIZES.DEFAULT;

/** Type for valid page sizes */
export type PageSize = (typeof PAGE_SIZES)[keyof typeof PAGE_SIZES];
