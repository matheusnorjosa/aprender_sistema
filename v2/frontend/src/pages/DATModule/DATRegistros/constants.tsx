/**
 * Constants for DATRegistrosPage
 * Issue #303: Split large DATModule pages
 */

/**
 * Status option interface
 */
export interface StatusOption {
  label: string;
  value: string;
}

/**
 * UF option interface
 */
export interface UfOption {
  label: string;
  value: string;
}

/**
 * Region option interface
 */
export interface RegiaoOption {
  label: string;
  value: string;
}

/**
 * Filter state interface
 */
export interface DATRegistrosFilters {
  regiao: string;
  uf: string | undefined;
  municipio: number | undefined;
  projeto_geral: number | undefined;
  usa_avaliar: boolean | undefined;
  status_formar: string | undefined;
}

// Status options for workflow steps
export const STATUS_OPTIONS: StatusOption[] = [
  { label: 'Pendente', value: 'pendente' },
  { label: 'Em Andamento', value: 'em_andamento' },
  { label: 'Concluído', value: 'concluido' },
];

// Brazilian states
export const UF_OPTIONS: UfOption[] = [
  'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
  'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN',
  'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO',
].map((uf) => ({ label: uf, value: uf }));

// Region to UF mapping
export const REGIAO_UFS: Record<string, string[]> = {
  Norte: ['AC', 'AP', 'AM', 'PA', 'RO', 'RR', 'TO'],
  Nordeste: ['AL', 'BA', 'CE', 'MA', 'PB', 'PE', 'PI', 'RN', 'SE'],
  'Centro-Oeste': ['DF', 'GO', 'MT', 'MS'],
  Sudeste: ['ES', 'MG', 'RJ', 'SP'],
  Sul: ['PR', 'RS', 'SC'],
};

// Region options for filter
export const REGIAO_OPTIONS: RegiaoOption[] = [
  { label: 'Todas', value: '' },
  { label: 'Norte', value: 'Norte' },
  { label: 'Nordeste', value: 'Nordeste' },
  { label: 'Centro-Oeste', value: 'Centro-Oeste' },
  { label: 'Sudeste', value: 'Sudeste' },
  { label: 'Sul', value: 'Sul' },
];

// Default filter state
export const DEFAULT_FILTERS: DATRegistrosFilters = {
  regiao: '',
  uf: undefined,
  municipio: undefined,
  projeto_geral: undefined,
  usa_avaliar: undefined,
  status_formar: undefined,
};
