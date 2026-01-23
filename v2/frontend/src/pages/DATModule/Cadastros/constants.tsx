/**
 * Constants for CadastrosPage
 * Issue #303: Split large DATModule pages
 */

import type { ReactNode } from 'react';
import { BookOutlined, BarChartOutlined } from '@ant-design/icons';
import { EXTERNAL_URLS } from '../../../constants';

/**
 * Status option interface
 */
export interface StatusOption {
  label: string;
  value: string;
}

/**
 * Etapa (workflow step) interface
 */
export interface Etapa {
  key: string;
  label: string;
}

/**
 * Platform configuration interface
 */
export interface PlataformaConfig {
  key: string;
  label: string;
  color: string;
  icon: ReactNode;
  url: string;
  etapas: Etapa[];
}

/**
 * Status icon configuration
 */
export interface StatusIconConfig {
  icon: string;
  color: string;
}

/**
 * Filter state interface
 */
export interface CadastrosFilters {
  search: string;
  uf: string | undefined;
  municipio: number | undefined;
  projeto_geral: number | undefined;
  status_etapa: string | undefined;
}

/**
 * UF option interface
 */
export interface UfOption {
  label: string;
  value: string;
}

// Status options for workflow steps
export const STATUS_OPTIONS: StatusOption[] = [
  { label: 'Pendente', value: 'pendente' },
  { label: 'Em Andamento', value: 'em_andamento' },
  { label: 'Concluído', value: 'concluido' },
  { label: 'N/A', value: 'na' },
];

// Platform configurations with their workflow steps
export const PLATAFORMAS: Record<string, PlataformaConfig> = {
  FORMAR: {
    key: 'FORMAR',
    label: 'FORMAR',
    color: '#1890ff',
    icon: <BookOutlined />,
    url: EXTERNAL_URLS.FORMAR_PLATFORM,
    etapas: [
      { key: 'criacao_curso', label: 'Criação Curso' },
      { key: 'chaves', label: 'Chaves' },
      { key: 'instrucoes', label: 'Instruções' },
      { key: 'envio', label: 'Envio' },
    ],
  },
  AVALIAR: {
    key: 'AVALIAR',
    label: 'AVALIAR',
    color: '#52c41a',
    icon: <BarChartOutlined />,
    url: EXTERNAL_URLS.AVALIAR_PLATFORM,
    etapas: [
      { key: 'recebidos', label: 'Recebidos' },
      { key: 'validados', label: 'Validados' },
      { key: 'importados', label: 'Importados' },
    ],
  },
};

// Projects that use AVALIAR platform
export const PROJETOS_AVALIAR: string[] = [
  'ACERTA',
  'NOVO LENDO',
  'TEMA',
  'VIDA E...',
  'PROJETO AMMA',
  'SUPERATIVAR',
  'GESTÃO ESCOLAR',
];

// Brazilian states
export const UF_OPTIONS: UfOption[] = [
  'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
  'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN',
  'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO',
].map((uf) => ({ label: uf, value: uf }));

// Status icon mapping
export const STATUS_ICONS: Record<string, StatusIconConfig> = {
  pendente: { icon: 'ClockCircleFilled', color: '#faad14' },
  em_andamento: { icon: 'ExclamationCircleFilled', color: '#1890ff' },
  concluido: { icon: 'CheckCircleFilled', color: '#52c41a' },
  na: { icon: 'MinusCircleFilled', color: '#d9d9d9' },
};

// Default filter state
export const DEFAULT_FILTERS: CadastrosFilters = {
  search: '',
  uf: undefined,
  municipio: undefined,
  projeto_geral: undefined,
  status_etapa: undefined,
};
