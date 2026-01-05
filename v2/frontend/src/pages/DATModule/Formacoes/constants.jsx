/**
 * Constants for FormacoesPage
 * Issue #303: Split large DATModule pages
 */

import {
  EnvironmentOutlined,
  VideoCameraOutlined,
  GlobalOutlined,
} from '@ant-design/icons';

// Status options with colors
export const STATUS_OPTIONS = [
  { label: 'Agendada', value: 'agendada', color: 'blue' },
  { label: 'Confirmada', value: 'confirmada', color: 'cyan' },
  { label: 'Em Andamento', value: 'em_andamento', color: 'orange' },
  { label: 'Realizada', value: 'realizada', color: 'green' },
  { label: 'Cancelada', value: 'cancelada', color: 'red' },
  { label: 'Reagendada', value: 'reagendada', color: 'purple' },
  { label: 'Pend. Docs', value: 'pendente_docs', color: 'gold' },
];

// Modalidade options with icons
export const MODALIDADE_OPTIONS = [
  { label: 'Presencial', value: 'presencial', icon: <EnvironmentOutlined /> },
  { label: 'Online', value: 'online', icon: <VideoCameraOutlined /> },
  { label: 'Híbrida', value: 'hibrida', icon: <GlobalOutlined /> },
];

// Brazilian states
export const UF_OPTIONS = [
  'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
  'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN',
  'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO',
].map((uf) => ({ label: uf, value: uf }));

// Default filter state
export const DEFAULT_FILTERS = {
  search: '',
  uf: undefined,
  municipio: undefined,
  projeto: undefined,
  coordenador: undefined,
  status: undefined,
  modalidade: undefined,
  data_inicio: undefined,
  data_fim: undefined,
};

// View modes
export const VIEW_MODES = {
  TABLE: 'table',
  CALENDAR: 'calendar',
};
