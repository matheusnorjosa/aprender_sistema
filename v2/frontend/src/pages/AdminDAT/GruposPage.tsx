/**
 * Admin DAT - Grupos
 *
 * CRUD de grupos Django com gestão de membros.
 * Fase 1 Iteração 3 - Plano DAT/GCal 2025-10-29
 */

import { useState, useEffect } from 'react';
import { Table, Button, Input, Space, Tag, Typography, Card, message, Modal, Form, Checkbox } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { TeamOutlined, ReloadOutlined, EditOutlined, PlusOutlined, UserAddOutlined } from '@ant-design/icons';
import { Link } from 'react-router-dom';
import { listGroups, createGroup, updateGroup, listUsers, assignGroups } from '../../api/adminDAT';
import { PAGE_SIZES } from '../../constants';
import type { ID } from '../../types';

const { Title } = Typography;
const { Search } = Input;

/**
 * Group record interface
 */
interface GroupRecord {
  id: ID;
  name: string;
  user_count?: number;
  permissions?: unknown[];
}

/**
 * User record interface for members management
 */
interface UserRecord {
  id: ID;
  username: string;
  email: string;
  groups?: Array<{ id: ID } | ID>;
}

/**
 * Group form values interface
 */
interface GroupFormValues {
  name: string;
}

export default function GruposPage(): JSX.Element {
  const [grupos, setGrupos] = useState<GroupRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [modalVisible, setModalVisible] = useState(false);
  const [editingGroup, setEditingGroup] = useState<GroupRecord | null>(null);
  const [membersModalVisible, setMembersModalVisible] = useState(false);
  const [selectedGroup, setSelectedGroup] = useState<GroupRecord | null>(null);
  const [usuarios, setUsuarios] = useState<UserRecord[]>([]);
  const [selectedUsers, setSelectedUsers] = useState<ID[]>([]);
  const [savingMembers, setSavingMembers] = useState(false);

  const [form] = Form.useForm<GroupFormValues>();

  const fetchGrupos = async (): Promise<void> => {
    setLoading(true);
    try {
      const data = await listGroups({
        search: searchText,
        ordering: 'name',
      });
      setGrupos(data.results as GroupRecord[]);
    } catch (error) {
      message.error(`Erro ao carregar grupos: ${(error as Error).message}`);
    } finally {
      setLoading(false);
    }
  };

  const fetchUsuarios = async (): Promise<void> => {
    try {
      const data = await listUsers({ ordering: 'username', page_size: PAGE_SIZES.ALL });
      setUsuarios(data.results as UserRecord[]);
    } catch (error) {
      message.error(`Erro ao carregar usuários: ${(error as Error).message}`);
    }
  };

  useEffect(() => {
    fetchGrupos();
  }, [searchText]);

  useEffect(() => {
    fetchUsuarios();
  }, []);

  const handleCreate = (): void => {
    setEditingGroup(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (group: GroupRecord): void => {
    setEditingGroup(group);
    form.setFieldsValue(group);
    setModalVisible(true);
  };

  const handleSave = async (values: GroupFormValues): Promise<void> => {
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
      message.error(`Erro: ${(error as Error).message}`);
    }
  };

  const handleManageMembers = async (group: GroupRecord): Promise<void> => {
    setSelectedGroup(group);
    setMembersModalVisible(true);

    // Carregar usuários que já estão no grupo
    const usersInGroup = usuarios.filter((u) =>
      u.groups && u.groups.some((g) => {
        const gId = typeof g === 'object' ? g.id : g;
        return gId === group.id;
      })
    );
    setSelectedUsers(usersInGroup.map((u) => u.id));
  };

  const handleSaveMembers = async (): Promise<void> => {
    if (!selectedGroup) return;

    setSavingMembers(true);
    try {
      const promises = usuarios.map(async (usuario) => {
        const isSelected = selectedUsers.includes(usuario.id);
        const currentGroups = usuario.groups
          ? usuario.groups.map((g) => (typeof g === 'object' ? g.id : g))
          : [];
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
      message.error(`Erro ao atualizar membros: ${(error as Error).message}`);
    } finally {
      setSavingMembers(false);
    }
  };

  const columns: ColumnsType<GroupRecord> = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 60 },
    { title: 'Nome', dataIndex: 'name', key: 'name', width: 250 },
    {
      title: 'Usuários',
      dataIndex: 'user_count',
      key: 'user_count',
      width: 100,
      render: (count: number | undefined) => <Tag color="blue">{count || 0} usuário(s)</Tag>,
    },
    {
      title: 'Permissões',
      dataIndex: 'permissions',
      key: 'permissions',
      width: 120,
      render: (perms: unknown[] | undefined) => <Tag color="purple">{perms?.length || 0} perm(s)</Tag>,
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
    <section className="p-6 bg-gray-100" style={{ minHeight: 'calc(100vh - 64px)' }} aria-labelledby="grupos-title">
      <nav className="mb-4" aria-label="Navegação">
        <Link to="/dat/admin">← Voltar para Admin DAT</Link>
      </nav>

      <Card>
        <header className="flex justify-between items-center mb-4">
          <Title level={3} className="m-0" id="grupos-title">
            <TeamOutlined aria-hidden="true" /> Grupos ({grupos.length})
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
        </header>

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
          className="w-full flex flex-col gap-2"
          value={selectedUsers}
          onChange={(values) => setSelectedUsers(values as ID[])}
        >
          {usuarios.map((usuario) => (
            <Checkbox key={String(usuario.id)} value={usuario.id}>
              {usuario.username} ({usuario.email})
            </Checkbox>
          ))}
        </Checkbox.Group>
      </Modal>
    </section>
  );
}
