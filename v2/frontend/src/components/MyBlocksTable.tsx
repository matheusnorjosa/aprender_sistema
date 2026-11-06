/**
 * Tabela de Bloqueios do Usuário
 *
 * Exibe lista de bloqueios com:
 * - Colunas: Início, Fim, Tipo, Status, Motivo
 * - Ação de exclusão (apenas para status 'pendente')
 * - Formatação de datas legíveis
 * - Estados de vazio e loading
 *
 * Sem rolagem horizontal (G30, padrão responsivo): ResponsiveTable. Sempre na linha o início, o
 * status e as ações (AcoesLinha; no celular, o menu "Mais ações"). O Fim aparece a partir de sm
 * (abaixo disso, o status vai junto do início) e Tipo e Motivo a partir de md; o que some da
 * linha vai para a linha expandida.
 */

import { Grid, Modal, Tag, Empty } from 'antd';
import { DeleteOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import type { ID } from '../types';
import { formatFortaleza } from '../utils/datetime';
import ResponsiveTable, { VISIVEL_A_PARTIR, type ColunaResponsiva } from './ResponsiveTable';
import { AcoesLinha, larguraAcoesLinha } from './AcoesLinha';

import type { JSX } from "react";

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

/** Quem a linha representa: nomeia o expandir e as ações ("Excluir: bloqueio de 15/09/2026 09:00"). */
function nomeDoBloqueio(bloqueio: BlockRecord): string {
  return `bloqueio de ${formatFortaleza(bloqueio.inicio)}`;
}

function tagDoStatus(status: BlockStatus): JSX.Element {
  return (
    <Tag color={STATUS_COLORS[status] || 'default'}>
      {status?.toUpperCase()}
    </Tag>
  );
}

export default function MyBlocksTable({ blocks, onDelete, loading }: MyBlocksTableProps): JSX.Element {
  const telas = Grid.useBreakpoint();
  const acoesCompactas = !telas.sm;

  // Ação destrutiva: começa no Cancelar e cita o bloqueio (o período).
  const confirmarExclusao = (bloqueio: BlockRecord): void => {
    Modal.confirm({
      title: 'Tem certeza que deseja excluir este bloqueio?',
      content: `Bloqueio de ${formatFortaleza(bloqueio.inicio)} a ${formatFortaleza(bloqueio.fim)}. Esta ação não pode ser desfeita.`,
      okText: 'Sim, excluir',
      okType: 'danger',
      cancelText: 'Cancelar',
      autoFocusButton: 'cancel',
      onOk: () => onDelete(bloqueio.id),
    });
  };

  /**
   * Configuração das colunas.
   */
  const columns: ColunaResponsiva<BlockRecord>[] = [
    {
      title: 'Início',
      dataIndex: 'inicio',
      key: 'inicio',
      // Abaixo de sm a coluna Status some: o status vai junto do início (estado fica na linha).
      render: (_, record) =>
        telas.sm ? (
          formatFortaleza(record.inicio)
        ) : (
          <>
            <div>{formatFortaleza(record.inicio)}</div>
            {tagDoStatus(record.status)}
          </>
        ),
      sorter: (a, b) => dayjs(a.inicio).unix() - dayjs(b.inicio).unix(),
    },
    {
      title: 'Fim',
      dataIndex: 'fim',
      key: 'fim',
      responsive: VISIVEL_A_PARTIR.sm,
      render: (_, record) => formatFortaleza(record.fim),
    },
    {
      title: 'Tipo',
      dataIndex: 'tipo',
      key: 'tipo',
      responsive: VISIVEL_A_PARTIR.md,
      width: 96,
      render: (_, record) => (
        <Tag color={record.tipo === 'T' ? 'volcano' : 'geekblue'}>
          {TIPO_LABELS[record.tipo] || record.tipo}
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
      responsive: VISIVEL_A_PARTIR.sm,
      width: 124,
      render: (_, record) => tagDoStatus(record.status),
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
      responsive: VISIVEL_A_PARTIR.md,
      ellipsis: true,
      render: (_, record) => record.motivo || '-',
    },
    {
      title: 'Ações',
      key: 'actions',
      width: larguraAcoesLinha(1, acoesCompactas),
      // Bloqueios são auto-aprovados; usuário pode excluir os próprios bloqueios
      render: (_, record) => (
        <AcoesLinha
          compacto={acoesCompactas}
          alvo={nomeDoBloqueio(record)}
          acoes={[
            {
              chave: 'excluir',
              rotulo: 'Excluir',
              icone: <DeleteOutlined />,
              onClick: () => confirmarExclusao(record),
              perigo: true,
            },
          ]}
        />
      ),
    },
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
    <ResponsiveTable<BlockRecord>
      columns={columns}
      dataSource={blocks}
      rowKey="id"
      loading={loading}
      nomeDaLinha={nomeDoBloqueio}
      pagination={{
        pageSize: 5,
        size: 'small',
        showSizeChanger: false,
      }}
      size="small"
    />
  );
}
