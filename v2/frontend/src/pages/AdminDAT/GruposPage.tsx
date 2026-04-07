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
  Select,
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
  group_type?: string | null;
  user_count?: number;
  permissions?: string[];
  permissoes_funcionais?: PermissaoFuncional[];
}

interface UserRecord {
  id: ID;
  username: string;
  email: string;
  groups?: string[];
  group_ids_display?: ID[];
}

interface GroupFormValues {
  name: string;
  group_type_input: 'setor' | 'funcao';
  permissao_funcional_ids: ID[];
  member_ids: ID[];
}

interface GruposPageProps {
  forcedType?: 'setor' | 'funcao';
}

const CATEGORY_LABELS: Record<string, { title: string; help: string }> = {
  admin_dat: {
    title: 'Administração DAT',
    help: 'Permissões para operar cadastros e configurações administrativas.',
  },
  dashboard: {
    title: 'Dashboards',
    help: 'Permissões para visualizar indicadores e painéis analíticos.',
  },
  gerencia: {
    title: 'Gerência',
    help: 'Permissões de atuação gerencial e supervisão operacional.',
  },
  importacao: {
    title: 'Importações',
    help: 'Permissões para importar dados de planilhas e arquivos.',
  },
  operacao: {
    title: 'Operações',
    help: 'Permissões de operação do dia a dia no sistema.',
  },
};

const TYPE_UI: Record<'setor' | 'funcao', { title: string; create: string; singular: string }> = {
  setor: { title: 'Setores', create: 'Novo Setor', singular: 'Setor' },
  funcao: { title: 'Funções', create: 'Nova Função', singular: 'Função' },
};

