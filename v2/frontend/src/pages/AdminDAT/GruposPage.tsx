/**
 * Admin DAT - Grupos
 *
 * CRUD de grupos Django com gestão de membros e permissões funcionais.
 * Fase 4a - RBAC funcional (Issue #830)
 */

import { useEffect, useMemo, useState } from 'react';
import {
  Button,
  Card,
  Checkbox,
  Empty,
  Form,
  Input,
  Modal,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  DeleteOutlined,
  EditOutlined,
  LockOutlined,
  PlusOutlined,
  ReloadOutlined,
  TeamOutlined,
  UserAddOutlined,
} from '@ant-design/icons';
import { Link } from 'react-router-dom';
import {
  createGroup,
  deleteGroup,
  getGroup,
  getRBACMeta,
  listGroups,
  listPermissoesFuncionais,
  listUsers,
  syncGroupMembers,
  updateGroup,
} from '../../api/adminDAT';
import type { PermissaoFuncional, RBACMetaPayload } from '../../api/adminDAT';
import { PAGE_SIZES } from '../../constants';
import type { ID } from '../../types';

const { Title, Text } = Typography;
const { Search } = Input;

interface GroupRecord {
  id: ID;
  name: string;
  user_count?: number;
  permissions?: string[];
  permissoes_funcionais?: PermissaoFuncional[];
}

interface UserRecord {
  id: ID;
  username: string;
  email: string;
  groups?: Array<{ id: ID } | ID>;
}

interface GroupFormValues {
  name: string;
  permissao_funcional_ids: ID[];
}

