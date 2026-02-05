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
import { Table, Button, Input, Space, Tag, Typography, Card, message, Modal, Form, Select, Divider } from 'antd';
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table';
import type { FilterValue, SorterResult } from 'antd/es/table/interface';
import { ReloadOutlined, EditOutlined, PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import { Link } from 'react-router-dom';
import { listUsers, createUser, updateUser, deleteUser, listGroups } from '../../api/adminDAT';
import logger from '../../utils/logger';
import { PAGE_SIZES } from '../../constants';
import type { ID } from '../../types';

const { Title, Text } = Typography;
const { Search } = Input;

// Grupos de SETOR e FUNÇÃO para RBAC (sincronizado com backend)
const SETOR_GROUPS = [
  'Superintendência', 'Vidas', 'Fluir', 'ACerta', 'Brincando', 'Sou da Paz',
  'DAT', 'Controle', 'Gerência'
];
const FUNCAO_GROUPS = ['Formador', 'Coordenador', 'Apoio de Coordenação', 'Gerente'];

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
  is_active: boolean;
  groups?: string[];
  group_ids_display?: ID[];
}

/**
 * Group record interface
 */
interface GroupRecord {
  id: ID;
  name: string;
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

  const [form] = Form.useForm<UserFormValues>();

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

  // Fetch groups on mount
  const fetchGrupos = async (): Promise<void> => {
    try {
      const data = await listGroups();
      setGrupos(data.results as GroupRecord[]);
    } catch (error) {
      logger.error('Erro ao carregar grupos:', error);
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
    setModalVisible(true);
  };

  const handleEdit = (user: UserRecord): void => {
    setEditingUser(user);
    // Separar IDs de grupos por tipo
    const userGroupIds = user.group_ids_display || [];
    const setorIds = grupos
      .filter(g => SETOR_GROUPS.includes(g.name) && userGroupIds.includes(g.id))
      .map(g => g.id);
    const funcaoIds = grupos
      .filter(g => FUNCAO_GROUPS.includes(g.name) && userGroupIds.includes(g.id))
      .map(g => g.id);

    form.setFieldsValue({
      username: user.username,
      email: user.email,
      first_name: user.first_name,
      last_name: user.last_name,
      cpf: user.cpf,
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
      const { setor_ids = [], funcao_ids = [], ...rest } = values;
      const payload = {
        ...rest,
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
      dataIndex: 'cpf',
      key: 'cpf',
      width: 150,
      render: (cpf: string | undefined) => cpf || <Tag color="orange">Sem CPF</Tag>,
    },
    {
      title: 'Setor',
      key: 'setor',
      render: (_, record) => {
        const setores = (record.groups || []).filter(g => SETOR_GROUPS.includes(g));
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
        const funcoes = (record.groups || []).filter(g => FUNCAO_GROUPS.includes(g));
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
      width: 100,
      render: (is_active: boolean) => (
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
    <section className="p-6 bg-gray-100" style={{ minHeight: 'calc(100vh - 64px)' }} aria-labelledby="usuarios-title">
      {/* Header */}
      <nav className="mb-4" aria-label="Navegação">
        <Link to="/dat/admin">← Voltar para Admin DAT</Link>
      </nav>

      <Card>
        <header className="flex justify-between items-center mb-4">
          <Title level={3} className="m-0" id="usuarios-title">
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
        </header>

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

          <Divider orientation="left">Grupos RBAC</Divider>

          <Form.Item
            name="setor_ids"
            label="Setor (onde trabalha)"
            tooltip="Gerência ou departamento do usuário"
            rules={[{ required: true, message: 'Selecione pelo menos um setor' }]}
          >
            <Select
              mode="multiple"
              placeholder="Selecione o(s) setor(es)"
              options={grupos
                .filter((g) => SETOR_GROUPS.includes(g.name))
                .map((g) => ({ label: g.name, value: g.id }))}
            />
          </Form.Item>

          <Form.Item
            name="funcao_ids"
            label="Função (o que pode fazer)"
            tooltip="Papel/cargo que define permissões"
            rules={[{ required: true, message: 'Selecione pelo menos uma função' }]}
          >
            <Select
              mode="multiple"
              placeholder="Selecione a(s) função(ões)"
              options={grupos
                .filter((g) => FUNCAO_GROUPS.includes(g.name))
                .map((g) => ({ label: g.name, value: g.id }))}
            />
          </Form.Item>

          <Text type="secondary" className="block mb-4">
            Nota: Apenas <Tag color="gold">Gerente</Tag> + <Tag color="purple">Superintendência</Tag> pode aprovar solicitações SUPER.
          </Text>

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
