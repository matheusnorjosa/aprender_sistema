/**
 * Column definitions for CoordenadoresPage
 * Issue #303: Split large DATModule pages
 *
 * Sem rolagem horizontal (G30, padrão responsivo): colunas do ResponsiveTable. Sempre na linha o
 * nome, o status e as ações (AcoesLinha; no celular, o menu "Mais ações"); a Área sobe a partir de
 * md, foto e contagens de lg, o e-mail de xl e o telefone só de xxl. O que some vai para a linha
 * expandida.
 */

import { Tag, Typography, Tooltip, Avatar, Badge, Switch } from 'antd';
import {
  EditOutlined,
  DeleteOutlined,
  MailOutlined,
  PhoneOutlined,
  EnvironmentOutlined,
  ProjectOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import { getAreaColor, getInitials } from './helpers';
import { VISIVEL_A_PARTIR, type ColunaResponsiva } from '../../../components/ResponsiveTable';
import { AcoesLinha, larguraAcoesLinha, type AcaoDaLinha } from '../../../components/AcoesLinha';
import type { ID } from '../../../types';

const { Text } = Typography;

/**
 * Coordenador record interface
 */
export interface CoordenadorRecord {
  id: ID;
  nome: string;
  cargo?: string | null;
  area?: string | null;
  email?: string | null;
  telefone?: string | null;
  foto_url?: string | null;
  data_admissao?: string | null;
  total_municipios?: number;
  total_projetos?: number;
  ativo?: boolean;
  observacoes?: string | null;
  [key: string]: unknown;
}

/**
 * Column handlers interface
 */
export interface ColumnHandlers {
  onView: (record: CoordenadorRecord) => void;
  onEdit: (record: CoordenadorRecord) => void;
  onDelete: (record: CoordenadorRecord) => void;
  onToggleAtivo: (record: CoordenadorRecord) => void;
  /** `execute_restricted_operations`, que o destroy exige: sem ela, Excluir não aparece. */
  podeExcluir: boolean;
}

/**
 * Creates column definitions for coordenadores table
 * @param handlers - Event handlers object
 * @returns Column definitions
 */
export function getColumns(
  { onView, onEdit, onDelete, onToggleAtivo, podeExcluir }: ColumnHandlers,
  acoesCompactas = false,
): ColunaResponsiva<CoordenadorRecord>[] {
  return [
    {
      title: <span className="sr-only">Foto</span>,
      dataIndex: 'foto_url',
      key: 'foto',
      responsive: VISIVEL_A_PARTIR.lg,
      width: 64,
      render: (foto: string | undefined, record) => (
        <Avatar
          src={foto}
          size={40}
          style={{ backgroundColor: getAreaColor(record.area) }}
        >
          {getInitials(record.nome)}
        </Avatar>
      ),
    },
    {
      title: 'Nome',
      dataIndex: 'nome',
      key: 'nome',
      sorter: true,
      render: (nome: string, record) => (
        <div>
          <Text strong>{nome}</Text>
          {record.cargo && (
            <div>
              <Text type="secondary" className="text-[11px]">
                {record.cargo}
              </Text>
            </div>
          )}
        </div>
      ),
    },
    {
      title: 'Área',
      dataIndex: 'area',
      key: 'area',
      responsive: VISIVEL_A_PARTIR.md,
      sorter: true,
      // A área pode ser longa: a tag quebra linha em vez de passar da célula.
      render: (area: string | undefined) => (
        <Tag color={getAreaColor(area)} style={{ whiteSpace: 'normal', overflowWrap: 'anywhere' }}>
          {area || '-'}
        </Tag>
      ),
    },
    {
      title: 'Email',
      dataIndex: 'email',
      key: 'email',
      responsive: VISIVEL_A_PARTIR.xl,
      ellipsis: true,
      render: (email: string | undefined) =>
        email ? (
          <a href={`mailto:${email}`}>
            <MailOutlined className="mr-1" />
            {email}
          </a>
        ) : (
          <Text type="secondary">-</Text>
        ),
    },
    {
      title: 'Telefone',
      dataIndex: 'telefone',
      key: 'telefone',
      responsive: VISIVEL_A_PARTIR.xxl,
      width: 140,
      render: (telefone: string | undefined) =>
        telefone ? (
          <span>
            <PhoneOutlined className="mr-1" />
            {telefone}
          </span>
        ) : (
          <Text type="secondary">-</Text>
        ),
    },
    {
      title: 'Municípios',
      dataIndex: 'total_municipios',
      key: 'municipios',
      responsive: VISIVEL_A_PARTIR.lg,
      width: 100,
      align: 'center',
      sorter: true,
      render: (total: number | undefined) => (
        <Badge
          count={total || 0}
          showZero
          style={{ backgroundColor: total && total > 0 ? '#1890ff' : '#d9d9d9' }}
        >
          <EnvironmentOutlined className="text-gray-400 text-lg" />
        </Badge>
      ),
    },
    {
      title: 'Projetos',
      dataIndex: 'total_projetos',
      key: 'projetos',
      responsive: VISIVEL_A_PARTIR.lg,
      width: 100,
      align: 'center',
      sorter: true,
      render: (total: number | undefined) => (
        <Badge
          count={total || 0}
          showZero
          style={{ backgroundColor: total && total > 0 ? '#52c41a' : '#d9d9d9' }}
        >
          <ProjectOutlined className="text-gray-400 text-lg" />
        </Badge>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'ativo',
      key: 'ativo',
      width: 72,
      align: 'center',
      render: (ativo: boolean | undefined, record) => (
        <Tooltip title={ativo !== false ? 'Clique para desativar' : 'Clique para ativar'}>
          <Switch
            checked={ativo !== false}
            size="small"
            onChange={() => onToggleAtivo(record)}
            checkedChildren={<CheckCircleOutlined />}
            unCheckedChildren={<CloseCircleOutlined />}
          />
        </Tooltip>
      ),
    },
    {
      title: 'Ações',
      key: 'acoes',
      width: larguraAcoesLinha(podeExcluir ? 3 : 2, acoesCompactas),
      render: (_, record) => {
        const acoes: AcaoDaLinha[] = [
          { chave: 'ver', rotulo: 'Ver detalhes', icone: <EyeOutlined />, onClick: () => onView(record) },
          { chave: 'editar', rotulo: 'Editar', icone: <EditOutlined />, onClick: () => onEdit(record) },
          ...(podeExcluir
            ? [{ chave: 'excluir', rotulo: 'Excluir', icone: <DeleteOutlined />, onClick: () => onDelete(record), perigo: true }]
            : []),
        ];
        return <AcoesLinha compacto={acoesCompactas} alvo={record.nome} acoes={acoes} />;
      },
    },
  ];
}
