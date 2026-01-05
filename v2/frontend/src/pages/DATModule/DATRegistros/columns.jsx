/**
 * Column definitions for DATRegistrosPage
 * Issue #303: Split large DATModule pages
 */

import { Space, Tag, Typography, Tooltip, Button } from 'antd';
import { EditOutlined, DeleteOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { STATUS_OPTIONS } from './constants';
import { renderStatusIcon } from './helpers';

const { Text } = Typography;

/**
 * Creates column definitions for DAT registros table
 * @param {Object} handlers - Event handlers object
 * @param {Function} handlers.onEdit - Handler for edit action
 * @param {Function} handlers.onDelete - Handler for delete action
 * @returns {Array} Column definitions
 */
export function getColumns({ onEdit, onDelete }) {
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
      render: (val) => val?.toLocaleString('pt-BR') || '-',
    },
    {
      title: 'Profs.',
      dataIndex: 'professor_qtde',
      key: 'professor_qtde',
      width: 80,
      align: 'right',
      render: (val) => val?.toLocaleString('pt-BR') || '-',
    },
    // Detalhes FORMAR
    {
      title: 'Reunião DAT',
      dataIndex: 'reuniao_dat',
      key: 'reuniao_dat',
      width: 110,
      render: (val) => (val ? dayjs(val).format('DD/MM/YYYY') : '-'),
    },
    {
      title: 'ID Turma',
      dataIndex: 'turma_formar_id',
      key: 'turma_formar_id',
      width: 100,
      render: (val) =>
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
      render: (val) => (val ? <Tag>{val}</Tag> : '-'),
    },
    {
      title: 'Chaves',
      dataIndex: 'chaves_inscricao_status',
      key: 'chaves',
      width: 100,
      render: (status) => {
        const colors = {
          concluido: 'green',
          em_andamento: 'gold',
          pendente: 'default',
        };
        const labels = {
          concluido: 'Geradas',
          em_andamento: 'Pend.',
          pendente: 'Pend.',
        };
        return <Tag color={colors[status]}>{labels[status] || status}</Tag>;
      },
    },
    {
      title: 'Envio',
      dataIndex: 'envio_codigos_status',
      key: 'envio',
      width: 70,
      align: 'center',
      render: (status) => (
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
      render: (val) => (
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
      render: (val) =>
        val ? <Tag color="green">SIM</Tag> : <Tag color="default">NÃO</Tag>,
    },
    {
      title: 'Recebidos',
      dataIndex: 'alunos_recebidos_status',
      key: 'recebidos',
      width: 90,
      align: 'center',
      render: (status) => renderStatusIcon(status),
    },
    {
      title: 'Validados',
      dataIndex: 'alunos_validados_status',
      key: 'validados',
      width: 90,
      align: 'center',
      render: (status) => renderStatusIcon(status),
    },
    {
      title: 'Importados',
      dataIndex: 'alunos_importados_status',
      key: 'importados',
      width: 90,
      align: 'center',
      render: (status) => renderStatusIcon(status),
    },
    {
      title: 'Obs. AVALIAR',
      dataIndex: 'obs_avaliar',
      key: 'obs_avaliar',
      width: 150,
      ellipsis: { showTitle: false },
      render: (val) => (
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
