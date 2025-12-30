/**
 * Admin DAT - Grupos
 *
 * CRUD de grupos Django com gestão de membros.
 * Fase 1 Iteração 3 - Plano DAT/GCal 2025-10-29
 */

import { useState, useEffect } from 'react';
import { Table, Button, Input, Space, Tag, Typography, Card, message, Modal, Form, Checkbox } from 'antd';
import { TeamOutlined, ReloadOutlined, EditOutlined, PlusOutlined, UserAddOutlined } from '@ant-design/icons';
import { Link } from 'react-router-dom';
import { listGroups, createGroup, updateGroup, listUsers, assignGroups } from '../../api/adminDAT';

const { Title } = Typography;
const { Search } = Input;

export default function GruposPage() {
  const [grupos, setGrupos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [modalVisible, setModalVisible] = useState(false);
  const [editingGroup, setEditingGroup] = useState(null);
  const [membersModalVisible, setMembersModalVisible] = useState(false);
  const [selectedGroup, setSelectedGroup] = useState(null);
  const [usuarios, setUsuarios] = useState([]);
  const [selectedUsers, setSelectedUsers] = useState([]);
  const [savingMembers, setSavingMembers] = useState(false);

  const [form] = Form.useForm();

  const fetchGrupos = async () => {
    setLoading(true);
    try {
      const data = await listGroups({
        search: searchText,
        ordering: 'name',
      });
      setGrupos(data.results || data);
    } catch (error) {
      message.error(`Erro ao carregar grupos: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const fetchUsuarios = async () => {
    try {
      const data = await listUsers({ ordering: 'username', page_size: 1000 });
      setUsuarios(data.results || data);
    } catch (error) {
      message.error(`Erro ao carregar usuários: ${error.message}`);
    }
  };

  useEffect(() => {
    fetchGrupos();
  }, [searchText]);

  useEffect(() => {
    fetchUsuarios();
  }, []);

  const handleCreate = () => {
    setEditingGroup(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (group) => {
    setEditingGroup(group);
    form.setFieldsValue(group);
    setModalVisible(true);
  };

  const handleSave = async (values) => {
    try {
      if (editingGroup) {
        await updateGroup(editingGroup.id, values);
        message.success('Grupo atualizado com sucesso');
      } else {
        await createGroup(values);
        message.success('Grupo criado com sucesso');
      }
      setModalVisible(false);
      form.resetFields();
      fetchGrupos();
    } catch (error) {
      message.error(`Erro: ${error.message}`);
    }
  };

  const handleManageMembers = async (group) => {
    setSelectedGroup(group);
    setMembersModalVisible(true);

    // Carregar usuários que já estão no grupo
    const usersInGroup = usuarios.filter((u) =>
      u.groups && u.groups.some((g) => g.id === group.id || g === group.id)
    );
    setSelectedUsers(usersInGroup.map((u) => u.id));
  };

  const handleSaveMembers = async () => {
    setSavingMembers(true);
    try {
      // Para cada usuário selecionado, atribuir o grupo
      // Para cada usuário não-selecionado que estava no grupo, remover o grupo

      const promises = usuarios.map(async (usuario) => {
        const isSelected = selectedUsers.includes(usuario.id);
        const currentGroups = usuario.groups ? usuario.groups.map((g) => (typeof g === 'object' ? g.id : g)) : [];
        const hasGroup = currentGroups.includes(selectedGroup.id);

        if (isSelected && !hasGroup) {
          // Adicionar grupo
          const newGroups = [...currentGroups, selectedGroup.id];
          return assignGroups(usuario.id, { group_ids: newGroups });
        } else if (!isSelected && hasGroup) {
          // Remover grupo
          const newGroups = currentGroups.filter((gid) => gid !== selectedGroup.id);
          return assignGroups(usuario.id, { group_ids: newGroups });
        }
        return Promise.resolve();
      });

      await Promise.all(promises);
      message.success('Membros atualizados com sucesso');
      setMembersModalVisible(false);
      fetchGrupos();
      fetchUsuarios();
    } catch (error) {
      message.error(`Erro ao atualizar membros: ${error.message}`);
    } finally {
      setSavingMembers(false);
    }
  };

  const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 60 },
    { title: 'Nome', dataIndex: 'name', key: 'name', width: 250 },
    {
      title: 'Usuários',
      dataIndex: 'user_count',
      key: 'user_count',
      width: 100,
      render: (count) => <Tag color="blue">{count || 0} usuário(s)</Tag>,
    },
    {
      title: 'Permissões',
      dataIndex: 'permissions',
      key: 'permissions',
      width: 120,
      render: (perms) => <Tag color="purple">{perms?.length || 0} perm(s)</Tag>,
    },
    {
      title: 'Ações',
      key: 'acoes',
      width: 250,
      render: (_, record) => (
        <Space>
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
            icon={<UserAddOutlined />}
            onClick={() => handleManageMembers(record)}
          >
            Gerenciar Membros
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div className="p-6 bg-gray-100" style={{ minHeight: 'calc(100vh - 64px)' }}>
      <div className="mb-4">
        <Link to="/admin-dat">← Voltar para Admin DAT</Link>
      </div>

      <Card>
        <div className="flex justify-between items-center mb-4">
          <Title level={3} className="m-0">
            <TeamOutlined /> Grupos ({grupos.length})
          </Title>
          <Space>
            <Search
              placeholder="Buscar por nome"
              allowClear
              style={{ width: 250 }}
              onSearch={setSearchText}
              onChange={(e) => !e.target.value && setSearchText('')}
            />
            <Button icon={<ReloadOutlined />} onClick={fetchGrupos} loading={loading}>
              Atualizar
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              Novo Grupo
            </Button>
          </Space>
        </div>

        <Table
          columns={columns}
          dataSource={grupos}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 15, showTotal: (total) => `Total: ${total}` }}
          scroll={{ x: 900 }}
        />
      </Card>

      {/* Modal Criar/Editar Grupo */}
      <Modal
        title={editingGroup ? 'Editar Grupo' : 'Novo Grupo'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={() => form.submit()}
        okText="Salvar"
        cancelText="Cancelar"
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSave}
        >
          <Form.Item
            name="name"
            label="Nome do Grupo"
            rules={[{ required: true, message: 'Nome é obrigatório' }]}
          >
            <Input placeholder="Ex: DAT, Superintendência, Coordenador" />
          </Form.Item>
        </Form>
      </Modal>

      {/* Modal Gerenciar Membros */}
      <Modal
        title={`Gerenciar Membros - ${selectedGroup?.name}`}
        open={membersModalVisible}
        onCancel={() => setMembersModalVisible(false)}
        onOk={handleSaveMembers}
        okText="Salvar"
        cancelText="Cancelar"
        confirmLoading={savingMembers}
        width={600}
      >
        <div className="mb-4">
          <Typography.Text type="secondary">
            Selecione os usuários que devem pertencer a este grupo:
          </Typography.Text>
        </div>

        <Checkbox.Group
          style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '8px' }}
          value={selectedUsers}
          onChange={setSelectedUsers}
        >
          {usuarios.map((usuario) => (
            <Checkbox key={usuario.id} value={usuario.id}>
              {usuario.username} ({usuario.email})
            </Checkbox>
          ))}
        </Checkbox.Group>
      </Modal>
    </div>
  );
}
