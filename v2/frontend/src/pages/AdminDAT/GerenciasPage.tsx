/**
 * Admin DAT - Gerencias
 *
 * CRUD de gerencias organizacionais com setor e status ativo.
 */

import { useState, useEffect } from 'react';
import { Table, Button, Input, Space, Tag, Typography, Card, message, Modal, Form, Checkbox } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import type { TablePaginationConfig } from 'antd/es/table';
import { ReloadOutlined, EditOutlined, PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import { Link } from 'react-router-dom';
import { listGerencias, createGerencia, updateGerencia, deleteGerencia } from '../../api/adminDAT';
import type { GerenciaRecord, GerenciaPayload } from '../../api/adminDAT';
import { DEFAULT_PAGE_SIZE } from '../../constants';

const { Title } = Typography;
const { Search } = Input;

/**
 * Gerencia form values interface
 */
interface GerenciaFormValues {
  nome: string;
  nome_setor: string;
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
      setGerencias(data.results as unknown as GerenciaRecord[]);
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
    fetchGerencias(1, pagination.pageSize || DEFAULT_PAGE_SIZE);
  }, [searchText]);

  const handleTableChange = (newPagination: TablePaginationConfig): void => {
    fetchGerencias(
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
      fetchGerencias(pagination.current || 1, pagination.pageSize || DEFAULT_PAGE_SIZE);
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
          fetchGerencias(pagination.current || 1, pagination.pageSize || DEFAULT_PAGE_SIZE);
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