function humanizeCategory(category: string): string {
  return category
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export default function GruposPage({ forcedType }: GruposPageProps = {}): JSX.Element {
  const [grupos, setGrupos] = useState<GroupRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [modalVisible, setModalVisible] = useState(false);
  const [editingGroup, setEditingGroup] = useState<GroupRecord | null>(null);
  const [savingGroup, setSavingGroup] = useState(false);
  const [deletingGroupId, setDeletingGroupId] = useState<ID | null>(null);

  const [usuarios, setUsuarios] = useState<UserRecord[]>([]);

  const [permissoesDisponiveis, setPermissoesDisponiveis] = useState<PermissaoFuncional[]>([]);
  const [rbacMeta, setRbacMeta] = useState<RBACMetaPayload | null>(null);

  const [form] = Form.useForm<GroupFormValues>();
  const selectedPermissionIds = Form.useWatch('permissao_funcional_ids', form) || [];
  const selectedMemberIds = Form.useWatch('member_ids', form) || [];
  const selectedGroupType = Form.useWatch('group_type_input', form) || forcedType || 'setor';
  const pageTypeMeta = forcedType ? TYPE_UI[forcedType] : null;

  const reservedGroupNames = useMemo(
    () => new Set([...(rbacMeta?.setor_groups || []), ...(rbacMeta?.funcao_groups || [])]),
    [rbacMeta]
  );

  const currentMemberIds = useMemo(() => {
    if (!editingGroup) {
      return [];
    }
    return usuarios
      .filter((usuario) => (usuario.group_ids_display || []).includes(editingGroup.id))
      .map((usuario) => usuario.id);
  }, [editingGroup, usuarios]);

  const membershipDelta = useMemo(() => {
    const current = new Set(currentMemberIds);
    const selected = new Set(selectedMemberIds);
    const added = selectedMemberIds.filter((id) => !current.has(id)).length;
    const removed = currentMemberIds.filter((id) => !selected.has(id)).length;
    return { added, removed };
  }, [currentMemberIds, selectedMemberIds]);

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
        categoryTitle: CATEGORY_LABELS[category]?.title || humanizeCategory(category),
        categoryHelp: CATEGORY_LABELS[category]?.help || 'Permissões relacionadas a este módulo.',
        permissions: perms.sort((a, b) => a.label.localeCompare(b.label)),
      }));
  }, [permissoesDisponiveis]);

  const isReservedGroup = (groupName: string): boolean => reservedGroupNames.has(groupName);

  const inferGroupType = (group: GroupRecord): 'setor' | 'funcao' | undefined => {
    if (group.group_type === 'setor' || group.group_type === 'funcao') {
      return group.group_type;
    }
    if (rbacMeta?.setor_groups.includes(group.name)) {
      return 'setor';
    }
    if (rbacMeta?.funcao_groups.includes(group.name)) {
      return 'funcao';
    }
    return undefined;
  };

  const fetchGrupos = async (): Promise<void> => {
    setLoading(true);
    try {
      const data = await listGroups({
        search: searchText,
        ordering: 'name',
        page_size: PAGE_SIZES.ALL,
      });
      const loaded = data.results as GroupRecord[];
      if (!forcedType) {
        setGrupos(loaded);
        return;
      }

      const fallbackTypes = new Set(
        forcedType === 'setor' ? (rbacMeta?.setor_groups || []) : (rbacMeta?.funcao_groups || [])
      );
      const filtered = loaded.filter((group) => {
        if (group.group_type) {
          return group.group_type === forcedType;
        }
        return fallbackTypes.has(group.name);
      });
      setGrupos(filtered);
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
  }, [searchText, forcedType, rbacMeta]);

  useEffect(() => {
    fetchUsuarios();
    fetchPermissoesAndMeta();
  }, []);

  const handleCreate = (): void => {
    setEditingGroup(null);
    form.resetFields();
    form.setFieldsValue({
      name: '',
      group_type_input: 'setor',
      permissao_funcional_ids: [],
      member_ids: [],
    });
    setModalVisible(true);
  };

  const handleEdit = async (group: GroupRecord): Promise<void> => {
    try {
      const groupDetail = (await getGroup(group.id)) as GroupRecord;
      setEditingGroup(groupDetail);
      const memberIds = usuarios
        .filter((usuario) => (usuario.group_ids_display || []).includes(group.id))
        .map((usuario) => usuario.id);
      const groupType = inferGroupType(groupDetail);
      form.setFieldsValue({
        name: groupDetail.name,
        group_type_input: groupType || 'setor',
        permissao_funcional_ids: (groupDetail.permissoes_funcionais || []).map((permissao) => permissao.id),
        member_ids: memberIds,
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
      const { member_ids = [], ...groupPayload } = values;
      let groupId: ID;

      if (editingGroup) {
        await updateGroup(editingGroup.id, groupPayload, options);
        groupId = editingGroup.id;
      } else {
        const createdGroup = await createGroup(groupPayload);
        groupId = createdGroup.id;
      }

      const syncResult = await syncGroupMembers(groupId, { user_ids: member_ids });
      if (editingGroup) {
        message.success(
          `Grupo atualizado com sucesso (+${syncResult.added}/-${syncResult.removed} membros)`
        );
      } else {
        message.success(`Grupo criado com sucesso (${syncResult.members_count} membros vinculados)`);
      }
      setModalVisible(false);
      form.resetFields();
      await Promise.all([fetchGrupos(), fetchUsuarios()]);
    } catch (error) {
      message.error(`Erro ao salvar grupo: ${(error as Error).message}`);
    } finally {
      setSavingGroup(false);
    }
  };

  const handleSave = async (values: GroupFormValues): Promise<void> => {
    const payload = forcedType ? { ...values, group_type_input: forcedType } : values;
    if (editingGroup && isReservedGroup(editingGroup.name) && payload.name !== editingGroup.name) {
      Modal.confirm({
        title: 'Grupo reservado',
        content:
          'Você está renomeando um grupo reservado. Confirma que deseja continuar com essa alteração?',
        okText: 'Confirmar renomeação',
        cancelText: 'Cancelar',
        onOk: () => persistGroup(payload, { confirmReserved: true }),
      });
      return;
    }

    await persistGroup(payload);
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
      title: 'Tipo',
      dataIndex: 'group_type',
      key: 'group_type',
      width: 120,
      render: (_: GroupRecord['group_type'], record: GroupRecord) => {
        const type = inferGroupType(record);
        if (type === 'funcao') {
          return <Tag color="geekblue">Função</Tag>;
        }
        if (type === 'setor') {
          return <Tag color="green">Setor</Tag>;
        }
        return <Text type="secondary">-</Text>;
      },
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
      width: 220,
      render: (_, record) => {
        const reserved = isReservedGroup(record.name);
        return (
          <Space>
            <Button type="link" size="small" icon={<EditOutlined />} onClick={() => void handleEdit(record)}>
              Editar
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
            <TeamOutlined aria-hidden="true" /> {pageTypeMeta ? pageTypeMeta.title : 'Grupos RBAC'} ({grupos.length})
          </Title>
          <Space>
            <Search
              placeholder={pageTypeMeta ? `Buscar ${pageTypeMeta.singular.toLowerCase()} por nome` : 'Buscar por nome'}
              allowClear
              style={{ width: '100%', maxWidth: 250 }}
              onSearch={setSearchText}
              onChange={(event) => !event.target.value && setSearchText('')}
            />
            <Button icon={<ReloadOutlined />} onClick={() => void fetchGrupos()} loading={loading}>
              Atualizar
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              {pageTypeMeta ? pageTypeMeta.create : 'Novo Grupo'}
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
        title={
          editingGroup
            ? `Editar ${pageTypeMeta ? pageTypeMeta.singular : 'Grupo'}`
            : (pageTypeMeta ? pageTypeMeta.create : 'Novo Grupo')
        }
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={() => form.submit()}
        okText="Salvar"
        cancelText="Cancelar"
        confirmLoading={savingGroup}
        width={820}
      >
        <Form form={form} layout="vertical" autoComplete="off" onFinish={(values) => void handleSave(values)}>
          <Form.Item
            name="name"
            label={`Nome do ${pageTypeMeta ? pageTypeMeta.singular : 'Grupo'}`}
            rules={[{ required: true, message: 'Nome é obrigatório' }]}
          >
            <Input placeholder={pageTypeMeta ? `Ex: ${pageTypeMeta.singular} Pedagógico` : 'Ex: DAT, Superintendência, Coordenador'} />
          </Form.Item>

          {!forcedType ? (
            <Form.Item
              name="group_type_input"
              label="Tipo do Grupo"
              rules={[{ required: true, message: 'Tipo do grupo é obrigatório' }]}
            >
              <Select
                options={[
                  { label: 'Setor (onde o usuário trabalha)', value: 'setor' },
                  { label: 'Função (o que o usuário pode fazer)', value: 'funcao' },
                ]}
              />
            </Form.Item>
          ) : null}

          <Form.Item
            name="permissao_funcional_ids"
            label={selectedGroupType === 'funcao' ? 'Permissões de acesso da Função' : 'Permissões de acesso'}
            extra="Use termos de negócio: selecione apenas o necessário para este perfil."
          >
            {permissionsByCategory.length === 0 ? (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description="Nenhuma permissão funcional disponível"
              />
            ) : (
              <Checkbox.Group className="w-full">
                <Space direction="vertical" className="w-full" size="middle">
                  {permissionsByCategory.map(({ category, categoryTitle, categoryHelp, permissions }) => (
                    <Card
                      key={category}
                      size="small"
                      title={
                        <Space direction="vertical" size={0}>
                          <Text strong>{categoryTitle}</Text>
                          <Text type="secondary" style={{ fontSize: 12 }}>{categoryHelp}</Text>
                        </Space>
                      }
                    >
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                        {permissions.map((permissao) => (
                          <Checkbox key={permissao.id} value={permissao.id}>
                            <Space direction="vertical" size={0}>
                              <Text>{permissao.label}</Text>
                              {permissao.description ? (
                                <Text type="secondary" style={{ fontSize: 12 }}>
                                  {permissao.description}
                                </Text>
                              ) : null}
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

          <Form.Item
            name="member_ids"
            label="Membros do grupo"
            tooltip="Selecione os usuários que devem pertencer a este grupo"
          >
            <Select
              mode="multiple"
              allowClear
              showSearch
              placeholder="Selecione os membros"
              optionFilterProp="label"
              options={usuarios.map((usuario) => ({
                label: `${usuario.username} (${usuario.email})`,
                value: usuario.id,
              }))}
            />
          </Form.Item>

          <Card size="small" title="Resumo antes de salvar" className="mb-2">
            <Space direction="vertical" size={8} style={{ width: '100%' }}>
              <Text>
                Permissões selecionadas: <Tag color="purple">{selectedPermissionIds.length}</Tag>
              </Text>
              <Text>
                Membros selecionados: <Tag color="blue">{selectedMemberIds.length}</Tag>
              </Text>
              {editingGroup ? (
                <Text type="secondary">
                  Alterações de membros: +{membershipDelta.added} / -{membershipDelta.removed}
                </Text>
              ) : (
                <Text type="secondary">Novo grupo: os membros serão vinculados no mesmo salvamento.</Text>
              )}
            </Space>
          </Card>
        </Form>
      </Modal>
    </section>
  );
}

