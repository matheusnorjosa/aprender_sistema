/**
 * Admin DAT - Gerencias
 *
 * CRUD de gerencias organizacionais com setor e status ativo.
 */

import { useState, useEffect, type JSX } from 'react';
import { Table, Button, Input, Space, Tag, Typography, Card, message, Modal, Form, Checkbox, Select } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import type { TablePaginationConfig } from 'antd/es/table';
import { ReloadOutlined, EditOutlined, PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import { Link } from 'react-router';
import { listGerencias, createGerencia, updateGerencia, deleteGerencia, getRBACMeta } from '../../api/adminDAT';
import type { GerenciaRecord, GerenciaPayload } from '../../api/adminDAT';
import { DEFAULT_PAGE_SIZE } from '../../constants';

const { Title, Text } = Typography;
const { Search } = Input;

/**
 * Gerencia form values interface
 */
interface GerenciaFormValues {
  nome: string;
  nome_setor: string;
  setor_canonico?: string;
  descricao: string;
  ativo: boolean;
}

export default function GerenciasPage(): JSX.Element {
  const [gerencias, setGerencias] = useState<GerenciaRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [modalVisible, setModalVisible] = useState(false);
  const [editingGerencia, setEditingGerencia] = useState<GerenciaRecord | null>(null);
  const [pagination, setPagination] = useState<TablePaginationConfig>({
    current: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    total: 0,
  });
  // Vocabulário setor-de-produto (SSOT = SETORES_PRODUTO no backend), buscado do endpoint de
  // options (/rbac/meta/) — Select FECHADO da conferência, sem hardcode (evita drift do vocabulário).
  const [setoresProduto, setSetoresProduto] = useState<string[]>([]);

  const [form] = Form.useForm<GerenciaFormValues>();

  const fetchGerencias = async (
    current = pagination.current || 1,
    pageSize = pagination.pageSize || DEFAULT_PAGE_SIZE,
  ): Promise<void> => {
    setLoading(true);
    try {
      const data = await listGerencias({
        search: searchText,
        ordering: 'nome',
        page: current,
        page_size: pageSize,
      });
      setGerencias(data.results);
      setPagination((prev) => ({
        ...prev,
        current,
        pageSize,
        total: data.count,
      }));
    } catch (error) {
      message.error(`Erro ao carregar gerencias: ${(error as Error).message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchGerencias(1, pagination.pageSize || DEFAULT_PAGE_SIZE);
  }, [searchText]);

  // Carrega o vocabulário de setor-de-produto uma vez (Select fechado da conferência).
  useEffect(() => {
    void (async () => {
      try {
        const meta = await getRBACMeta();
        setSetoresProduto(meta.setores_produto);
      } catch {
        // meta indisponível: o Select fica sem options até um reload; não bloqueia a listagem.
      }
    })();
  }, []);

  const handleTableChange = (newPagination: TablePaginationConfig): void => {
    void fetchGerencias(
      newPagination.current || 1,
      newPagination.pageSize || pagination.pageSize || DEFAULT_PAGE_SIZE,
    );
  };

  const handleCreate = (): void => {
    setEditingGerencia(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (gerencia: GerenciaRecord): void => {
    setEditingGerencia(gerencia);
    form.setFieldsValue({
      nome: gerencia.nome,
      nome_setor: gerencia.nome_setor,
      setor_canonico: gerencia.setor_canonico,
      descricao: gerencia.descricao,
      ativo: gerencia.ativo,
    });
    setModalVisible(true);
  };

  const handleSave = async (values: GerenciaFormValues): Promise<void> => {
    try {
      const payload: GerenciaPayload = {
        nome: values.nome,
        nome_setor: values.nome_setor,
        descricao: values.descricao,
        ativo: values.ativo,
        // setor_canonico é opcional (CharField allow_blank); envia string vazia se limpo.
        setor_canonico: values.setor_canonico ?? '',
      };
      if (editingGerencia) {
        await updateGerencia(editingGerencia.id, payload);
        message.success('Gerencia atualizada com sucesso');
      } else {
        await createGerencia(payload);
        message.success('Gerencia criada com sucesso');
      }
      setModalVisible(false);
      form.resetFields();
      void fetchGerencias(pagination.current || 1, pagination.pageSize || DEFAULT_PAGE_SIZE);
    } catch (error) {
      message.error(`Erro: ${(error as Error).message}`);
    }
  };

  const handleDelete = (gerencia: GerenciaRecord): void => {
    Modal.confirm({
      title: 'Confirmar exclusao',
      content: `Tem certeza que deseja excluir a gerencia "${gerencia.nome}"?`,
      okText: 'Sim, excluir',
      okType: 'danger',
      cancelText: 'Cancelar',
      onOk: async () => {
        try {
          await deleteGerencia(gerencia.id);
          message.success('Gerencia excluida com sucesso');
          void fetchGerencias(pagination.current || 1, pagination.pageSize || DEFAULT_PAGE_SIZE);
        } catch (error) {
          message.error(`Erro ao excluir: ${(error as Error).message}`);
        }
      },
    });
  };

  const columns: ColumnsType<GerenciaRecord> = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 60 },
    { title: 'Nome', dataIndex: 'nome', key: 'nome', width: 200 },
    { title: 'Nome Setor', dataIndex: 'nome_setor', key: 'nome_setor', width: 150 },
    {
      title: 'Setor canônico',
      dataIndex: 'setor_canonico',
      key: 'setor_canonico',
      width: 170,
      render: (v: string) => (v ? <Tag color="geekblue">{v}</Tag> : <Tag>não definido</Tag>),
    },
    {
      // Sinal de qualidade do de-para v15 (read-only) — ajuda a priorizar a conferência de
      // baixa confiança. Valor exibido cru (vocabulário definido pelo importer, RELAY 50).
      title: 'Confiança',
      dataIndex: 'setor_canonico_confianca',
      key: 'setor_canonico_confianca',
      width: 130,
      // Realça baixa qualidade p/ priorizar a conferência: `na` (não-aplicável, prioridade
      // máxima) vermelho; `media` laranja; `alta` verde/neutro. Vocabulário do de-para v15.
      render: (v: string) => {
        if (!v) return <Text type="secondary">—</Text>;
        const color = v === 'na' ? 'red' : v === 'media' ? 'orange' : 'green';
        return <Tag color={color}>{v}</Tag>;
      },
      // Filtro client-side (a lista de gerências cabe em poucas páginas) p/ isolar baixa confiança.
      filters: [
        { text: 'na (conferir!)', value: 'na' },
        { text: 'media', value: 'media' },
        { text: 'alta', value: 'alta' },
      ],
      onFilter: (value, record) => record.setor_canonico_confianca === value,
    },
    { title: 'Gerente', dataIndex: 'gerente_nome', key: 'gerente_nome', width: 150 },
    {
      title: 'Projetos',
      dataIndex: 'projetos_count',
      key: 'projetos_count',
      width: 80,
      render: (count: number) => <Tag color="blue">{count}</Tag>,
    },
    {
      title: 'Ativo',
      dataIndex: 'ativo',
      key: 'ativo',
      width: 80,
      render: (ativo: boolean) => <Tag color={ativo ? 'green' : 'red'}>{ativo ? 'Sim' : 'Nao'}</Tag>,
    },
    {
      title: 'Acoes',
      key: 'acoes',
      width: 150,
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
    <section className="p-6 bg-gray-100" style={{ minHeight: 'calc(100vh - 64px)' }} aria-labelledby="gerencias-title">
      <nav className="mb-4" aria-label="Navegacao">
        <Link to="/dat/admin">&larr; Voltar para Admin DAT</Link>
      </nav>

      <Card>
        <header className="flex justify-between items-center mb-4">
          <Title level={3} className="m-0" id="gerencias-title">
            Gerencias ({pagination.total || 0})
          </Title>
          <Space>
            <Search
              placeholder="Buscar por nome ou setor..."
              allowClear
              style={{ width: '100%', maxWidth: 250 }}
              onSearch={setSearchText}
              onChange={(e) => !e.target.value && setSearchText('')}
            />
            <Button
              icon={<ReloadOutlined />}
              onClick={() => fetchGerencias(pagination.current || 1, pagination.pageSize || DEFAULT_PAGE_SIZE)}
              loading={loading}
            >
              Atualizar
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              Nova Gerencia
            </Button>
          </Space>
        </header>

        <Table
          columns={columns}
          dataSource={gerencias}
          rowKey="id"
          loading={loading}
          onChange={handleTableChange}
          pagination={{
            ...pagination,
            showSizeChanger: true,
            pageSizeOptions: ['15', '30', '50', '100'],
            showTotal: (total) => `Total: ${total}`,
          }}
          scroll={{ x: 900 }}
        />
      </Card>

      {/* Modal Criar/Editar Gerencia */}
      <Modal
        title={editingGerencia ? 'Editar Gerencia' : 'Nova Gerencia'}
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
          autoComplete="off"
          onFinish={handleSave}
        >
          <Form.Item
            name="nome"
            label="Nome da Gerencia"
            rules={[{ required: true, message: 'Nome e obrigatorio' }]}
          >
            <Input placeholder="Ex: Gerencia de Projetos" />
          </Form.Item>

          <Form.Item
            name="nome_setor"
            label="Nome do Setor"
            rules={[{ required: true, message: 'Nome do setor e obrigatorio' }]}
          >
            <Input placeholder="Ex: Superintendencia" />
          </Form.Item>

          <Form.Item
            name="setor_canonico"
            label="Setor canônico (vocabulário de setor-de-produto)"
          >
            <Select
              allowClear
              showSearch
              placeholder="Selecione o setor canônico..."
              options={setoresProduto.map((s) => ({ label: s, value: s }))}
            />
          </Form.Item>

          <Form.Item
            name="descricao"
            label="Descricao"
          >
            <Input.TextArea rows={3} placeholder="Descricao da gerencia" />
          </Form.Item>

          <Form.Item name="ativo" valuePropName="checked" initialValue={true}>
            <Checkbox>Gerencia ativa</Checkbox>
          </Form.Item>
        </Form>
      </Modal>
    </section>
  );
}
