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

// Opções de status. Espelham os choices do backend (M16-08):
// DATRegistro.TURMA_STATUS_CHOICES e DATRegistro.STATUS_CHOICES. Divergir daqui faz
// o Select oferecer valores que o serializer rejeita com 400 (perdendo o formulário
// inteiro) ou esconder valores válidos. O contrato é travado por
// __tests__/statusOptionsContract.test.ts.

// turma_formar_status -> DATRegistro.TURMA_STATUS_CHOICES
export const TURMA_STATUS_OPTIONS: StatusOption[] = [
  { label: 'Criada', value: 'criada' },
  { label: 'Pendente', value: 'pendente' },
  { label: 'Erro', value: 'erro' },
];

// etapas FORMAR/AVALIAR (*_status) -> DATRegistro.STATUS_CHOICES
export const ETAPA_STATUS_OPTIONS: StatusOption[] = [
  { label: 'Concluído', value: 'concluido' },
  { label: 'Pendente', value: 'pendente' },
  { label: 'Em Andamento', value: 'em_andamento' },
  { label: 'Não Aplicável', value: 'nao_aplicavel' },
  { label: 'Erro', value: 'erro' },
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
