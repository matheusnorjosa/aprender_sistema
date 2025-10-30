/**
 * Admin DAT - Municípios
 *
 * CRUD de municípios com indicadores (UF, ativo).
 * Fase 1 Iteração 2 - Plano DAT/GCal 2025-10-29
 */

import { useState, useEffect } from 'react';
import { Table, Button, Input, Space, Tag, Typography, Card, message, Select, Modal, Form, Checkbox } from 'antd';
import { EnvironmentOutlined, ReloadOutlined, EditOutlined, PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import { Link } from 'react-router-dom';
import { listMunicipios, createMunicipio, updateMunicipio, deleteMunicipio } from '../../api/adminDAT';

const { Title } = Typography;
const { Search } = Input;

export default function MunicipiosPage() {
  const [municipios, setMunicipios] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [ufFilter, setUfFilter] = useState(undefined);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingMunicipio, setEditingMunicipio] = useState(null);

  const [form] = Form.useForm();

  const fetchMunicipios = async () => {
    setLoading(true);
    try {
      const data = await listMunicipios({
        search: searchText,
        uf: ufFilter,
        ordering: 'nome',
      });
      setMunicipios(data.results || data);
    } catch (error) {
      message.error(`Erro ao carregar municípios: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMunicipios();
  }, [searchText, ufFilter]);

  const handleCreate = () => {
    setEditingMunicipio(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (municipio) => {
    setEditingMunicipio(municipio);
    form.setFieldsValue({
      nome: municipio.nome,
      uf: municipio.uf,
      ibge_code: municipio.ibge_code,
      ativo: municipio.ativo,
    });
    setModalVisible(true);
  };

  const handleSave = async (values) => {
    try {
      if (editingMunicipio) {
        await updateMunicipio(editingMunicipio.id, values);
        message.success('Município atualizado com sucesso');
      } else {
        await createMunicipio(values);
        message.success('Município criado com sucesso');
      }
      setModalVisible(false);
      form.resetFields();
      fetchMunicipios();
    } catch (error) {
      message.error(`Erro: ${error.message}`);
    }
  };

  const handleDelete = (municipio) => {
    Modal.confirm({
      title: 'Confirmar exclusão',
      content: `Tem certeza que deseja excluir o município "${municipio.nome}"?`,
      okText: 'Sim, excluir',
      okType: 'danger',
      cancelText: 'Cancelar',
      onOk: async () => {
        try {
          await deleteMunicipio(municipio.id);
          message.success('Município excluído com sucesso');
          fetchMunicipios();
        } catch (error) {
          message.error(`Erro ao excluir: ${error.message}`);
        }
      },
    });
  };

  const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 60 },
    { title: 'Nome', dataIndex: 'nome', key: 'nome', width: 300 },
    { title: 'UF', dataIndex: 'uf', key: 'uf', width: 80, render: (uf) => <Tag color="blue">{uf}</Tag> },
    { title: 'IBGE', dataIndex: 'ibge_code', key: 'ibge_code', width: 120 },
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
            Municípios ({municipios.length})
          </Title>
          <Space>
            <Search
              placeholder="Buscar por nome ou IBGE"
              allowClear
              style={{ width: 250 }}
              onSearch={setSearchText}
              onChange={(e) => !e.target.value && setSearchText('')}
            />
            <Select
              placeholder="Filtrar por UF"
              allowClear
              style={{ width: 100 }}
              onChange={setUfFilter}
              options={['BA', 'CE', 'PE', 'RN', 'SE', 'AL', 'PB', 'PI', 'MA'].map((uf) => ({ label: uf, value: uf }))}
            />
            <Button icon={<ReloadOutlined />} onClick={fetchMunicipios} loading={loading}>
              Atualizar
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              Novo Município
            </Button>
          </Space>
        </div>

        <Table
          columns={columns}
          dataSource={municipios}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 15, showTotal: (total) => `Total: ${total}` }}
          scroll={{ x: 1000 }}
        />
      </Card>

      {/* Modal Criar/Editar Município */}
      <Modal
        title={editingMunicipio ? 'Editar Município' : 'Novo Município'}
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
            label="Nome do Município"
            rules={[{ required: true, message: 'Nome é obrigatório' }]}
          >
            <Input placeholder="Ex: Salvador" />
          </Form.Item>

          <Form.Item
            name="uf"
            label="UF"
            rules={[{ required: true, message: 'UF é obrigatória' }]}
          >
            <Select
              placeholder="Selecione a UF"
              options={[
                { label: 'BA', value: 'BA' },
                { label: 'CE', value: 'CE' },
                { label: 'PE', value: 'PE' },
                { label: 'RN', value: 'RN' },
                { label: 'SE', value: 'SE' },
                { label: 'AL', value: 'AL' },
                { label: 'PB', value: 'PB' },
                { label: 'PI', value: 'PI' },
                { label: 'MA', value: 'MA' },
              ]}
            />
          </Form.Item>

          <Form.Item
            name="ibge_code"
            label="Código IBGE"
            rules={[{ required: true, message: 'Código IBGE é obrigatório' }]}
          >
            <Input placeholder="Ex: 2927408" maxLength={7} />
          </Form.Item>

          <Form.Item name="ativo" valuePropName="checked" initialValue={true}>
            <Checkbox>Município ativo</Checkbox>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
