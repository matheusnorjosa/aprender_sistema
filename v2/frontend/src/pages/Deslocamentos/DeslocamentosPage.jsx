/**
 * Deslocamentos Page - Issue #188
 *
 * CRUD interface for managing travel records between municipalities.
 *
 * Features:
 * - List with filters (Usuario, Date Range, Origem/Destino)
 * - Create/Edit via modal
 * - Delete with confirmation
 * - Pagination (50 per page)
 * - RBAC: Only Controle/Coordenador can access
 *
 * API:
 * - GET /api/deslocamentos/ (list with filters)
 * - POST /api/deslocamentos/ (create)
 * - PUT /api/deslocamentos/{id}/ (update)
 * - DELETE /api/deslocamentos/{id}/ (delete)
 */

import { useState, useEffect, useCallback } from 'react';
import {
  Table,
  Button,
  Modal,
  Form,
  Input,
  Select,
  DatePicker,
  message,
  Space,
  Popconfirm,
  Row,
  Col,
  Card,
  Typography,
  Tooltip,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SearchOutlined,
  CarOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { getMe } from '../../api/availability';
import logger from '../../utils/logger';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;
const { TextArea } = Input;

// API Base URL
const API_BASE = '/api';

/**
 * Fetch deslocamentos with filters
 */
async function fetchDeslocamentos(filters = {}) {
  const params = new URLSearchParams();
  if (filters.usuario_id) params.append('usuario_id', filters.usuario_id);
  if (filters.data_inicio) params.append('data_inicio', filters.data_inicio);
  if (filters.data_fim) params.append('data_fim', filters.data_fim);
  if (filters.origem) params.append('origem', filters.origem);
  if (filters.destino) params.append('destino', filters.destino);
  if (filters.page) params.append('page', filters.page);

  const response = await fetch(`${API_BASE}/deslocamentos/?${params.toString()}`, {
    credentials: 'include',
  });

  if (!response.ok) {
    throw new Error(`Erro ao buscar deslocamentos: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Fetch usuarios for select
 */
async function fetchUsuarios() {
  const response = await fetch(`${API_BASE}/options/usuarios/`, {
    credentials: 'include',
  });

  if (!response.ok) {
    throw new Error('Erro ao buscar usuários');
  }

  return response.json();
}

/**
 * Create deslocamento
 */
async function createDeslocamento(data) {
  const response = await fetch(`${API_BASE}/deslocamentos/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json();
    throw error;
  }

  return response.json();
}

/**
 * Update deslocamento
 */
async function updateDeslocamento(id, data) {
  const response = await fetch(`${API_BASE}/deslocamentos/${id}/`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json();
    throw error;
  }

  return response.json();
}

/**
 * Delete deslocamento
 */
async function deleteDeslocamento(id) {
  const response = await fetch(`${API_BASE}/deslocamentos/${id}/`, {
    method: 'DELETE',
    credentials: 'include',
  });

  if (!response.ok) {
    throw new Error('Erro ao deletar deslocamento');
  }
}

export default function DeslocamentosPage() {
  const [canAccess, setCanAccess] = useState(false);
  const [loading, setLoading] = useState(true);
  const [deslocamentos, setDeslocamentos] = useState([]);
  const [usuarios, setUsuarios] = useState([]);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 50, total: 0 });
  const [filters, setFilters] = useState({});
  const [modalVisible, setModalVisible] = useState(false);
  const [modalMode, setModalMode] = useState('create'); // 'create' or 'edit'
  const [currentRecord, setCurrentRecord] = useState(null);
  const [form] = Form.useForm();

  // Load user and check permissions
  useEffect(() => {
    async function loadUser() {
      try {
        const userData = await getMe();

        // Check RBAC: Controle, Coordenador, or DAT
        const canControle = userData.groups?.includes('Controle');
        const canCoordenador = userData.groups?.includes('Coordenador');
        const canDAT = userData.groups?.includes('DAT');
        const canSuper = userData.is_superuser || userData.is_superintendencia;

        setCanAccess(canControle || canCoordenador || canDAT || canSuper);
      } catch (error) {
        logger.error('Erro ao carregar usuário:', error);
        setCanAccess(false);
      } finally {
        setLoading(false);
      }
    }

    loadUser();
  }, []);

  // Load deslocamentos
  const loadDeslocamentos = useCallback(async (page = 1) => {
    setLoading(true);
    try {
      const data = await fetchDeslocamentos({ ...filters, page });
      setDeslocamentos(data.results || []);
      setPagination({
        current: page,
        pageSize: 50,
        total: data.count || 0,
      });
    } catch (error) {
      message.error(error.message);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  // Load usuarios for select
  const loadUsuarios = useCallback(async () => {
    try {
      const data = await fetchUsuarios();
      setUsuarios(data);
    } catch (error) {
      logger.error('Erro ao carregar usuários:', error);
    }
  }, []);

  useEffect(() => {
    if (canAccess) {
      loadDeslocamentos();
      loadUsuarios();
    }
  }, [canAccess, filters, loadDeslocamentos, loadUsuarios]);

  // Handle table change (pagination)
  const handleTableChange = (paginationConfig) => {
    loadDeslocamentos(paginationConfig.current);
  };

  // Handle filter change
  const handleFilterChange = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  // Handle date range change
  const handleDateRangeChange = (dates) => {
    if (dates && dates.length === 2) {
      setFilters((prev) => ({
        ...prev,
        data_inicio: dates[0].format('YYYY-MM-DD'),
        data_fim: dates[1].format('YYYY-MM-DD'),
      }));
    } else {
      setFilters((prev) => {
        const { data_inicio: _data_inicio, data_fim: _data_fim, ...rest } = prev;
        return rest;
      });
    }
  };

  // Open modal for create
  const handleCreate = () => {
    setModalMode('create');
    setCurrentRecord(null);
    form.resetFields();
    setModalVisible(true);
  };

  // Open modal for edit
  const handleEdit = (record) => {
    setModalMode('edit');
    setCurrentRecord(record);
    form.setFieldsValue({
      usuario: record.usuario,
      origem: record.origem,
      destino: record.destino,
      start_date: dayjs(record.start_date),
      end_date: dayjs(record.end_date),
      observacao: record.observacao || '',
    });
    setModalVisible(true);
  };

  // Handle modal submit
  const handleModalSubmit = async () => {
    try {
      const values = await form.validateFields();

      // Format data
      const data = {
        usuario: values.usuario,
        origem: values.origem,
        destino: values.destino,
        start_date: values.start_date.format('YYYY-MM-DD'),
        end_date: values.end_date.format('YYYY-MM-DD'),
        observacao: values.observacao || '',
      };

      if (modalMode === 'create') {
        await createDeslocamento(data);
        message.success('Deslocamento criado com sucesso!');
      } else {
        await updateDeslocamento(currentRecord.id, data);
        message.success('Deslocamento atualizado com sucesso!');
      }

      setModalVisible(false);
      form.resetFields();
      loadDeslocamentos(pagination.current);
    } catch (error) {
      if (error.end_date) {
        message.error(error.end_date[0]);
      } else if (error.destino) {
        message.error(error.destino[0]);
      } else {
        message.error('Erro ao salvar deslocamento');
      }
    }
  };

  // Handle delete
  const handleDelete = async (id) => {
    try {
      await deleteDeslocamento(id);
      message.success('Deslocamento deletado com sucesso!');
      loadDeslocamentos(pagination.current);
    } catch {
      message.error('Erro ao deletar deslocamento');
    }
  };

  // Columns for table
  const columns = [
    {
      title: 'Formador',
      dataIndex: 'usuario_nome',
      key: 'usuario_nome',
      width: 200,
    },
    {
      title: 'Origem',
      dataIndex: 'origem',
      key: 'origem',
      width: 150,
    },
    {
      title: 'Destino',
      dataIndex: 'destino',
      key: 'destino',
      width: 150,
    },
    {
      title: 'Data Início',
      dataIndex: 'start_date',
      key: 'start_date',
      width: 120,
      render: (date) => dayjs(date).format('DD/MM/YYYY'),
    },
    {
      title: 'Data Fim',
      dataIndex: 'end_date',
      key: 'end_date',
      width: 120,
      render: (date) => dayjs(date).format('DD/MM/YYYY'),
    },
    {
      title: 'Observação',
      dataIndex: 'observacao',
      key: 'observacao',
      ellipsis: true,
      render: (text) => (
        <Tooltip title={text}>
          <span>{text ? text.substring(0, 50) : '-'}</span>
        </Tooltip>
      ),
    },
    {
      title: 'Ações',
      key: 'actions',
      fixed: 'right',
      width: 120,
      render: (_, record) => (
        <Space size="small">
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
            size="small"
          />
          <Popconfirm
            title="Tem certeza que deseja deletar?"
            onConfirm={() => handleDelete(record.id)}
            okText="Sim"
            cancelText="Não"
          >
            <Button type="link" danger icon={<DeleteOutlined />} size="small" />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // Permission check
  if (loading) {
    return <div className="p-6">Carregando...</div>;
  }

  if (!canAccess) {
    return (
      <div className="p-6">
        <Card>
          <Title level={3}>Sem permissão</Title>
          <Text>Você não tem permissão para acessar esta página.</Text>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-4 bg-gray-50 min-h-screen">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <Title level={2}>
            <CarOutlined /> Deslocamentos
          </Title>
          <Text type="secondary">Gestão de deslocamentos entre municípios</Text>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
          Novo Deslocamento
        </Button>
      </div>

      {/* Filters */}
      <Card title="Filtros" size="small">
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} md={6}>
            <Select
              placeholder="Selecione um formador"
              allowClear
              showSearch
              optionFilterProp="children"
              style={{ width: '100%' }}
              onChange={(value) => handleFilterChange('usuario_id', value)}
            >
              {usuarios.map((u) => (
                <Select.Option key={u.id} value={u.id}>
                  {u.first_name} {u.last_name}
                </Select.Option>
              ))}
            </Select>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <RangePicker
              placeholder={['Data Início', 'Data Fim']}
              format="DD/MM/YYYY"
              style={{ width: '100%' }}
              onChange={handleDateRangeChange}
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Input
              placeholder="Origem"
              prefix={<SearchOutlined />}
              onChange={(e) => handleFilterChange('origem', e.target.value)}
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Input
              placeholder="Destino"
              prefix={<SearchOutlined />}
              onChange={(e) => handleFilterChange('destino', e.target.value)}
            />
          </Col>
        </Row>
      </Card>

      {/* Table */}
      <Card>
        <Table
          columns={columns}
          dataSource={deslocamentos}
          rowKey="id"
          loading={loading}
          pagination={pagination}
          onChange={handleTableChange}
          scroll={{ x: 1000 }}
        />
      </Card>

      {/* Modal */}
      <Modal
        title={modalMode === 'create' ? 'Novo Deslocamento' : 'Editar Deslocamento'}
        open={modalVisible}
        onOk={handleModalSubmit}
        onCancel={() => {
          setModalVisible(false);
          form.resetFields();
        }}
        okText="Salvar"
        cancelText="Cancelar"
        width={600}
      >
        <Form form={form} layout="vertical" className="mt-4">
          <Form.Item
            name="usuario"
            label="Formador"
            rules={[{ required: true, message: 'Selecione um formador' }]}
          >
            <Select
              placeholder="Selecione um formador"
              showSearch
              optionFilterProp="children"
            >
              {usuarios.map((u) => (
                <Select.Option key={u.id} value={u.id}>
                  {u.first_name} {u.last_name}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="origem"
                label="Origem"
                rules={[
                  { required: true, message: 'Informe a origem' },
                  { max: 200, message: 'Máximo 200 caracteres' },
                ]}
              >
                <Input placeholder="Ex: Fortaleza" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="destino"
                label="Destino"
                rules={[
                  { required: true, message: 'Informe o destino' },
                  { max: 200, message: 'Máximo 200 caracteres' },
                ]}
              >
                <Input placeholder="Ex: Sobral" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="start_date"
                label="Data Início"
                rules={[{ required: true, message: 'Selecione a data de início' }]}
              >
                <DatePicker format="DD/MM/YYYY" style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="end_date"
                label="Data Fim"
                rules={[{ required: true, message: 'Selecione a data de fim' }]}
              >
                <DatePicker format="DD/MM/YYYY" style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="observacao"
            label="Observação"
            rules={[{ max: 500, message: 'Máximo 500 caracteres' }]}
          >
            <TextArea rows={3} placeholder="Observações sobre o deslocamento" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
