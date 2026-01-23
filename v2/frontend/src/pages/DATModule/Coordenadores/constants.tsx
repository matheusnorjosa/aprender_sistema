/**
 * Constants for CoordenadoresPage
 * Issue #303: Split large DATModule pages
 */

/**
 * Filter state interface
 */
export interface CoordenadoresFilters {
  search: string;
  area: string | undefined;
  ativo: boolean | undefined;
}

/**
 * View mode type
 */
export type ViewMode = 'cards' | 'table' | 'area';

// Default areas
export const AREAS_DEFAULT: string[] = [
  'DAT',
  'Tecnologia',
  'Pedagógico',
  'Administrativo',
  'Comercial',
  'Financeiro',
  'RH',
  'Marketing',
  'Logística',
  'Suporte',
];

// Area color mapping (Ant Design colors)
export const AREA_COLORS: Record<string, string> = {
  DAT: 'red',
  Tecnologia: 'blue',
  Pedagógico: 'green',
  Administrativo: 'orange',
  Comercial: 'purple',
  Financeiro: 'gold',
  RH: 'cyan',
  Marketing: 'magenta',
  Logística: 'volcano',
  Suporte: 'geekblue',
};

// Default filter state
export const DEFAULT_FILTERS: CoordenadoresFilters = {
  search: '',
  area: undefined,
  ativo: undefined,
};

// View modes
export const VIEW_MODES = {
  CARDS: 'cards' as const,
  TABLE: 'table' as const,
  AREA: 'area' as const,
};
