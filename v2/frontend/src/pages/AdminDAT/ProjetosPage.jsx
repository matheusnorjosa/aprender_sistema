/**
 * Admin DAT - Projetos
 *
 * CRUD de projetos com fluxo (SUPER/NAO_SUPER) e status ativo.
 * Fase 1 Iteração 2 - Plano DAT/GCal 2025-10-29
 */

import { useState, useEffect } from 'react';
import { Table, Button, Input, Space, Tag, Typography, Card, message, Modal, Form, Radio, Checkbox } from 'antd';
import { ProjectOutlined, ReloadOutlined, EditOutlined, PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import { Link } from 'react-router-dom';
import { listProjetos, createProjeto, updateProjeto, deleteProjeto } from '../../api/adminDAT';

const { Title } = Typography;
const { Search } = Input;

export default function ProjetosPage() {
  const [projetos, setProjetos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [modalVisible, setModalVisible] = useState(false);
  const [editingProjeto, setEditingProjeto] = useState(null);

  const [form] = Form.useForm();

  const fetchProjetos = async () => {
    setLoading(true);
    try {
      const data = await listProjetos({
        search: searchText,
        ordering: 'nome',
      });
      setProjetos(data.results || data);
    } catch (error) {
      message.error(`Erro ao carregar projetos: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjetos();
  }, [searchText]);

  const handleCreate = () => {
    setEditingProjeto(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (projeto) => {
    setEditingProjeto(projeto);
    form.setFieldsValue({
      nome: projeto.nome,
      codigo: projeto.codigo,
      fluxo: projeto.fluxo,
      ativo: projeto.ativo,
    });
    setModalVisible(true);
  };

  const handleSave = async (values) => {
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
      message.error(`Erro: ${error.message}`);
    }
  };

  const handleDelete = (projeto) => {
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
          message.error(`Erro ao excluir: ${error.message}`);
        }
      },
    });
  };

  const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 60 },
    { title: 'Nome', dataIndex: 'nome', key: 'nome', width: 300 },
    { title: 'Código', dataIndex: 'codigo', key: 'codigo', width: 120 },
    {
      title: 'Fluxo',
      dataIndex: 'fluxo',
      key: 'fluxo',
      width: 150,
      render: (fluxo) => (
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
      render: (ativo) => <Tag color={ativo ? 'green' : 'red'}>{ativo ? 'Sim' : 'Não'}</Tag>,
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
    <div style={{ padding: '24px', background: '#f0f2f5', minHeight: 'calc(100vh - 64px)' }}>
      <div style={{ marginBottom: '16px' }}>
        <Link to="/admin-dat">← Voltar para Admin DAT</Link>
      </div>

      <Card>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <Title level={3} style={{ margin: 0 }}>
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
        </div>

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
    </div>
  );
}