export default function GruposPage(): JSX.Element {
  const [grupos, setGrupos] = useState<GroupRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [modalVisible, setModalVisible] = useState(false);
  const [editingGroup, setEditingGroup] = useState<GroupRecord | null>(null);
  const [savingGroup, setSavingGroup] = useState(false);
  const [deletingGroupId, setDeletingGroupId] = useState<ID | null>(null);

  const [membersModalVisible, setMembersModalVisible] = useState(false);
  const [selectedGroup, setSelectedGroup] = useState<GroupRecord | null>(null);
  const [usuarios, setUsuarios] = useState<UserRecord[]>([]);
  const [selectedUsers, setSelectedUsers] = useState<ID[]>([]);
  const [savingMembers, setSavingMembers] = useState(false);

  const [permissoesDisponiveis, setPermissoesDisponiveis] = useState<PermissaoFuncional[]>([]);
  const [rbacMeta, setRbacMeta] = useState<RBACMetaPayload | null>(null);

  const [form] = Form.useForm<GroupFormValues>();

  const reservedGroupNames = useMemo(
    () => new Set([...(rbacMeta?.setor_groups || []), ...(rbacMeta?.funcao_groups || [])]),
    [rbacMeta]
  );

  const permissionsByCategory = useMemo(() => {
    const grouped = new Map<string, PermissaoFuncional[]>();
    permissoesDisponiveis.forEach((permissao) => {
      const key = permissao.category || 'geral';
      const current = grouped.get(key) || [];
      current.push(permissao);
      grouped.set(key, current);
    });

    return Array.from(grouped.entries())
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([category, perms]) => ({
        category,
        permissions: perms.sort((a, b) => a.label.localeCompare(b.label)),
      }));
  }, [permissoesDisponiveis]);

  const isReservedGroup = (groupName: string): boolean => reservedGroupNames.has(groupName);

  const fetchGrupos = async (): Promise<void> => {
    setLoading(true);
    try {
      const data = await listGroups({
        search: searchText,
        ordering: 'name',
        page_size: PAGE_SIZES.ALL,
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

  const fetchPermissoesAndMeta = async (): Promise<void> => {
    try {
      const [permissionsResponse, metaResponse] = await Promise.all([
        listPermissoesFuncionais({ ordering: 'category,label', page_size: PAGE_SIZES.ALL }),
        getRBACMeta(),
      ]);
      setPermissoesDisponiveis(permissionsResponse.results);
      setRbacMeta(metaResponse);
    } catch (error) {
      message.error(`Erro ao carregar metadados RBAC: ${(error as Error).message}`);
    }
  };

  useEffect(() => {
    fetchGrupos();
  }, [searchText]);

  useEffect(() => {
    fetchUsuarios();
    fetchPermissoesAndMeta();
  }, []);

  const handleCreate = (): void => {
    setEditingGroup(null);
    form.resetFields();
    form.setFieldsValue({ name: '', permissao_funcional_ids: [] });
    setModalVisible(true);
  };

  const handleEdit = async (group: GroupRecord): Promise<void> => {
    try {
      const groupDetail = (await getGroup(group.id)) as GroupRecord;
      setEditingGroup(groupDetail);
      form.setFieldsValue({
        name: groupDetail.name,
        permissao_funcional_ids: (groupDetail.permissoes_funcionais || []).map((permissao) => permissao.id),
      });
      setModalVisible(true);
    } catch (error) {
      message.error(`Erro ao carregar grupo para edição: ${(error as Error).message}`);
    }
  };

  const persistGroup = async (
    values: GroupFormValues,
    options: { confirmReserved?: boolean } = {}
  ): Promise<void> => {
    setSavingGroup(true);
    try {
      if (editingGroup) {
        await updateGroup(editingGroup.id, values, options);
        message.success('Grupo atualizado com sucesso');
      } else {
        await createGroup(values);
        message.success('Grupo criado com sucesso');
      }
      setModalVisible(false);
      form.resetFields();
      await fetchGrupos();
    } catch (error) {
      message.error(`Erro ao salvar grupo: ${(error as Error).message}`);
    } finally {
      setSavingGroup(false);
    }
  };

  const handleSave = async (values: GroupFormValues): Promise<void> => {
    if (editingGroup && isReservedGroup(editingGroup.name) && values.name !== editingGroup.name) {
      Modal.confirm({
        title: 'Grupo reservado',
        content:
          'Você está renomeando um grupo reservado. Confirma que deseja continuar com essa alteração?',
        okText: 'Confirmar renomeação',
        cancelText: 'Cancelar',
        onOk: () => persistGroup(values, { confirmReserved: true }),
      });
      return;
    }

    await persistGroup(values);
  };

  const handleDelete = (group: GroupRecord): void => {
    if (isReservedGroup(group.name)) {
      message.warning('Grupo reservado: exclusão bloqueada na interface.');
      return;
    }

    Modal.confirm({
      title: 'Confirmar exclusão',
      content: `Tem certeza que deseja excluir o grupo "${group.name}"?`,
      okText: 'Excluir',
      okType: 'danger',
      cancelText: 'Cancelar',
      onOk: async () => {
        setDeletingGroupId(group.id);
        try {
          await deleteGroup(group.id);
          message.success('Grupo excluído com sucesso');
          await fetchGrupos();
        } catch (error) {
          message.error(`Erro ao excluir grupo: ${(error as Error).message}`);
        } finally {
          setDeletingGroupId(null);
        }
      },
    });
  };

  const handleManageMembers = async (group: GroupRecord): Promise<void> => {
    setSelectedGroup(group);
    setMembersModalVisible(true);

    const usersInGroup = usuarios.filter(
      (usuario) =>
        usuario.groups &&
        usuario.groups.some((groupRef) => {
          const groupId = typeof groupRef === 'object' ? groupRef.id : groupRef;
          return groupId === group.id;
        })
    );
    setSelectedUsers(usersInGroup.map((user) => user.id));
  };

  const handleSaveMembers = async (): Promise<void> => {
    if (!selectedGroup) return;

    setSavingMembers(true);
    try {
      const result = await syncGroupMembers(selectedGroup.id, { user_ids: selectedUsers });
      message.success(
        `Membros atualizados com sucesso (${result.members_count} total, +${result.added}/-${result.removed})`
      );
      setMembersModalVisible(false);
      await Promise.all([fetchGrupos(), fetchUsuarios()]);
    } catch (error) {
      message.error(`Erro ao atualizar membros: ${(error as Error).message}`);
    } finally {
      setSavingMembers(false);
    }
  };

  const columns: ColumnsType<GroupRecord> = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 70 },
    {
      title: 'Nome',
      dataIndex: 'name',
      key: 'name',
      width: 260,
      render: (name: string) => (
        <Space size={8}>
          <Text>{name}</Text>
          {isReservedGroup(name) ? (
            <Tag color="gold" icon={<LockOutlined />} style={{ marginInlineEnd: 0 }}>
              Reservado
            </Tag>
          ) : null}
        </Space>
      ),
    },
    {
      title: 'Usuários',
      dataIndex: 'user_count',
      key: 'user_count',
      width: 120,
      render: (count: number | undefined) => <Tag color="blue">{count || 0} usuário(s)</Tag>,
    },
    {
      title: 'Permissões funcionais',
      dataIndex: 'permissoes_funcionais',
      key: 'permissoes_funcionais',
      width: 420,
      render: (permissoes: PermissaoFuncional[] | undefined) => {
        if (!permissoes || permissoes.length === 0) {
          return <Text type="secondary">Sem permissões funcionais</Text>;
        }

        const displayed = permissoes.slice(0, 3);
        const remaining = permissoes.length - displayed.length;

        return (
          <Space size={[4, 4]} wrap>
            {displayed.map((permissao) => (
              <Tag key={permissao.id} color="purple">
                {permissao.label}
              </Tag>
            ))}
            {remaining > 0 ? <Tag>+{remaining}</Tag> : null}
          </Space>
        );
      },
    },
    {
      title: 'Ações',
      key: 'acoes',
      width: 320,
      render: (_, record) => {
        const reserved = isReservedGroup(record.name);
        return (
          <Space>
            <Button type="link" size="small" icon={<EditOutlined />} onClick={() => void handleEdit(record)}>
              Editar
            </Button>
            <Button
              type="link"
              size="small"
              icon={<UserAddOutlined />}
              onClick={() => void handleManageMembers(record)}
            >
              Gerenciar Membros
            </Button>
            <Button
              type="link"
              danger
              size="small"
              icon={reserved ? <LockOutlined /> : <DeleteOutlined />}
              disabled={reserved}
              loading={deletingGroupId === record.id}
              onClick={() => handleDelete(record)}
            >
              Excluir
            </Button>
          </Space>
        );
      },
    },
  ];

  return (
    <section
      className="p-6 bg-gray-100"
      style={{ minHeight: 'calc(100vh - 64px)' }}
      aria-labelledby="grupos-title"
    >
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
              onChange={(event) => !event.target.value && setSearchText('')}
            />
            <Button icon={<ReloadOutlined />} onClick={() => void fetchGrupos()} loading={loading}>
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
          scroll={{ x: 1200 }}
        />
      </Card>

      <Modal
        title={editingGroup ? 'Editar Grupo' : 'Novo Grupo'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={() => form.submit()}
        okText="Salvar"
        cancelText="Cancelar"
        confirmLoading={savingGroup}
        width={820}
      >
        <Form form={form} layout="vertical" onFinish={(values) => void handleSave(values)}>
          <Form.Item
            name="name"
            label="Nome do Grupo"
            rules={[{ required: true, message: 'Nome é obrigatório' }]}
          >
            <Input placeholder="Ex: DAT, Superintendência, Coordenador" />
          </Form.Item>

          <Form.Item name="permissao_funcional_ids" label="Permissões funcionais">
            {permissionsByCategory.length === 0 ? (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description="Nenhuma permissão funcional disponível"
              />
            ) : (
              <Checkbox.Group className="w-full">
                <Space direction="vertical" className="w-full" size="middle">
                  {permissionsByCategory.map(({ category, permissions }) => (
                    <Card key={category} size="small" title={category}>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                        {permissions.map((permissao) => (
                          <Checkbox key={permissao.id} value={permissao.id}>
                            <Space direction="vertical" size={0}>
                              <Text>{permissao.label}</Text>
                              <Text type="secondary" style={{ fontSize: 12 }}>
                                {permissao.codename}
                              </Text>
                            </Space>
                          </Checkbox>
                        ))}
                      </div>
                    </Card>
                  ))}
                </Space>
              </Checkbox.Group>
            )}
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={`Gerenciar Membros - ${selectedGroup?.name}`}
        open={membersModalVisible}
        onCancel={() => setMembersModalVisible(false)}
        onOk={() => void handleSaveMembers()}
        okText="Salvar"
        cancelText="Cancelar"
        confirmLoading={savingMembers}
        width={620}
      >
        <div className="mb-4">
          <Text type="secondary">Selecione os usuários que devem pertencer a este grupo:</Text>
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

