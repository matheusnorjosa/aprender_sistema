/**
 * AdminDAT — CRUD de Projetos Gerais (#1914)
 *
 * ProjetoGeral é a FAMÍLIA de projeto (nome-base, ex.: "PROJETO AMMA"), com a política de
 * cálculo de códigos (por aluno / por professor) e o flag de AVALIAR. O ViewSet já existia
 * (/api/projetos-gerais/); esta tela dá o CRUD que faltava.
 *
 * Fora de escopo (costura backend #1914-BE): a conferência de `setor_canonico` — esse campo
 * é do model Gerencia/Projeto e não é serializado, então não entra aqui.
 */
import { useState, useEffect, type JSX } from 'react';
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
  Checkbox,
  InputNumber,
} from 'antd';
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table';
import { ReloadOutlined, EditOutlined, PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import { Link } from 'react-router';
import {
  listProjetosGerais,
  createProjetoGeral,
  updateProjetoGeral,
  deleteProjetoGeral,
  type ProjetoGeralRecord,
  type ProjetoGeralPayload,
} from '../../api/adminDAT';
import { DEFAULT_PAGE_SIZE } from '../../constants';

const { Title } = Typography;
const { Search } = Input;

const TIPO_CALCULO_OPTIONS = [
  { label: 'Por Aluno (qtde_alunos / divisor)', value: 'por_aluno' },
  { label: 'Por Professor (qtde_professores * multiplicador)', value: 'por_professor' },
  { label: 'Não Aplicável (não gera códigos)', value: 'nao_aplicavel' },
];

interface ProjetoGeralFormValues {
  nome: string;
  usa_avaliar?: boolean;
  tipo_calculo_codigos?: 'por_aluno' | 'por_professor' | 'nao_aplicavel';
  divisor_aluno?: number;
  multiplicador_professor?: number | string;
  ativo?: boolean;
  descricao?: string;
}

export default function ProjetosGeraisPage(): JSX.Element {
  const [projetos, setProjetos] = useState<ProjetoGeralRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [searchText, setSearchText] = useState<string>('');
  const [modalVisible, setModalVisible] = useState<boolean>(false);
  const [editing, setEditing] = useState<ProjetoGeralRecord | null>(null);
  const [pagination, setPagination] = useState<TablePaginationConfig>({
    current: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    total: 0,
  });
  const [form] = Form.useForm<ProjetoGeralFormValues>();

  const fetchProjetos = async (page = 1, pageSize = DEFAULT_PAGE_SIZE): Promise<void> => {
    try {
      setLoading(true);
      const data = await listProjetosGerais({
        ...(searchText && { search: searchText }),
        ordering: 'nome',
        page,
        page_size: pageSize,
      });
      setProjetos(data.results ?? []);
      setPagination((prev) => ({ ...prev, current: page, pageSize, total: data.count ?? 0 }));
    } catch (error) {
      message.error(`Erro ao carregar projetos gerais: ${(error as Error).message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchProjetos(1, pagination.pageSize ?? DEFAULT_PAGE_SIZE);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchText]);

  const handleTableChange = (p: TablePaginationConfig): void => {
    void fetchProjetos(p.current ?? 1, p.pageSize ?? DEFAULT_PAGE_SIZE);
  };

  const handleCreate = (): void => {
    setEditing(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (record: ProjetoGeralRecord): void => {
    setEditing(record);
    form.setFieldsValue({
      nome: record.nome,
      usa_avaliar: record.usa_avaliar,
      tipo_calculo_codigos: record.tipo_calculo_codigos,
      divisor_aluno: record.divisor_aluno,
      multiplicador_professor: record.multiplicador_professor,
      ativo: record.ativo,
      descricao: record.descricao,
    });
    setModalVisible(true);
  };

  const handleSave = async (values: ProjetoGeralFormValues): Promise<void> => {
    try {
      // Monta o payload só com campos definidos (exactOptionalPropertyTypes) e converte
      // multiplicador_professor para string (DecimalField no backend).
      const payload: ProjetoGeralPayload = {
        nome: values.nome,
        ...(values.usa_avaliar !== undefined && { usa_avaliar: values.usa_avaliar }),
        ...(values.tipo_calculo_codigos !== undefined && { tipo_calculo_codigos: values.tipo_calculo_codigos }),
        ...(values.divisor_aluno !== undefined && { divisor_aluno: values.divisor_aluno }),
        ...(values.multiplicador_professor != null && {
          multiplicador_professor: String(values.multiplicador_professor),
        }),
        ...(values.ativo !== undefined && { ativo: values.ativo }),
        ...(values.descricao !== undefined && { descricao: values.descricao }),
      };
      if (editing) {
        await updateProjetoGeral(editing.id, payload);
        message.success('Projeto geral atualizado');
      } else {
        await createProjetoGeral(payload);
        message.success('Projeto geral criado');
      }
      setModalVisible(false);
      void fetchProjetos(pagination.current ?? 1, pagination.pageSize ?? DEFAULT_PAGE_SIZE);
    } catch (error) {
      message.error(`Erro ao salvar: ${(error as Error).message}`);
    }
  };

  const handleDelete = (record: ProjetoGeralRecord): void => {
    Modal.confirm({
      title: 'Excluir projeto geral',
      content: `Tem certeza que deseja excluir "${record.nome}"?`,
      okText: 'Sim, excluir',
      cancelText: 'Cancelar',
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          await deleteProjetoGeral(record.id);
          message.success('Projeto geral excluído');
          void fetchProjetos(pagination.current ?? 1, pagination.pageSize ?? DEFAULT_PAGE_SIZE);
        } catch (error) {
          message.error(`Erro ao excluir: ${(error as Error).message}`);
        }
      },
    });
  };

  const columns: ColumnsType<ProjetoGeralRecord> = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 60 },
    { title: 'Nome', dataIndex: 'nome', key: 'nome', width: 260 },
    {
      title: 'Usa AVALIAR',
      dataIndex: 'usa_avaliar',
      key: 'usa_avaliar',
      width: 120,
      render: (v: boolean) => <Tag color={v ? 'green' : 'default'}>{v ? 'Sim' : 'Não'}</Tag>,
    },
    {
      title: 'Cálculo de códigos',
      dataIndex: 'tipo_calculo_codigos',
      key: 'tipo_calculo_codigos',
      width: 200,
      render: (v: string) => TIPO_CALCULO_OPTIONS.find((o) => o.value === v)?.label ?? v,
    },
    { title: 'Projetos', dataIndex: 'projetos_count', key: 'projetos_count', width: 100 },
    {
      title: 'Ativo',
      dataIndex: 'ativo',
      key: 'ativo',
      width: 90,
      render: (v: boolean) => <Tag color={v ? 'green' : 'red'}>{v ? 'Sim' : 'Não'}</Tag>,
    },
    {
      title: 'Ações',
      key: 'acoes',
      width: 150,
      render: (_, record) => (
        <Space size="small">
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)}>
            Editar
          </Button>
          <Button type="link" size="small" danger icon={<DeleteOutlined />} onClick={() => handleDelete(record)}>
            Excluir
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <section
      className="p-6 bg-gray-100"
      style={{ minHeight: 'calc(100vh - 64px)' }}
      aria-labelledby="projetos-gerais-title"
    >
      <nav aria-label="Navegação">
        <Link to="/dat/admin">← Voltar para Admin DAT</Link>
      </nav>
      <Card style={{ marginTop: 16 }}>
        <header className="flex justify-between items-center mb-4">
          <Title level={2} id="projetos-gerais-title" className="m-0">
            Projetos Gerais
          </Title>
          <Space>
            <Search
              placeholder="Buscar por nome..."
              allowClear
              onSearch={(v) => setSearchText(v)}
              style={{ width: 240 }}
            />
            <Button
              icon={<ReloadOutlined />}
              loading={loading}
              onClick={() => fetchProjetos(pagination.current ?? 1, pagination.pageSize ?? DEFAULT_PAGE_SIZE)}
            >
              Atualizar
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              Novo Projeto Geral
            </Button>
          </Space>
        </header>
        <Table
          columns={columns}
          dataSource={projetos}
          rowKey="id"
          loading={loading}
          onChange={handleTableChange}
          pagination={pagination}
          scroll={{ x: 900 }}
        />
      </Card>

      <Modal
        title={editing ? 'Editar Projeto Geral' : 'Novo Projeto Geral'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={() => form.submit()}
        okText="Salvar"
        cancelText="Cancelar"
        width={600}
      >
        <Form form={form} layout="vertical" autoComplete="off" onFinish={handleSave}>
          <Form.Item name="nome" label="Nome" rules={[{ required: true, message: 'Nome é obrigatório' }]}>
            <Input placeholder="Ex: PROJETO AMMA" />
          </Form.Item>
          <Form.Item name="tipo_calculo_codigos" label="Cálculo de códigos" initialValue="por_professor">
            <Select options={TIPO_CALCULO_OPTIONS} />
          </Form.Item>
          <Form.Item name="divisor_aluno" label="Divisor (por aluno)" initialValue={20}>
            <InputNumber min={1} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="multiplicador_professor" label="Multiplicador (por professor)" initialValue={1.1}>
            <InputNumber min={0} step={0.1} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="usa_avaliar" valuePropName="checked" initialValue={false}>
            <Checkbox>Usa AVALIAR</Checkbox>
          </Form.Item>
          <Form.Item name="ativo" valuePropName="checked" initialValue={true}>
            <Checkbox>Projeto ativo</Checkbox>
          </Form.Item>
          <Form.Item name="descricao" label="Descrição">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </section>
  );
}
