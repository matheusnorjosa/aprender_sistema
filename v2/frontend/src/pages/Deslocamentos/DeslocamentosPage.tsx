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

import { useState, useEffect, useCallback, ChangeEvent, JSX } from 'react';
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
  Radio,
} from 'antd';
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table';
import type { RadioChangeEvent } from 'antd/es/radio';
import type { Dayjs } from 'dayjs';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SearchOutlined,
  CarOutlined,
  UploadOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { getMe } from '../../api/availability';
import { importDeslocamentos } from '../../api/ops';
import ImportUploader, { ValidationResult, ApplyResult } from '../../components/ImportUploader';
import logger from '../../utils/logger';
import type { ID, CurrentUser } from '../../types';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;
const { TextArea } = Input;

// API Base URL
const API_BASE = '/api';

/** Deslocamento record type */
interface DeslocamentoRecord {
  id: ID;
  usuario: ID;
  usuario_nome: string;
  origem: string;
  destino: string;
  start_date: string;
  end_date: string;
  observacao?: string;
}

/** Usuario option type */
interface UsuarioOptionType {
  id: ID;
  first_name: string;
  last_name: string;
}

/** Filters type */
interface FiltersType {
  usuario_id?: ID;
  data_inicio?: string;
  data_fim?: string;
  origem?: string;
  destino?: string;
  page?: number;
}

/** Form values type */
interface FormValuesType {
  usuario: ID;
  origem: string;
  destino: string;
  start_date: Dayjs;
  end_date: Dayjs;
  observacao?: string;
}

/** API error type */
interface ApiErrorType {
  end_date?: string[];
  destino?: string[];
  [key: string]: string[] | undefined;
}

/** View mode type */
type ViewMode = 'lista' | 'importar';

/**
 * Converte resposta do backend para formato do ImportUploader.
 */
function toValidationResult(response: Record<string, unknown>): ValidationResult {
  const stats = response.stats as Record<string, unknown> | undefined;
  const pendencias = response.pendencias as Record<string, unknown[]> | undefined;

  const errors: string[] = [];
  if (pendencias?.usuarios) {
    (pendencias.usuarios as Array<{ linha: number; nome?: string; email?: string }>).forEach((p) => {
      errors.push(`Linha ${p.linha}: Usuario nao encontrado (${p.email || p.nome})`);
    });
  }
  if (pendencias?.dates) {
    (pendencias.dates as Array<{ linha: number; erro?: string }>).forEach((p) => {
      errors.push(`Linha ${p.linha}: Data invalida${p.erro ? ` - ${p.erro}` : ''}`);
    });
  }

  return {
    stats: {
      created: (stats?.created as number) || 0,
      updated: (stats?.updated as number) || 0,
      unchanged: (stats?.unchanged as number) || 0,
    },
    errors: errors.length > 0 ? errors : undefined,
    pendencias,
  };
}

/**
 * Converte resposta do backend para ApplyResult.
 */
function toApplyResult(response: Record<string, unknown>): ApplyResult {
  const stats = response.stats as Record<string, unknown> | undefined;
  return {
    stats: {
      created: (stats?.created as number) || 0,
      updated: (stats?.updated as number) || 0,
      unchanged: (stats?.unchanged as number) || 0,
    },
  };
}

/**
 * Fetch deslocamentos with filters
 */
