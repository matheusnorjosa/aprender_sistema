/**
 * Column definitions for FormacoesPage
 * Issue #303: Split large DATModule pages
 */

import { Space, Tag, Typography, Tooltip, Button } from 'antd';
import {
  EditOutlined,
  DeleteOutlined,
  FileTextOutlined,
  CameraOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { renderStatusTag, renderModalidadeTag } from './helpers';

const { Text } = Typography;

/**
 * Creates column definitions for formacoes table
 * @param {Object} handlers - Event handlers object
 * @param {Function} handlers.onEdit - Handler for edit action
 * @param {Function} handlers.onDelete - Handler for delete action
 * @returns {Array} Column definitions
 */
export function getColumns({ onEdit, onDelete }) {
  return [
    {
      title: 'Data',
      dataIndex: 'data_formacao',
      key: 'data',
      width: 100,
      fixed: 'left',
      sorter: true,
      render: (data) => (
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
      render: (nome) => <Tag color="blue">{nome}</Tag>,
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
      render: (modalidade) => renderModalidadeTag(modalidade),
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
      render: (status) => renderStatusTag(status),
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
