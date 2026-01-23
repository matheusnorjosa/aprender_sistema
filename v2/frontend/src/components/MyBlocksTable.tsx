/**
 * Tabela de Bloqueios do Usuário
 *
 * Exibe lista de bloqueios com:
 * - Colunas: Início, Fim, Tipo, Status, Motivo
 * - Ação de exclusão (apenas para status 'pendente')
 * - Formatação de datas legíveis
 * - Estados de vazio e loading
 */

import { Table, Button, Popconfirm, Tag, Empty } from 'antd';
import { DeleteOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import type { ColumnsType, ColumnType } from 'antd/es/table';
import type { ID } from '../types';

/**
 * Block type
 */
type BlockType = 'T' | 'P';

/**
 * Block status
 */
type BlockStatus = 'pendente' | 'aprovado' | 'reprovado';

/**
 * Block record interface
 */
export interface BlockRecord {
  id: ID;
  inicio: string;
  fim: string;
  tipo: BlockType;
  status: BlockStatus;
  motivo?: string;
}

/**
 * MyBlocksTable props interface
 */
export interface MyBlocksTableProps {
  blocks: BlockRecord[];
  onDelete: (id: ID) => void;
  loading: boolean;
}

/**
 * Mapeia status para cores de Tag.
 */
const STATUS_COLORS: Record<BlockStatus, string> = {
  pendente: 'blue',
  aprovado: 'green',
  reprovado: 'red',
};

/**
 * Mapeia tipo de bloqueio para label.
 */
const TIPO_LABELS: Record<BlockType, string> = {
  T: 'Total',
  P: 'Parcial',
};

export default function MyBlocksTable({ blocks, onDelete, loading }: MyBlocksTableProps): JSX.Element {
  /**
   * Configuração das colunas.
   */
  const columns: ColumnsType<BlockRecord> = [
    {
      title: 'Início',
      dataIndex: 'inicio',
      key: 'inicio',
      render: (text: string) => dayjs(text).format('DD/MM/YYYY HH:mm'),
      sorter: (a, b) => dayjs(a.inicio).unix() - dayjs(b.inicio).unix(),
    },
    {
      title: 'Fim',
      dataIndex: 'fim',
      key: 'fim',
      render: (text: string) => dayjs(text).format('DD/MM/YYYY HH:mm'),
    },
    {
      title: 'Tipo',
      dataIndex: 'tipo',
      key: 'tipo',
      render: (tipo: BlockType) => (
        <Tag color={tipo === 'T' ? 'volcano' : 'geekblue'}>
          {TIPO_LABELS[tipo] || tipo}
        </Tag>
      ),
      filters: [
        { text: 'Total', value: 'T' },
        { text: 'Parcial', value: 'P' },
      ],
      onFilter: (value, record) => record.tipo === value,
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: BlockStatus) => (
        <Tag color={STATUS_COLORS[status] || 'default'}>
          {status?.toUpperCase()}
        </Tag>
      ),
      filters: [
        { text: 'Pendente', value: 'pendente' },
        { text: 'Aprovado', value: 'aprovado' },
        { text: 'Reprovado', value: 'reprovado' },
      ],
      onFilter: (value, record) => record.status === value,
    },
    {
      title: 'Motivo',
      dataIndex: 'motivo',
      key: 'motivo',
      ellipsis: true,
      render: (text: string | undefined) => text || '-',
    },
    {
      title: 'Ações',
      key: 'actions',
      fixed: 'right',
      width: 100,
      render: (_, record) => {
        // Apenas bloqueios pendentes podem ser excluídos
        const canDelete = record.status === 'pendente';

        if (!canDelete) {
          return (
            <Button type="text" disabled size="small">
              -
            </Button>
          );
        }

        return (
          <Popconfirm
            title="Tem certeza que deseja excluir este bloqueio?"
            description="Esta ação não pode ser desfeita."
            onConfirm={() => onDelete(record.id)}
            okText="Sim, excluir"
            cancelText="Cancelar"
            okButtonProps={{ danger: true }}
          >
            <Button
              type="text"
              danger
              size="small"
              icon={<DeleteOutlined />}
            >
              Excluir
            </Button>
          </Popconfirm>
        );
      },
    } as ColumnType<BlockRecord>,
  ];

  /**
   * Renderiza estado vazio.
   */
  if (!loading && blocks.length === 0) {
    return (
      <Empty
        description="Nenhum bloqueio cadastrado"
        image={Empty.PRESENTED_IMAGE_SIMPLE}
      />
    );
  }

  return (
    <Table
      columns={columns}
      dataSource={blocks}
      rowKey="id"
      loading={loading}
      pagination={{
        pageSize: 5,
        size: 'small',
        showSizeChanger: false,
      }}
      scroll={{ x: 800 }}
      size="small"
    />
  );
}