async function fetchDeslocamentos(filters: FiltersType = {}): Promise<{ results: DeslocamentoRecord[]; count: number }> {
  const params = new URLSearchParams();
  if (filters.usuario_id) params.append('usuario_id', String(filters.usuario_id));
  if (filters.data_inicio) params.append('data_inicio', filters.data_inicio);
  if (filters.data_fim) params.append('data_fim', filters.data_fim);
  if (filters.origem) params.append('origem', filters.origem);
  if (filters.destino) params.append('destino', filters.destino);
  if (filters.page) params.append('page', String(filters.page));

  const response = await fetch(`${API_BASE}/deslocamentos/?${params.toString()}`, {
    credentials: 'include',
  });

  if (!response.ok) {
    throw new Error(`Erro ao buscar deslocamentos: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Fetch formadores do setor do usuário logado para select.
 * Usa endpoint que filtra automaticamente pela gerencia do usuário.
 */
async function fetchFormadoresDoSetor(): Promise<UsuarioOptionType[]> {
  const response = await fetch(`${API_BASE}/options/formadores-do-setor/`, {
    credentials: 'include',
  });

  if (!response.ok) {
    throw new Error('Erro ao buscar formadores');
  }

  return response.json();
}

/**
 * Create deslocamento
 */
async function createDeslocamento(data: Record<string, unknown>): Promise<DeslocamentoRecord> {
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
async function updateDeslocamento(id: ID, data: Record<string, unknown>): Promise<DeslocamentoRecord> {
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
async function deleteDeslocamento(id: ID): Promise<void> {
  const response = await fetch(`${API_BASE}/deslocamentos/${id}/`, {
    method: 'DELETE',
    credentials: 'include',
  });

  if (!response.ok) {
    throw new Error('Erro ao deletar deslocamento');
  }
}

export default function DeslocamentosPage(): JSX.Element {
  const [viewMode, setViewMode] = useState<ViewMode>('lista');
  const [canAccess, setCanAccess] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);
  const [deslocamentos, setDeslocamentos] = useState<DeslocamentoRecord[]>([]);
  const [usuarios, setUsuarios] = useState<UsuarioOptionType[]>([]);
  const [pagination, setPagination] = useState<TablePaginationConfig>({ current: 1, pageSize: 50, total: 0 });
  const [filters, setFilters] = useState<FiltersType>({});
  const [modalVisible, setModalVisible] = useState<boolean>(false);
  const [modalMode, setModalMode] = useState<'create' | 'edit'>('create');
  const [currentRecord, setCurrentRecord] = useState<DeslocamentoRecord | null>(null);
  const [form] = Form.useForm<FormValuesType>();

  // Load user and check permissions
  useEffect(() => {
    async function loadUser(): Promise<void> {
      try {
        const userData = await getMe() as CurrentUser;

        // Check RBAC: Controle, Coordenador, or DAT
        const canControle = userData.groups?.includes('Controle');
        const canCoordenador = userData.groups?.includes('Coordenador');
        const canDAT = userData.groups?.includes('DAT');
        const canSuper = userData.is_superuser || (userData as CurrentUser & { is_superintendencia?: boolean }).is_superintendencia;

        setCanAccess(!!(canControle || canCoordenador || canDAT || canSuper));
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
  const loadDeslocamentos = useCallback(async (page = 1): Promise<void> => {
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
      message.error((error as Error).message);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  // Load formadores do setor do usuário logado
  const loadFormadores = useCallback(async (): Promise<void> => {
    try {
      const data = await fetchFormadoresDoSetor();
      setUsuarios(data);
    } catch (error) {
      logger.error('Erro ao carregar formadores:', error);
    }
  }, []);

  useEffect(() => {
    if (canAccess) {
      loadDeslocamentos();
      loadFormadores();
    }
  }, [canAccess, filters, loadDeslocamentos, loadFormadores]);

  // Handle table change (pagination)
  const handleTableChange = (paginationConfig: TablePaginationConfig): void => {
    loadDeslocamentos(paginationConfig.current);
  };

  // Handle filter change
  const handleFilterChange = (key: keyof FiltersType, value: string | ID | undefined): void => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  // Handle date range change
  const handleDateRangeChange = (dates: [Dayjs | null, Dayjs | null] | null): void => {
    if (dates && dates.length === 2 && dates[0] && dates[1]) {
      setFilters((prev) => ({
        ...prev,
        data_inicio: dates[0]!.format('YYYY-MM-DD'),
        data_fim: dates[1]!.format('YYYY-MM-DD'),
      }));
    } else {
      setFilters((prev) => {
        const { data_inicio: _data_inicio, data_fim: _data_fim, ...rest } = prev;
        return rest;
      });
    }
  };

  // Open modal for create
  const handleCreate = (): void => {
    setModalMode('create');
    setCurrentRecord(null);
    form.resetFields();
    setModalVisible(true);
  };

  // Open modal for edit
  const handleEdit = (record: DeslocamentoRecord): void => {
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
  const handleModalSubmit = async (): Promise<void> => {
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
        await updateDeslocamento(currentRecord!.id, data);
        message.success('Deslocamento atualizado com sucesso!');
      }

      setModalVisible(false);
      form.resetFields();
      loadDeslocamentos(pagination.current);
    } catch (error) {
      const apiError = error as ApiErrorType;
      if (apiError.end_date) {
        message.error(apiError.end_date[0]);
      } else if (apiError.destino) {
        message.error(apiError.destino[0]);
      } else {
        message.error('Erro ao salvar deslocamento');
      }
    }
  };

  // Handle delete
  const handleDelete = async (id: ID): Promise<void> => {
    try {
      await deleteDeslocamento(id);
      message.success('Deslocamento deletado com sucesso!');
      loadDeslocamentos(pagination.current);
    } catch {
      message.error('Erro ao deletar deslocamento');
    }
  };

  // Columns for table
  const columns: ColumnsType<DeslocamentoRecord> = [
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
      render: (date: string) => dayjs(date).format('DD/MM/YYYY'),
    },
    {
      title: 'Data Fim',
      dataIndex: 'end_date',
      key: 'end_date',
      width: 120,
      render: (date: string) => dayjs(date).format('DD/MM/YYYY'),
    },
    {
      title: 'Observação',
      dataIndex: 'observacao',
      key: 'observacao',
      ellipsis: true,
      render: (text: string | undefined) => (
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
          <Text type="secondary">
            {viewMode === 'lista'
              ? 'Gestão de deslocamentos entre municípios'
              : 'Importe deslocamentos em massa via arquivo CSV/XLSX'}
          </Text>
        </div>
        <Space>
          <Radio.Group
            value={viewMode}
            onChange={(e: RadioChangeEvent) => setViewMode(e.target.value)}
            buttonStyle="solid"
          >
            <Radio.Button value="lista">Lista</Radio.Button>
            <Radio.Button value="importar">Importar</Radio.Button>
          </Radio.Group>
          {viewMode === 'lista' && (
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              Novo Deslocamento
            </Button>
          )}
        </Space>
      </div>

      {viewMode === 'lista' ? (
        <>
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
              onChange={(value: ID | undefined) => handleFilterChange('usuario_id', value)}
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
              onChange={(e: ChangeEvent<HTMLInputElement>) => handleFilterChange('origem', e.target.value)}
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Input
              placeholder="Destino"
              prefix={<SearchOutlined />}
              onChange={(e: ChangeEvent<HTMLInputElement>) => handleFilterChange('destino', e.target.value)}
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
        </>
      ) : (
        /* View: Importar em Massa */
        <Row gutter={[16, 16]}>
          <Col xs={24} lg={16}>
            <Card
              title={
                <span>
                  <UploadOutlined style={{ marginRight: 8 }} />
                  Importar Deslocamentos em Massa
                </span>
              }
              bordered={false}
            >
              <ImportUploader
                label="Selecione o arquivo"
                description="CSV/XLSX com colunas: usuario, origem, destino, data_inicio, data_fim, observacao"
                onDryRun={async (file: File) => toValidationResult(await importDeslocamentos(file, true) as unknown as Record<string, unknown>)}
                onApply={async (file: File) => {
                  const result = await importDeslocamentos(file, false);
                  await loadDeslocamentos();
                  return toApplyResult(result as unknown as Record<string, unknown>);
                }}
              />
            </Card>
          </Col>

          {/* Card de Instrucoes */}
          <Col xs={24} lg={8}>
            <Card title="Formato do Arquivo" bordered={false}>
              <Text strong>Colunas obrigatorias:</Text>
              <ul style={{ marginTop: 8, paddingLeft: 20 }}>
                <li><code>usuario</code> - Email ou nome do formador</li>
                <li><code>origem</code> - Local de origem</li>
                <li><code>destino</code> - Local de destino</li>
                <li><code>data_inicio</code> - Data de inicio</li>
                <li><code>data_fim</code> - Data de fim</li>
              </ul>
              <Text strong style={{ marginTop: 16, display: 'block' }}>Coluna opcional:</Text>
              <ul style={{ marginTop: 8, paddingLeft: 20 }}>
                <li><code>observacao</code> - Observacao</li>
              </ul>
              <Text type="secondary" style={{ marginTop: 16, display: 'block', fontSize: 12 }}>
                Formatos de data aceitos: YYYY-MM-DD, DD/MM/YYYY, ISO 8601
              </Text>
            </Card>
          </Col>
        </Row>
      )}

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
