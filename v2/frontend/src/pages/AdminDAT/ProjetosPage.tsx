/**
 * Admin DAT - Projetos
 *
 * CRUD de projetos com fluxo (SUPER/NAO_SUPER) e status ativo.
 * Fase 1 Iteração 2 - Plano DAT/GCal 2025-10-29
 */

import { useState, useEffect } from 'react';
import { Table, Button, Input, Space, Tag, Typography, Card, message, Modal, Form, Radio, Checkbox } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { ReloadOutlined, EditOutlined, PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import { Link } from 'react-router-dom';
import { listProjetos, createProjeto, updateProjeto, deleteProjeto } from '../../api/adminDAT';
import type { ID } from '../../types';

const { Title } = Typography;
const { Search } = Input;

/**
 * Projeto record interface
 */
interface ProjetoRecord {
  id: ID;
  nome: string;
  codigo: string;
  fluxo: 'SUPER' | 'NAO_SUPER';
  ativo: boolean;
}

/**
 * Projeto form values interface
 */
interface ProjetoFormValues {
  nome: string;
  codigo: string;
  fluxo: 'SUPER' | 'NAO_SUPER';
  ativo: boolean;
}

export default function ProjetosPage(): JSX.Element {
  const [projetos, setProjetos] = useState<ProjetoRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [modalVisible, setModalVisible] = useState(false);
  const [editingProjeto, setEditingProjeto] = useState<ProjetoRecord | null>(null);

  const [form] = Form.useForm<ProjetoFormValues>();

  const fetchProjetos = async (): Promise<void> => {
    setLoading(true);
    try {
      const data = await listProjetos({
        search: searchText,
        ordering: 'nome',
      });
      // Note: API returns Projeto with is_active, but component uses ativo field name
      // This is acceptable during migration - will be unified in strict mode phase
      setProjetos(data.results as unknown as ProjetoRecord[]);
    } catch (error) {
      message.error(`Erro ao carregar projetos: ${(error as Error).message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjetos();
  }, [searchText]);

  const handleCreate = (): void => {
    setEditingProjeto(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (projeto: ProjetoRecord): void => {
    setEditingProjeto(projeto);
    form.setFieldsValue({
      nome: projeto.nome,
      codigo: projeto.codigo,
      fluxo: projeto.fluxo,
      ativo: projeto.ativo,
    });
    setModalVisible(true);
  };

  const handleSave = async (values: ProjetoFormValues): Promise<void> => {
    try {
      if (editingProjeto) {
        await updateProjeto(editingProjeto.id, values);
        message.success('Projeto atualizado com sucesso');
      } else {
        await createProjeto(values);
        message.success('Projeto criado com sucesso');
      }
      setModalVisible(false);
      form.resetFields();
      fetchProjetos();
    } catch (error) {
      message.error(`Erro: ${(error as Error).message}`);
    }
  };

  const handleDelete = (projeto: ProjetoRecord): void => {
    Modal.confirm({
      title: 'Confirmar exclusão',
      content: `Tem certeza que deseja excluir o projeto "${projeto.nome}"?`,
      okText: 'Sim, excluir',
      okType: 'danger',
      cancelText: 'Cancelar',
      onOk: async () => {
        try {
          await deleteProjeto(projeto.id);
          message.success('Projeto excluído com sucesso');
          fetchProjetos();
        } catch (error) {
          message.error(`Erro ao excluir: ${(error as Error).message}`);
        }
      },
    });
  };

  const columns: ColumnsType<ProjetoRecord> = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 60 },
    { title: 'Nome', dataIndex: 'nome', key: 'nome', width: 300 },
    { title: 'Código', dataIndex: 'codigo', key: 'codigo', width: 120 },
    {
      title: 'Fluxo',
      dataIndex: 'fluxo',
      key: 'fluxo',
      width: 150,
      render: (fluxo: string) => (
        <Tag color={fluxo === 'SUPER' ? 'gold' : 'blue'}>
          {fluxo === 'SUPER' ? 'SUPER (Manual)' : 'NAO_SUPER (Auto)'}
        </Tag>
      ),
    },
    {
      title: 'Ativo',
      dataIndex: 'ativo',
      key: 'ativo',
      width: 100,
      render: (ativo: boolean) => <Tag color={ativo ? 'green' : 'red'}>{ativo ? 'Sim' : 'Não'}</Tag>,
    },
    {
      title: 'Ações',
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
    <section className="p-6 bg-gray-100" style={{ minHeight: 'calc(100vh - 64px)' }} aria-labelledby="projetos-title">
      <nav className="mb-4" aria-label="Navegação">
        <Link to="/admin-dat">← Voltar para Admin DAT</Link>
      </nav>

      <Card>
        <header className="flex justify-between items-center mb-4">
          <Title level={3} className="m-0" id="projetos-title">
            Projetos ({projetos.length})
          </Title>
          <Space>
            <Search
              placeholder="Buscar por nome ou código"
              allowClear
              style={{ width: 250 }}
              onSearch={setSearchText}
              onChange={(e) => !e.target.value && setSearchText('')}
            />
            <Button icon={<ReloadOutlined />} onClick={fetchProjetos} loading={loading}>
              Atualizar
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              Novo Projeto
            </Button>
          </Space>
        </header>

        <Table
          columns={columns}
          dataSource={projetos}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 15, showTotal: (total) => `Total: ${total}` }}
          scroll={{ x: 900 }}
        />
      </Card>

      {/* Modal Criar/Editar Projeto */}
      <Modal
        title={editingProjeto ? 'Editar Projeto' : 'Novo Projeto'}
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
            name="nome"
            label="Nome do Projeto"
            rules={[{ required: true, message: 'Nome é obrigatório' }]}
          >
            <Input placeholder="Ex: PROJETO AMMA" />
          </Form.Item>

          <Form.Item
            name="codigo"
            label="Código"
            rules={[{ required: true, message: 'Código é obrigatório' }]}
          >
            <Input placeholder="Ex: AMMA" />
          </Form.Item>

          <Form.Item
            name="fluxo"
            label="Fluxo de Aprovação"
            rules={[{ required: true, message: 'Fluxo é obrigatório' }]}
            initialValue="NAO_SUPER"
          >
            <Radio.Group>
              <Radio value="SUPER">SUPER (Aprovação Manual pela Superintendência)</Radio>
              <Radio value="NAO_SUPER">NAO_SUPER (Auto-aprovado)</Radio>
            </Radio.Group>
          </Form.Item>

          <Form.Item name="ativo" valuePropName="checked" initialValue={true}>
            <Checkbox>Projeto ativo</Checkbox>
          </Form.Item>
        </Form>
      </Modal>
    </section>
  );
}
