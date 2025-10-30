/**
 * Admin DAT - Usuários
 *
 * Gestão de usuários: listagem, busca, criação/edição e atribuição de CPF.
 * Substitui uso cotidiano do Django Admin para usuários.
 *
 * Fase 1 Iteração 2 - Plano DAT/GCal 2025-10-29
 * GAP-001 (resolvido): Endpoint /api/usuarios-admin/ reativado
 */

import { useState, useEffect } from 'react';
import { Table, Button, Input, Space, Tag, Typography, Card, message } from 'antd';
import { UserAddOutlined, ReloadOutlined, EditOutlined } from '@ant-design/icons';
import { Link } from 'react-router-dom';
import { listUsers } from '../../api/adminDAT';

const { Title } = Typography;
const { Search } = Input;

export default function UsuariosPage() {
  const [usuarios, setUsuarios] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
    total: 0,
  });

  /**
   * Fetch users from API
   */
  const fetchUsuarios = async (params = {}) => {
    setLoading(true);
    try {
      const data = await listUsers({
        search: searchText,
        page: params.current || pagination.current,
        page_size: params.pageSize || pagination.pageSize,
        ordering: params.ordering || 'username',
      });

      // DRF pagination response structure
      setUsuarios(data.results || data);
      setPagination({
        ...pagination,
        current: params.current || pagination.current,
        total: data.count || (data.results || data).length,
      });
    } catch (error) {
      message.error(`Erro ao carregar usuários: ${error.message}`);
      console.error('Erro ao carregar usuários:', error);
    } finally {
      setLoading(false);
    }
  };

  // Load users on mount and search change
  useEffect(() => {
    fetchUsuarios();
  }, [searchText]);

  const handleTableChange = (newPagination, filters, sorter) => {
    fetchUsuarios({
      current: newPagination.current,
      pageSize: newPagination.pageSize,
      ordering: sorter.field ? `${sorter.order === 'descend' ? '-' : ''}${sorter.field}` : undefined,
    });
  };

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 60,
      sorter: true,
    },
    {
      title: 'Username',
      dataIndex: 'username',
      key: 'username',
      width: 150,
      sorter: true,
    },
    {
      title: 'Nome',
      key: 'nome',
      render: (_, record) => `${record.first_name || ''} ${record.last_name || ''}`.trim() || '-',
      width: 200,
    },
    {
      title: 'Email',
      dataIndex: 'email',
      key: 'email',
      width: 250,
      sorter: true,
    },
    {
      title: 'CPF',
      dataIndex: 'cpf',
      key: 'cpf',
      width: 150,
      render: (cpf) => cpf || <Tag color="orange">Sem CPF</Tag>,
    },
    {
      title: 'Grupos',
      dataIndex: 'groups',
      key: 'groups',
      render: (groups) =>
        (groups || []).map((g) => (
          <Tag key={g} color="blue">
            {g}
          </Tag>
        )),
      width: 250,
    },
    {
      title: 'Status',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 100,
      render: (is_active) => (
        <Tag color={is_active ? 'green' : 'red'}>{is_active ? 'Ativo' : 'Inativo'}</Tag>
      ),
    },
    {
      title: 'Ações',
      key: 'acoes',
      width: 150,
      render: (_, record) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            disabled
            title="Em desenvolvimento"
          >
            Editar
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px', background: '#f0f2f5', minHeight: 'calc(100vh - 64px)' }}>
      {/* Header */}
      <div style={{ marginBottom: '16px' }}>
        <Link to="/admin-dat">← Voltar para Admin DAT</Link>
      </div>

      <Card>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <Title level={3} style={{ margin: 0 }}>
            Usuários ({pagination.total})
          </Title>
          <Space>
            <Search
              placeholder="Buscar por username, email, nome, CPF"
              allowClear
              style={{ width: 300 }}
              onSearch={(value) => setSearchText(value)}
              onChange={(e) => {
                if (!e.target.value) setSearchText('');
              }}
            />
            <Button icon={<ReloadOutlined />} onClick={() => fetchUsuarios()} loading={loading}>
              Atualizar
            </Button>
            <Button type="primary" icon={<UserAddOutlined />} disabled title="Em desenvolvimento">
              Novo Usuário
            </Button>
          </Space>
        </div>

        {/* Tabela */}
        <Table
          columns={columns}
          dataSource={usuarios}
          rowKey="id"
          loading={loading}
          pagination={{
            ...pagination,
            showSizeChanger: true,
            showTotal: (total) => `Total: ${total} usuários`,
          }}
          onChange={handleTableChange}
          scroll={{ x: 1200 }}
        />
      </Card>
    </div>
  );
}
