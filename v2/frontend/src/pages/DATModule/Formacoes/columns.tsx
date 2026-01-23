/**
 * Column definitions for FormacoesPage
 * Issue #303: Split large DATModule pages
 */

import { Space, Tag, Typography, Tooltip, Button } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  EditOutlined,
  DeleteOutlined,
  FileTextOutlined,
  CameraOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { renderStatusTag, renderModalidadeTag } from './helpers';
import type { ID } from '../../../types';

const { Text } = Typography;

/**
 * Formacao record interface
 */
export interface FormacaoRecord {
  id: ID;
  data_formacao?: string;
  horario_inicio?: string;
  horario_fim?: string;
  projeto_nome?: string;
  municipio_nome?: string;
  uf?: string;
  coordenador_nome?: string;
  formador_nome?: string;
  modalidade?: string;
  quantidade_prevista?: number;
  quantidade_presente?: number;
  status?: string;
  lista_presenca_enviada?: boolean;
  relatorio_enviado?: boolean;
  fotos_enviadas?: boolean;
}

/**
 * Column handlers interface
 */
export interface ColumnHandlers {
  onEdit: (record: FormacaoRecord) => void;
  onDelete: (record: FormacaoRecord) => void;
}

/**
 * Creates column definitions for formacoes table
 * @param handlers - Event handlers object
 * @returns Column definitions
 */
export function getColumns({ onEdit, onDelete }: ColumnHandlers): ColumnsType<FormacaoRecord> {
  return [
    {
      title: 'Data',
      dataIndex: 'data_formacao',
      key: 'data',
      width: 100,
      fixed: 'left',
      sorter: true,
      render: (data: string | undefined) => (
        <div>
          <Text strong>{data ? dayjs(data).format('DD/MM/YYYY') : '-'}</Text>
        </div>
      ),
    },
    {
      title: 'Horário',
      key: 'horario',
      width: 100,
      render: (_, record) => (
        <Text type="secondary">
          {record.horario_inicio || '--:--'} - {record.horario_fim || '--:--'}
        </Text>
      ),
    },
    {
      title: 'Projeto',
      dataIndex: 'projeto_nome',
      key: 'projeto',
      width: 120,
      render: (nome: string | undefined) => <Tag color="blue">{nome}</Tag>,
    },
    {
      title: 'Município - UF',
      key: 'municipio_uf',
      width: 180,
      render: (_, record) => (
        <Text>
          {record.municipio_nome} - {record.uf}
        </Text>
      ),
    },
    {
      title: 'Coordenador',
      dataIndex: 'coordenador_nome',
      key: 'coordenador',
      width: 150,
      ellipsis: true,
    },
    {
      title: 'Formador',
      dataIndex: 'formador_nome',
      key: 'formador',
      width: 150,
      ellipsis: true,
    },
    {
      title: 'Modalidade',
      dataIndex: 'modalidade',
      key: 'modalidade',
      width: 110,
      render: (modalidade: string | undefined) => renderModalidadeTag(modalidade),
    },
    {
      title: 'Participantes',
      key: 'participantes',
      width: 120,
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Text type="secondary" className="text-[11px]">
            Prev: {record.quantidade_prevista || 0}
          </Text>
          <Text className="text-[11px]">
            Pres: <Text strong>{record.quantidade_presente || 0}</Text>
          </Text>
        </Space>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: string | undefined) => renderStatusTag(status),
    },
    {
      title: 'Docs',
      key: 'docs',
      width: 100,
      render: (_, record) => (
        <Space size={4}>
          <Tooltip title={record.lista_presenca_enviada ? 'Lista enviada' : 'Lista pendente'}>
            <FileTextOutlined
              style={{
                color: record.lista_presenca_enviada ? '#52c41a' : '#999',
              }}
            />
          </Tooltip>
          <Tooltip title={record.relatorio_enviado ? 'Relatório enviado' : 'Relatório pendente'}>
            <FileTextOutlined
              style={{
                color: record.relatorio_enviado ? '#52c41a' : '#999',
              }}
            />
          </Tooltip>
          <Tooltip title={record.fotos_enviadas ? 'Fotos enviadas' : 'Fotos pendentes'}>
            <CameraOutlined
              style={{
                color: record.fotos_enviadas ? '#52c41a' : '#999',
              }}
            />
          </Tooltip>
        </Space>
      ),
    },
    {
      title: 'Ações',
      key: 'acoes',
      width: 100,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="Editar">
            <Button
              type="text"
              size="small"
              icon={<EditOutlined />}
              onClick={() => onEdit(record)}
              aria-label="Editar formação"
            />
          </Tooltip>
          <Tooltip title="Excluir">
            <Button
              type="text"
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={() => onDelete(record)}
              aria-label="Excluir formação"
            />
          </Tooltip>
        </Space>
      ),
    },
  ];
}
