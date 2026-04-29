/**
 * Admin DAT - Produtos
 *
 * CRUD de produtos por projeto com codigo e status ativo.
 */

import { useState, useEffect } from 'react';
import { Table, Button, Input, Space, Tag, Typography, Card, message, Modal, Form, Checkbox, Select } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import type { TablePaginationConfig } from 'antd/es/table';
import { ReloadOutlined, EditOutlined, PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import { Link } from 'react-router-dom';
import { listProdutos, createProduto, updateProduto, deleteProduto, listProjetos } from '../../api/adminDAT';
import type { ProdutoRecord, ProdutoPayload } from '../../api/adminDAT';
import { DEFAULT_PAGE_SIZE } from '../../constants';
import type { ID, Projeto } from '../../types';

const { Title } = Typography;
const { Search } = Input;

/**
 * Produto form values interface
 */
interface ProdutoFormValues {
  codigo: string;
  nome: string;
  descricao: string;
  projeto: ID;
  ativo: boolean;
}

export default function ProdutosPage(): JSX.Element {
  const [produtos, setProdutos] = useState<ProdutoRecord[]>([]);
  const [projetos, setProjetos] = useState<Projeto[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [modalVisible, setModalVisible] = useState(false);
  const [editingProduto, setEditingProduto] = useState<ProdutoRecord | null>(null);
  const [pagination, setPagination] = useState<TablePaginationConfig>({
    current: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    total: 0,
  });

  const [form] = Form.useForm<ProdutoFormValues>();

  const fetchProdutos = async (
    current = pagination.current || 1,
    pageSize = pagination.pageSize || DEFAULT_PAGE_SIZE,
  ): Promise<void> => {
    setLoading(true);
    try {
      const data = await listProdutos({
        search: searchText,
        ordering: 'nome',
        page: current,
        page_size: pageSize,
      });
      setProdutos(data.results as unknown as ProdutoRecord[]);
      setPagination((prev) => ({
        ...prev,
        current,
        pageSize,
        total: data.count,
      }));
    } catch (error) {
      message.error(`Erro ao carregar produtos: ${(error as Error).message}`);
    } finally {
      setLoading(false);
    }
  };

  const fetchProjetos = async (): Promise<void> => {
    try {
      const data = await listProjetos({ page_size: 200 });
      setProjetos(data.results);
    } catch (error) {
      message.error(`Erro ao carregar projetos: ${(error as Error).message}`);
    }
  };

  useEffect(() => {
    fetchProdutos(1, pagination.pageSize || DEFAULT_PAGE_SIZE);
  }, [searchText]);

  const handleTableChange = (newPagination: TablePaginationConfig): void => {
    fetchProdutos(
      newPagination.current || 1,
      newPagination.pageSize || pagination.pageSize || DEFAULT_PAGE_SIZE,
    );
  };

  useEffect(() => {
    fetchProjetos();
  }, []);

  const handleCreate = (): void => {
    setEditingProduto(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (produto: ProdutoRecord): void => {
    setEditingProduto(produto);
    form.setFieldsValue({
      codigo: produto.codigo,
      nome: produto.nome,
      descricao: produto.descricao,
      projeto: produto.projeto,
      ativo: produto.ativo,
    });
    setModalVisible(true);
  };

  const handleSave = async (values: ProdutoFormValues): Promise<void> => {
    try {
      const payload: ProdutoPayload = {
        codigo: values.codigo,
        nome: values.nome,
        descricao: values.descricao,
        projeto: values.projeto,
        ativo: values.ativo,
      };
      if (editingProduto) {
        await updateProduto(editingProduto.id, payload);
        message.success('Produto atualizado com sucesso');
      } else {
        await createProduto(payload);
        message.success('Produto criado com sucesso');
      }
      setModalVisible(false);
      form.resetFields();
      fetchProdutos(pagination.current || 1, pagination.pageSize || DEFAULT_PAGE_SIZE);
    } catch (error) {
      message.error(`Erro: ${(error as Error).message}`);
    }
  };

  const handleDelete = (produto: ProdutoRecord): void => {
    Modal.confirm({
      title: 'Confirmar exclusao',
      content: `Tem certeza que deseja excluir o produto "${produto.nome}"?`,
      okText: 'Sim, excluir',
      okType: 'danger',
      cancelText: 'Cancelar',
      onOk: async () => {
        try {
          await deleteProduto(produto.id);
          message.success('Produto excluido com sucesso');
          fetchProdutos(pagination.current || 1, pagination.pageSize || DEFAULT_PAGE_SIZE);
        } catch (error) {
          message.error(`Erro ao excluir: ${(error as Error).message}`);
        }
      },
    });
  };

  const columns: ColumnsType<ProdutoRecord> = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 60 },
    { title: 'Codigo', dataIndex: 'codigo', key: 'codigo', width: 120 },
    { title: 'Nome', dataIndex: 'nome', key: 'nome', width: 250 },
    { title: 'Projeto', dataIndex: 'projeto_nome', key: 'projeto_nome', width: 150 },
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
    <section className="p-6 bg-gray-100" style={{ minHeight: 'calc(100vh - 64px)' }} aria-labelledby="produtos-title">
      <nav className="mb-4" aria-label="Navegacao">
        <Link to="/dat/admin">&larr; Voltar para Admin DAT</Link>
      </nav>

      <Card>
        <header className="flex justify-between items-center mb-4">
          <Title level={3} className="m-0" id="produtos-title">
            Produtos ({pagination.total || 0})
          </Title>
          <Space>
            <Search
              placeholder="Buscar por nome ou codigo..."
              allowClear
              style={{ width: '100%', maxWidth: 250 }}
              onSearch={setSearchText}
              onChange={(e) => !e.target.value && setSearchText('')}
            />
            <Button
              icon={<ReloadOutlined />}
              onClick={() => fetchProdutos(pagination.current || 1, pagination.pageSize || DEFAULT_PAGE_SIZE)}
              loading={loading}
            >
              Atualizar
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              Novo Produto
            </Button>
          </Space>
        </header>

        <Table
          columns={columns}
          dataSource={produtos}
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

      {/* Modal Criar/Editar Produto */}
      <Modal
        title={editingProduto ? 'Editar Produto' : 'Novo Produto'}
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
            name="codigo"
            label="Codigo"
            rules={[{ required: true, message: 'Codigo e obrigatorio' }]}
          >
            <Input placeholder="Ex: PROD-001" />
          </Form.Item>

          <Form.Item
            name="nome"
            label="Nome do Produto"
            rules={[{ required: true, message: 'Nome e obrigatorio' }]}
          >
            <Input placeholder="Ex: Material Didatico" />
          </Form.Item>

          <Form.Item
            name="descricao"
            label="Descricao"
          >
            <Input.TextArea rows={3} placeholder="Descricao do produto" />
          </Form.Item>

          <Form.Item
            name="projeto"
            label="Projeto"
            rules={[{ required: true, message: 'Projeto e obrigatorio' }]}
          >
            <Select
              placeholder="Selecione um projeto"
              showSearch
              optionFilterProp="children"
              filterOption={(input, option) =>
                (option?.children as unknown as string)?.toLowerCase().includes(input.toLowerCase()) ?? false
              }
            >
              {projetos.map((p) => (
                <Select.Option key={p.id} value={p.id}>
                  {p.nome}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item name="ativo" valuePropName="checked" initialValue={true}>
            <Checkbox>Produto ativo</Checkbox>
          </Form.Item>
        </Form>
      </Modal>
    </section>
  );
}
