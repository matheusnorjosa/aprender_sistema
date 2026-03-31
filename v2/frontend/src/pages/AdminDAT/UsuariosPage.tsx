/**
 * Admin DAT - Usuários
 *
 * Gestão de usuários: listagem, busca, criação/edição e atribuição de CPF.
 * Substitui uso cotidiano do Django Admin para usuários.
 *
 * Fase 1 Iteração 2 - Plano DAT/GCal 2025-10-29
 * GAP-001 (resolvido): Endpoint /api/usuarios-admin/ reativado
 */

import { useEffect, useMemo, useState } from 'react';
import {
  Table,
  Button,
  Input,
  Space,
  Tag,
  Typography,
  Card,
  message,
  Modal,
  Form,
  Select,
  Divider,
  Radio,
  Checkbox,
  Alert,
} from 'antd';
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table';
import type { FilterValue, SorterResult } from 'antd/es/table/interface';
import type { RadioChangeEvent } from 'antd/es/radio';
import { ReloadOutlined, EditOutlined, PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import { Link } from 'react-router-dom';
import { checkAuth } from '../../api/auth';
import { listUsers, createUser, updateUser, deleteUser, listGroups, getRBACMeta } from '../../api/adminDAT';
import type { PermissaoFuncional, RBACMetaPayload } from '../../api/adminDAT';
import { importUsuarios } from '../../api/ops';
import type { ImportResult } from '../../api/ops';
import ImportUploader from '../../components/ImportUploader';
import type { ValidationResult, ApplyResult } from '../../components/ImportUploader';
import logger from '../../utils/logger';
import { PAGE_SIZES } from '../../constants';
import type { ID } from '../../types';

/** View mode type */
type ViewMode = 'lista' | 'importar';

/**
 * Helper to convert ImportResult to ValidationResult format
 */
function toValidationResult(result: ImportResult): ValidationResult {
  return {
    stats: {
      created: result.created,
      updated: result.updated,
      unchanged: result.skipped,
    },
    errors: result.errors.map((e) => `Linha ${e.row}: ${e.message}`),
  };
}

/**
 * Helper to convert ImportResult to ApplyResult format
 */
function toApplyResult(result: ImportResult): ApplyResult {
  return {
    stats: {
      created: result.created,
      updated: result.updated,
      unchanged: result.skipped,
    },
  };
}

const { Title, Text } = Typography;
const { Search } = Input;

/**
 * User record interface
 */
interface UserRecord {
  id: ID;
  username: string;
  email: string;
  first_name?: string;
  last_name?: string;
  cpf?: string;
  cpf_masked?: string;
  telefone?: string;
  cargo?: string;
  is_active: boolean;
  is_superuser: boolean;
  groups?: string[];
  group_ids_display?: ID[];
}

/**
 * Group record interface
 */
interface GroupRecord {
  id: ID;
  name: string;
  permissions?: string[];
  permissoes_funcionais?: PermissaoFuncional[];
}

/**
 * User form values interface
 */
interface UserFormValues {
  username: string;
  email: string;
  first_name?: string;
  last_name?: string;
  cpf?: string;
  telefone?: string;
  cargo?: string;
  is_active: boolean;
  is_superuser: boolean;
  setor_ids: ID[];
  funcao_ids: ID[];
  password?: string;
}

/**
 * Pagination state interface
 */
interface PaginationState {
  current: number;
  pageSize: number;
  total: number;
}

/**
 * Fetch params interface
 */
interface FetchParams {
  current?: number;
  pageSize?: number;
  ordering?: string;
}

export default function UsuariosPage(): JSX.Element {
  const [usuarios, setUsuarios] = useState<UserRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [pagination, setPagination] = useState<PaginationState>({
    current: 1,
    pageSize: PAGE_SIZES.SMALL,
    total: 0,
  });
  const [modalVisible, setModalVisible] = useState(false);
  const [editingUser, setEditingUser] = useState<UserRecord | null>(null);
  const [grupos, setGrupos] = useState<GroupRecord[]>([]);
  const [rbacMeta, setRbacMeta] = useState<RBACMetaPayload | null>(null);
  const [currentIsSuperuser, setCurrentIsSuperuser] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>('lista');

  const [form] = Form.useForm<UserFormValues>();
  const selectedSetorIds = Form.useWatch('setor_ids', form) || [];
  const selectedFuncaoIds = Form.useWatch('funcao_ids', form) || [];

  const setorGroupsSet = useMemo(
    () => new Set(rbacMeta?.setor_groups || []),
    [rbacMeta]
  );
  const funcaoGroupsSet = useMemo(
    () => new Set(rbacMeta?.funcao_groups || []),
    [rbacMeta]
  );

  const setorOptions = useMemo(
    () => grupos
      .filter((g) => setorGroupsSet.has(g.name))
      .sort((a, b) => a.name.localeCompare(b.name))
      .map((g) => ({ label: g.name, value: g.id })),
    [grupos, setorGroupsSet]
  );

  const funcaoOptions = useMemo(
    () => grupos
      .filter((g) => funcaoGroupsSet.has(g.name))
      .sort((a, b) => a.name.localeCompare(b.name))
      .map((g) => ({ label: g.name, value: g.id })),
    [grupos, funcaoGroupsSet]
  );

  /**
   * Fetch users from API
   */
  const fetchUsuarios = async (params: FetchParams = {}): Promise<void> => {
    setLoading(true);
    try {
      const apiParams: Record<string, unknown> = {};

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

      const data = await listUsers(apiParams);

      // DRF pagination response structure
      // Note: API returns AdminUser with Group[], component uses string[]
      // This is acceptable during migration - will be unified in strict mode phase
      setUsuarios(data.results as unknown as UserRecord[]);
      setPagination({
        current: params.current || pagination.current,
        pageSize: params.pageSize || pagination.pageSize,
        total: data.count || data.results.length,
      });
    } catch (error) {
      message.error(`Erro ao carregar usuários: ${(error as Error).message}`);
      logger.error('Erro ao carregar usuários:', error);
    } finally {
      setLoading(false);
    }
  };

  // Fetch RBAC metadata and groups for dynamic classification
  const fetchRbacContext = async (): Promise<void> => {
    try {
      const [groupsData, meta] = await Promise.all([
        listGroups({ ordering: 'name', page_size: PAGE_SIZES.ALL }),
        getRBACMeta(),
      ]);
      setGrupos(groupsData.results as GroupRecord[]);
      setRbacMeta(meta);
    } catch (error) {
      logger.error('Erro ao carregar contexto RBAC:', error);
      message.error('Erro ao carregar metadados RBAC');
    }
  };

  // Load RBAC context and current auth profile on mount
  useEffect(() => {
    void fetchRbacContext();
    void (async () => {
      const auth = await checkAuth();
      setCurrentIsSuperuser(Boolean(auth.user?.is_superuser));
    })();
  }, []);

  // Load users on mount and search change (reset to page 1)
  useEffect(() => {
    fetchUsuarios({ current: 1 });
  }, [searchText]);

  const handleTableChange = (
    newPagination: TablePaginationConfig,
    _filters: Record<string, FilterValue | null>,
    sorter: SorterResult<UserRecord> | SorterResult<UserRecord>[]
  ): void => {
    const params: FetchParams = {
      current: newPagination.current,
      pageSize: newPagination.pageSize,
    };

    // Handle single sorter
    const singleSorter = Array.isArray(sorter) ? sorter[0] : sorter;
    if (singleSorter && singleSorter.field) {
      params.ordering = `${singleSorter.order === 'descend' ? '-' : ''}${String(singleSorter.field)}`;
    }

    fetchUsuarios(params);
  };

  const handleCreate = (): void => {
    setEditingUser(null);
    form.resetFields();
    form.setFieldsValue({
      is_active: true,
      is_superuser: false,
      setor_ids: [],
      funcao_ids: [],
    });
    setModalVisible(true);
  };

  const handleEdit = (user: UserRecord): void => {
    setEditingUser(user);
    // Separar IDs de grupos por tipo
    const userGroupIds = user.group_ids_display || [];
    const setorIds = grupos
      .filter((g) => setorGroupsSet.has(g.name) && userGroupIds.includes(g.id))
      .map(g => g.id);
    const funcaoIds = grupos
      .filter((g) => funcaoGroupsSet.has(g.name) && userGroupIds.includes(g.id))
      .map(g => g.id);

    form.setFieldsValue({
      username: user.username,
      email: user.email,
      first_name: user.first_name,
      last_name: user.last_name,
      cpf: user.cpf,
      telefone: user.telefone,
      cargo: user.cargo,
      is_active: user.is_active,
      is_superuser: user.is_superuser,
      setor_ids: setorIds,
      funcao_ids: funcaoIds,
    });
    setModalVisible(true);
  };

  const handleDelete = (user: UserRecord): void => {
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
          message.error(`Erro ao excluir: ${(error as Error).message}`);
        }
      },
    });
  };

  const handleSave = async (values: UserFormValues): Promise<void> => {
    try {
      // Combinar setor_ids e funcao_ids em group_ids
      const { setor_ids = [], funcao_ids = [], is_superuser, ...rest } = values;
      const payload = {
        ...rest,
        ...(currentIsSuperuser ? { is_superuser } : {}),
        group_ids: [...setor_ids, ...funcao_ids],
      };

      if (editingUser) {
        await updateUser(editingUser.id, payload);
        message.success('Usuário atualizado com sucesso');
      } else {
        await createUser(payload);
        message.success('Usuário criado com sucesso');
      }
      setModalVisible(false);
      form.resetFields();
      fetchUsuarios();
    } catch (error) {
      message.error(`Erro: ${(error as Error).message}`);
    }
  };

  const columns: ColumnsType<UserRecord> = [
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
      dataIndex: 'cpf_masked',
      key: 'cpf',
      width: 150,
      render: (cpfMasked: string | undefined) => cpfMasked || <Tag color="orange">Sem CPF</Tag>,
    },
    {
      title: 'Telefone',
      dataIndex: 'telefone',
      key: 'telefone',
      width: 150,
      render: (telefone: string | undefined) => telefone || <Text type="secondary">-</Text>,
    },
    {
      title: 'Cargo',
      dataIndex: 'cargo',
      key: 'cargo',
      width: 180,
      render: (cargo: string | undefined) => cargo || <Text type="secondary">-</Text>,
    },
    {
      title: 'Setor',
      key: 'setor',
      render: (_, record) => {
        const setores = (record.groups || []).filter((g) => setorGroupsSet.has(g));
        return setores.length > 0 ? (
          setores.map((g) => (
            <Tag key={g} color="purple">{g}</Tag>
          ))
        ) : (
          <Text type="secondary">-</Text>
        );
      },
      width: 150,
    },
    {
      title: 'Função',
      key: 'funcao',
      render: (_, record) => {
        const funcoes = (record.groups || []).filter((g) => funcaoGroupsSet.has(g));
        return funcoes.length > 0 ? (
          funcoes.map((g) => (
            <Tag key={g} color={g === 'Gerente' ? 'gold' : 'blue'}>{g}</Tag>
          ))
        ) : (
          <Text type="secondary">-</Text>
        );
      },
      width: 180,
    },
    {
      title: 'Status',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 180,
      render: (is_active: boolean, record: UserRecord) => (
        <Space>
          <Tag color={is_active ? 'green' : 'red'}>{is_active ? 'Ativo' : 'Inativo'}</Tag>
          {record.is_superuser ? <Tag color="gold">Superuser</Tag> : null}
        </Space>
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
    <section className="p-6 bg-gray-100" style={{ minHeight: 'calc(100vh - 64px)' }} aria-labelledby="usuarios-title">
      {/* Header */}
      <nav className="mb-4" aria-label="Navegação">
        <Link to="/dat/admin">← Voltar para Admin DAT</Link>
      </nav>

      <Card>
        <header className="flex justify-between items-center mb-4">
          <Title level={3} className="m-0" id="usuarios-title">
            {viewMode === 'lista'
              ? `Usuários (${pagination.total})`
              : 'Importar Usuários'}
          </Title>
          <Radio.Group
            value={viewMode}
            onChange={(e: RadioChangeEvent) => setViewMode(e.target.value)}
            buttonStyle="solid"
          >
            <Radio.Button value="lista">Lista</Radio.Button>
            <Radio.Button value="importar">Importar</Radio.Button>
          </Radio.Group>
          {viewMode === 'lista' && (
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
          )}
        </header>

        {viewMode === 'lista' ? (
          /* Tabela */
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
        ) : (
          /* Importação */
          <ImportUploader
            label="Importar Usuários de CSV/XLSX"
            description="Colunas obrigatórias: cpf, nome. Opcionais: email, telefone, cargo, grupos (separados por vírgula). O CPF é a chave de idempotência."
            onDryRun={async (file: File) => toValidationResult(await importUsuarios(file, true) as unknown as ImportResult)}
            onApply={async (file: File) => {
              const result = await importUsuarios(file, false);
              // Recarregar lista após importação
              fetchUsuarios();
              return toApplyResult(result as unknown as ImportResult);
            }}
          />
        )}
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
              { required: true, message: 'CPF é obrigatório' },
              {
                pattern: /^[0-9]{11}$/,
                message: 'CPF deve conter exatamente 11 dígitos numéricos',
              },
            ]}
          >
            <Input placeholder="12345678901 (apenas números)" maxLength={11} />
          </Form.Item>

          <Form.Item name="telefone" label="Telefone">
            <Input placeholder="Ex: 85999990000" maxLength={20} />
          </Form.Item>

          <Form.Item name="cargo" label="Cargo">
            <Input placeholder="Ex: Coordenador Pedagógico" maxLength={100} />
          </Form.Item>

          <Space size={24} className="mb-4">
            <Form.Item name="is_active" valuePropName="checked" style={{ marginBottom: 0 }}>
              <Checkbox>Usuário ativo</Checkbox>
            </Form.Item>

            {currentIsSuperuser ? (
              <Form.Item name="is_superuser" valuePropName="checked" style={{ marginBottom: 0 }}>
                <Checkbox>Superusuário</Checkbox>
              </Form.Item>
            ) : null}
          </Space>

          {!currentIsSuperuser ? (
            <Alert
              type="info"
              showIcon
              className="mb-4"
              message="Somente superusuários podem alterar privilégio de superusuário."
            />
          ) : null}

          <Divider orientation="left">Perfil de Acesso</Divider>

          <Alert
            type="info"
            showIcon
            className="mb-4"
            message="Como configurar"
            description="Setor define onde a pessoa atua. Função define o que a pessoa pode fazer no sistema."
          />

          <Form.Item
            name="setor_ids"
            label="Setor (onde trabalha)"
            tooltip="Unidade/área de atuação da pessoa"
            rules={[{ required: true, message: 'Selecione pelo menos um setor' }]}
          >
            <Select
              mode="multiple"
              allowClear
              showSearch
              optionFilterProp="label"
              maxTagCount="responsive"
              placeholder="Selecione um ou mais setores"
              options={setorOptions}
            />
          </Form.Item>

          <Form.Item
            name="funcao_ids"
            label="Função (o que pode fazer)"
            tooltip="Papel da pessoa no processo"
            rules={[{ required: true, message: 'Selecione pelo menos uma função' }]}
          >
            <Select
              mode="multiple"
              allowClear
              showSearch
              optionFilterProp="label"
              maxTagCount="responsive"
              placeholder="Selecione uma ou mais funções"
              options={funcaoOptions}
            />
          </Form.Item>

          <Card size="small" title="Resumo do perfil de acesso" className="mb-4">
            <Space direction="vertical" size={8} style={{ width: '100%' }}>
              <div>
                <Text strong>Setores selecionados: </Text>
                {selectedSetorIds.length > 0 ? (
                  grupos
                    .filter((group) => selectedSetorIds.includes(group.id))
                    .map((group) => (
                      <Tag key={group.id} color="green">{group.name}</Tag>
                    ))
                ) : (
                  <Text type="secondary">nenhum setor selecionado</Text>
                )}
              </div>
              <div>
                <Text strong>Funções selecionadas: </Text>
                {selectedFuncaoIds.length > 0 ? (
                  grupos
                    .filter((group) => selectedFuncaoIds.includes(group.id))
                    .map((group) => (
                      <Tag key={group.id} color="blue">{group.name}</Tag>
                    ))
                ) : (
                  <Text type="secondary">nenhuma função selecionada</Text>
                )}
              </div>
              <div>
                <Text strong>Permissões efetivas: </Text>
                {(() => {
                  const selectedGroups = grupos.filter((group) =>
                    [...selectedSetorIds, ...selectedFuncaoIds].includes(group.id)
                  );
                  const labels = new Set<string>();
                  selectedGroups.forEach((group) => {
                    (group.permissoes_funcionais || []).forEach((permissao) => labels.add(permissao.label));
                  });
                  if (labels.size === 0) {
                    return <Text type="secondary">sem permissões específicas definidas</Text>;
                  }
                  return (
                    <>
                      <Tag color="purple">{labels.size} permissão(ões)</Tag>
                      {Array.from(labels).sort().slice(0, 6).map((label) => (
                        <Tag key={label} color="purple">{label}</Tag>
                      ))}
                      {labels.size > 6 ? <Tag>+{labels.size - 6}</Tag> : null}
                    </>
                  );
                })()}
              </div>
            </Space>
          </Card>

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
    </section>
  );
}
