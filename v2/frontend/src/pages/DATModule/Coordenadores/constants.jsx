/**
 * Constants for CoordenadoresPage
 * Issue #303: Split large DATModule pages
 */

// Default areas
export const AREAS_DEFAULT = [
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
export const AREA_COLORS = {
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
export const DEFAULT_FILTERS = {
  search: '',
  area: undefined,
  ativo: undefined,
};

// View modes
export const VIEW_MODES = {
  CARDS: 'cards',
  TABLE: 'table',
  AREA: 'area',
};
