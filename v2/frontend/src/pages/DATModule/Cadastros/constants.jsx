/**
 * Constants for CadastrosPage
 * Issue #303: Split large DATModule pages
 */

import { BookOutlined, BarChartOutlined } from '@ant-design/icons';

// Status options for workflow steps
export const STATUS_OPTIONS = [
  { label: 'Pendente', value: 'pendente' },
  { label: 'Em Andamento', value: 'em_andamento' },
  { label: 'Concluído', value: 'concluido' },
  { label: 'N/A', value: 'na' },
];

// Platform configurations with their workflow steps
export const PLATAFORMAS = {
  FORMAR: {
    key: 'FORMAR',
    label: 'FORMAR',
    color: '#1890ff',
    icon: <BookOutlined />,
    url: 'https://www.aprenderformar.com.br/plataforma/',
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
    url: 'https://avaliar.aprenderformar.com.br/',
    etapas: [
      { key: 'recebidos', label: 'Recebidos' },
      { key: 'validados', label: 'Validados' },
      { key: 'importados', label: 'Importados' },
    ],
  },
};

// Projects that use AVALIAR platform
export const PROJETOS_AVALIAR = [
  'ACERTA',
  'NOVO LENDO',
  'TEMA',
  'VIDA E...',
  'PROJETO AMMA',
  'SUPERATIVAR',
  'GESTÃO ESCOLAR',
];

// Brazilian states
export const UF_OPTIONS = [
  'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
  'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN',
  'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO',
].map((uf) => ({ label: uf, value: uf }));

// Status icon mapping
export const STATUS_ICONS = {
  pendente: { icon: 'ClockCircleFilled', color: '#faad14' },
  em_andamento: { icon: 'ExclamationCircleFilled', color: '#1890ff' },
  concluido: { icon: 'CheckCircleFilled', color: '#52c41a' },
  na: { icon: 'MinusCircleFilled', color: '#d9d9d9' },
};

// Default filter state
export const DEFAULT_FILTERS = {
  search: '',
  uf: undefined,
  municipio: undefined,
  projeto_geral: undefined,
  status_etapa: undefined,
};
