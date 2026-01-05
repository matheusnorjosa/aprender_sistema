/**
 * Column definitions for CoordenadoresPage
 * Issue #303: Split large DATModule pages
 */

import { Space, Tag, Typography, Tooltip, Button, Avatar, Badge, Switch } from 'antd';
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

const { Text } = Typography;

/**
 * Creates column definitions for coordenadores table
 * @param {Object} handlers - Event handlers object
 * @param {Function} handlers.onView - Handler for view action
 * @param {Function} handlers.onEdit - Handler for edit action
 * @param {Function} handlers.onDelete - Handler for delete action
 * @param {Function} handlers.onToggleAtivo - Handler for toggle active status
 * @returns {Array} Column definitions
 */
export function getColumns({ onView, onEdit, onDelete, onToggleAtivo }) {
  return [
    {
      title: '',
      dataIndex: 'foto_url',
      key: 'foto',
      width: 60,
      fixed: 'left',
      render: (foto, record) => (
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
      width: 180,
      fixed: 'left',
      sorter: true,
      render: (nome, record) => (
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
      width: 120,
      sorter: true,
      render: (area) => <Tag color={getAreaColor(area)}>{area || '-'}</Tag>,
    },
    {
      title: 'Email',
      dataIndex: 'email',
      key: 'email',
      width: 200,
      ellipsis: true,
      render: (email) =>
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
      width: 140,
      render: (telefone) =>
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
      width: 100,
      align: 'center',
      sorter: true,
      render: (total) => (
        <Badge
          count={total || 0}
          showZero
          style={{ backgroundColor: total > 0 ? '#1890ff' : '#d9d9d9' }}
        >
          <EnvironmentOutlined className="text-gray-400 text-lg" />
        </Badge>
      ),
    },
    {
      title: 'Projetos',
      dataIndex: 'total_projetos',
      key: 'projetos',
      width: 100,
      align: 'center',
      sorter: true,
      render: (total) => (
        <Badge
          count={total || 0}
          showZero
          style={{ backgroundColor: total > 0 ? '#52c41a' : '#d9d9d9' }}
        >
          <ProjectOutlined className="text-gray-400 text-lg" />
        </Badge>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'ativo',
      key: 'ativo',
      width: 90,
      align: 'center',
      render: (ativo, record) => (
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
      width: 120,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="Ver detalhes">
            <Button
              type="text"
              size="small"
              icon={<EyeOutlined />}
              onClick={() => onView(record)}
              aria-label="Ver detalhes do coordenador"
            />
          </Tooltip>
          <Tooltip title="Editar">
            <Button
              type="text"
              size="small"
              icon={<EditOutlined />}
              onClick={() => onEdit(record)}
              aria-label="Editar coordenador"
            />
          </Tooltip>
          <Tooltip title="Excluir">
            <Button
              type="text"
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={() => onDelete(record)}
              aria-label="Excluir coordenador"
            />
          </Tooltip>
        </Space>
      ),
    },
  ];
}
