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
import { Table, Button, Input, Space, Tag, Typography, Card, message, Modal, Form, Select } from 'antd';
import { UserAddOutlined, ReloadOutlined, EditOutlined, PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import { Link } from 'react-router-dom';
import { listUsers, createUser, updateUser, deleteUser, listGroups } from '../../api/adminDAT';

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
  const [modalVisible, setModalVisible] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [grupos, setGrupos] = useState([]);

  const [form] = Form.useForm();

  /**
   * Fetch users from API
   */
  const fetchUsuarios = async (params = {}) => {
    setLoading(true);
    try {
      const apiParams = {};

      // Only add non-empty search
      if (searchText) {
        apiParams.search = searchText;
      }

      // Add pagination params
      apiParams.page = params.current || pagination.current;
      apiParams.page_size = params.pageSize || pagination.pageSize;

      // Add ordering if provided
      if (params.ordering) {
        apiParams.ordering = params.ordering;
      } else {
        apiParams.ordering = 'username';
      }

      console.log('fetchUsuarios - API params:', apiParams);
      const data = await listUsers(apiParams);

      // DRF pagination response structure
      setUsuarios(data.results || data);
      setPagination({
        current: params.current || pagination.current,
        pageSize: params.pageSize || pagination.pageSize,
        total: data.count || (data.results || data).length,
      });
    } catch (error) {
      message.error(`Erro ao carregar usuários: ${error.message}`);
      console.error('Erro ao carregar usuários:', error);
    } finally {
      setLoading(false);
    }
  };

  // Fetch groups on mount
  const fetchGrupos = async () => {
    try {
      const data = await listGroups();
      setGrupos(data.results || data);
    } catch (error) {
      console.error('Erro ao carregar grupos:', error);
    }
  };

  // Load groups only on mount
  useEffect(() => {
    fetchGrupos();
  }, []);

  // Load users on mount and search change (reset to page 1)
  useEffect(() => {
    fetchUsuarios({ current: 1 });
  }, [searchText]);

  const handleTableChange = (newPagination, filters, sorter) => {
    console.log('handleTableChange called:', { newPagination, filters, sorter });

    const params = {
      current: newPagination.current,
      pageSize: newPagination.pageSize,
    };

    // Only add ordering if it exists
    if (sorter && sorter.field) {
      params.ordering = `${sorter.order === 'descend' ? '-' : ''}${sorter.field}`;
    }

    console.log('Calling fetchUsuarios with:', params);
    fetchUsuarios(params);
  };

  const handleCreate = () => {
    setEditingUser(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (user) => {
    setEditingUser(user);
    form.setFieldsValue({
      username: user.username,
      email: user.email,
      first_name: user.first_name,
      last_name: user.last_name,
      cpf: user.cpf,
      group_ids: user.group_ids_display || [],
    });
    setModalVisible(true);
  };

  const handleDelete = (user) => {
    Modal.confirm({
      title: 'Confirmar exclusão',
      content: `Tem certeza que deseja excluir o usuário "${user.username}"? Esta ação não pode ser desfeita.`,
      okText: 'Excluir',
      okType: 'danger',
      cancelText: 'Cancelar',
      onOk: async () => {
        try {
          await deleteUser(user.id);
          message.success('Usuário excluído com sucesso');
          fetchUsuarios();
        } catch (error) {
          message.error(`Erro ao excluir: ${error.message}`);
        }
      },
    });
  };

  const handleSave = async (values) => {
    try {
      if (editingUser) {
        await updateUser(editingUser.id, values);
        message.success('Usuário atualizado com sucesso');
      } else {
        await createUser(values);
        message.success('Usuário criado com sucesso');
      }
      setModalVisible(false);
      form.resetFields();
      fetchUsuarios();
    } catch (error) {
      message.error(`Erro: ${error.message}`);
    }
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
      width: 200,
      render: (_, record) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            Editar
          </Button>
          <Button
            type="link"
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record)}
          >
            Excluir
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
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
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

      {/* Modal Criar/Editar Usuário */}
      <Modal
        title={editingUser ? 'Editar Usuário' : 'Novo Usuário'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={() => form.submit()}
        okText="Salvar"
        cancelText="Cancelar"
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSave}
        >
          <Form.Item
            name="username"
            label="Username"
            rules={[{ required: true, message: 'Username é obrigatório' }]}
          >
            <Input placeholder="Ex: joao.silva" disabled={!!editingUser} />
          </Form.Item>

          <Form.Item
            name="email"
            label="Email"
            rules={[
              { required: true, message: 'Email é obrigatório' },
              { type: 'email', message: 'Email inválido' },
            ]}
          >
            <Input placeholder="usuario@example.com" />
          </Form.Item>

          <Form.Item name="first_name" label="Nome">
            <Input placeholder="João" />
          </Form.Item>

          <Form.Item name="last_name" label="Sobrenome">
            <Input placeholder="Silva" />
          </Form.Item>

          <Form.Item
            name="cpf"
            label="CPF"
            rules={[
              {
                pattern: /^[0-9]{11}$/,
                message: 'CPF deve conter exatamente 11 dígitos numéricos',
              },
            ]}
          >
            <Input placeholder="12345678901 (apenas números)" maxLength={11} />
          </Form.Item>

          <Form.Item
            name="group_ids"
            label="Grupos"
            rules={[{ required: true, message: 'Selecione pelo menos um grupo' }]}
          >
            <Select
              mode="multiple"
              placeholder="Selecione os grupos"
              options={grupos.map((g) => ({ label: g.name, value: g.id }))}
            />
          </Form.Item>

          {!editingUser && (
            <Form.Item
              name="password"
              label="Senha"
              rules={[{ required: true, message: 'Senha é obrigatória para novo usuário' }]}
            >
              <Input.Password placeholder="Senha inicial" />
            </Form.Item>
          )}
        </Form>
      </Modal>
    </div>
  );
}
