/**
 * Column definitions for DATRegistrosPage
 * Issue #303: Split large DATModule pages
 */

import { Space, Tag, Typography, Tooltip, Button } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { EditOutlined, DeleteOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { STATUS_OPTIONS } from './constants';
import { renderStatusIcon } from './helpers';
import type { ID } from '../../../types';

const { Text } = Typography;

/**
 * DAT registro record interface
 */
export interface DATRegistroRecord {
  id: ID;
  municipio_nome: string;
  municipio_uf: string;
  projeto_geral_nome?: string;
  projeto_nome?: string;
  aluno_qtde?: number;
  professor_qtde?: number;
  reuniao_dat?: string;
  turma_formar_id?: string;
  nr_codigos?: number;
  chaves_inscricao_status?: string;
  envio_codigos_status?: string;
  obs_formar?: string;
  usa_avaliar?: boolean;
  alunos_recebidos_status?: string;
  alunos_validados_status?: string;
  alunos_importados_status?: string;
  obs_avaliar?: string;
}

/**
 * Column handlers interface
 */
export interface ColumnHandlers {
  onEdit: (record: DATRegistroRecord) => void;
  onDelete: (record: DATRegistroRecord) => void;
}

/**
 * Creates column definitions for DAT registros table
 * @param handlers - Event handlers object
 * @returns Column definitions
 */
export function getColumns({ onEdit, onDelete }: ColumnHandlers): ColumnsType<DATRegistroRecord> {
  return [
    // Dados Básicos
    {
      title: 'Município - UF',
      key: 'municipio_uf',
      width: 180,
      fixed: 'left',
      render: (_, record) => (
        <Text strong>
          {record.municipio_nome} - {record.municipio_uf}
        </Text>
      ),
    },
    {
      title: 'Projeto Geral',
      dataIndex: 'projeto_geral_nome',
      key: 'projeto_geral',
      width: 150,
    },
    {
      title: 'Projeto',
      dataIndex: 'projeto_nome',
      key: 'projeto',
      width: 150,
    },
    {
      title: 'Alunos',
      dataIndex: 'aluno_qtde',
      key: 'aluno_qtde',
      width: 80,
      align: 'right',
      render: (val: number | undefined) => val?.toLocaleString('pt-BR') || '-',
    },
    {
      title: 'Profs.',
      dataIndex: 'professor_qtde',
      key: 'professor_qtde',
      width: 80,
      align: 'right',
      render: (val: number | undefined) => val?.toLocaleString('pt-BR') || '-',
    },
    // Detalhes FORMAR
    {
      title: 'Reunião DAT',
      dataIndex: 'reuniao_dat',
      key: 'reuniao_dat',
      width: 110,
      render: (val: string | undefined) => (val ? dayjs(val).format('DD/MM/YYYY') : '-'),
    },
    {
      title: 'ID Turma',
      dataIndex: 'turma_formar_id',
      key: 'turma_formar_id',
      width: 100,
      render: (val: string | undefined) =>
        val ? (
          <Text code className="text-blue-500">
            {val}
          </Text>
        ) : (
          '-'
        ),
    },
    {
      title: 'Códs',
      dataIndex: 'nr_codigos',
      key: 'nr_codigos',
      width: 70,
      align: 'center',
      render: (val: number | undefined) => (val ? <Tag>{val}</Tag> : '-'),
    },
    {
      title: 'Chaves',
      dataIndex: 'chaves_inscricao_status',
      key: 'chaves',
      width: 100,
      render: (status: string | undefined) => {
        const colors: Record<string, string> = {
          concluido: 'green',
          em_andamento: 'gold',
          pendente: 'default',
        };
        const labels: Record<string, string> = {
          concluido: 'Geradas',
          em_andamento: 'Pend.',
          pendente: 'Pend.',
        };
        return <Tag color={status ? colors[status] : 'default'}>{status ? labels[status] : status}</Tag>;
      },
    },
    {
      title: 'Envio',
      dataIndex: 'envio_codigos_status',
      key: 'envio',
      width: 70,
      align: 'center',
      render: (status: string | undefined) => (
        <Tooltip title={STATUS_OPTIONS.find((s) => s.value === status)?.label || status}>
          {renderStatusIcon(status)}
        </Tooltip>
      ),
    },
    {
      title: 'Obs. FORMAR',
      dataIndex: 'obs_formar',
      key: 'obs_formar',
      width: 150,
      ellipsis: { showTitle: false },
      render: (val: string | undefined) => (
        <Tooltip title={val}>
          <Text type="secondary">{val || '-'}</Text>
        </Tooltip>
      ),
    },
    // Detalhes AVALIAR
    {
      title: 'Usa AVALIAR',
      dataIndex: 'usa_avaliar',
      key: 'usa_avaliar',
      width: 100,
      align: 'center',
      render: (val: boolean | undefined) =>
        val ? <Tag color="green">SIM</Tag> : <Tag color="default">NÃO</Tag>,
    },
    {
      title: 'Recebidos',
      dataIndex: 'alunos_recebidos_status',
      key: 'recebidos',
      width: 90,
      align: 'center',
      render: (status: string | undefined) => renderStatusIcon(status),
    },
    {
      title: 'Validados',
      dataIndex: 'alunos_validados_status',
      key: 'validados',
      width: 90,
      align: 'center',
      render: (status: string | undefined) => renderStatusIcon(status),
    },
    {
      title: 'Importados',
      dataIndex: 'alunos_importados_status',
      key: 'importados',
      width: 90,
      align: 'center',
      render: (status: string | undefined) => renderStatusIcon(status),
    },
    {
      title: 'Obs. AVALIAR',
      dataIndex: 'obs_avaliar',
      key: 'obs_avaliar',
      width: 150,
      ellipsis: { showTitle: false },
      render: (val: string | undefined) => (
        <Tooltip title={val}>
          <Text type="secondary">{val || '-'}</Text>
        </Tooltip>
      ),
    },
    // Ações
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
              aria-label="Editar registro"
            />
          </Tooltip>
          <Tooltip title="Excluir">
            <Button
              type="text"
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={() => onDelete(record)}
              aria-label="Excluir registro"
            />
          </Tooltip>
        </Space>
      ),
    },
  ];
}
