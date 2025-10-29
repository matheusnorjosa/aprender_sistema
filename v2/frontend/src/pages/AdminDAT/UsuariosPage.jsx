/**
 * Admin DAT - Usuários
 *
 * Gestão de usuários: listagem, busca, criação/edição e atribuição de CPF.
 * Substitui uso cotidiano do Django Admin para usuários.
 *
 * Fase 1 - Plano DAT/GCal 2025-10-29
 * GAP-001: Endpoint /api/usuarios-admin/ precisa ser reativado
 */

import { useState, useEffect } from 'react';
import { Table, Button, Input, Space, Tag, Typography, Alert, Card } from 'antd';
import { UserAddOutlined, SearchOutlined, ReloadOutlined } from '@ant-design/icons';
import { Link } from 'react-router-dom';

const { Title } = Typography;
const { Search } = Input;

export default function UsuariosPage() {
  const [usuarios, setUsuarios] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');

  // Placeholder: dados mock para desenvolvimento
  const mockData = [
    {
      id: 1,
      username: 'admin',
      email: 'admin@example.com',
      first_name: 'Admin',
      last_name: 'Sistema',
      cpf: '123.456.789-00',
      is_active: true,
      groups: ['Superintendência', 'DAT'],
    },
    {
      id: 2,
      username: 'coordenador1',
      email: 'coord@example.com',
      first_name: 'Coordenador',
      last_name: 'Teste',
      cpf: '987.654.321-00',
      is_active: true,
      groups: ['Coordenador'],
    },
  ];

  useEffect(() => {
    // TODO: Implementar fetch de /api/usuarios-admin/ quando reativado
    setUsuarios(mockData);
  }, []);

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 60,
    },
    {
      title: 'Username',
      dataIndex: 'username',
      key: 'username',
      width: 150,
    },
    {
      title: 'Nome',
      key: 'nome',
      render: (_, record) => `${record.first_name} ${record.last_name}`,
      width: 200,
    },
    {
      title: 'Email',
      dataIndex: 'email',
      key: 'email',
      width: 250,
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
        groups.map((g) => (
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
          <Button type="link" size="small" disabled>
            Editar
          </Button>
          <Button type="link" size="small" danger disabled>
            Desativar
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
            Usuários
          </Title>
          <Space>
            <Search
              placeholder="Buscar por username, email, nome, CPF"
              allowClear
              style={{ width: 300 }}
              onChange={(e) => setSearchText(e.target.value)}
            />
            <Button icon={<ReloadOutlined />} onClick={() => setUsuarios(mockData)}>
              Atualizar
            </Button>
            <Button type="primary" icon={<UserAddOutlined />} disabled>
              Novo Usuário
            </Button>
          </Space>
        </div>

        {/* Alert de desenvolvimento */}
        <Alert
          message="Módulo em desenvolvimento"
          description="GAP-001: Endpoint /api/usuarios-admin/ precisa ser reativado. Dados mock sendo exibidos."
          type="warning"
          showIcon
          closable
          style={{ marginBottom: '16px' }}
        />

        {/* Tabela */}
        <Table
          columns={columns}
          dataSource={usuarios.filter(
            (u) =>
              u.username.toLowerCase().includes(searchText.toLowerCase()) ||
              u.email.toLowerCase().includes(searchText.toLowerCase()) ||
              u.first_name.toLowerCase().includes(searchText.toLowerCase()) ||
              u.last_name.toLowerCase().includes(searchText.toLowerCase()) ||
              (u.cpf && u.cpf.includes(searchText))
          )}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10, showSizeChanger: true, showTotal: (total) => `Total: ${total} usuários` }}
          scroll={{ x: 1200 }}
        />
      </Card>
    </div>
  );
}
