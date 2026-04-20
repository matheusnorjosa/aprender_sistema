/**
 * DAT Module - Gestão de Cadastros em Plataformas
 *
 * Issue #303: Refactored - extracted constants, columns, and helpers to ./Cadastros/
 *
 * Workflow FORMAR: Criação Curso → Chaves → Instruções → Envio
 * Workflow AVALIAR: Recebidos → Validados → Importados
 */

import { useState, useEffect } from 'react';
import { useTableFilters, type TableFilterParams } from '../../hooks/useTableFilters';
import type { PaginatedResponse } from '../../types';
import {
  Table,
  Button,
  Input,
  Space,
  Typography,
  Card,
  message,
  Select,
  Modal,
  Form,
  InputNumber,
  DatePicker,
  Divider,
  Row,
  Col,
  Statistic,
  Tabs,
  Badge,
} from 'antd';
import {
  ReloadOutlined,
  PlusOutlined,
  DeleteOutlined,
  DownloadOutlined,
  FilterOutlined,
  ClearOutlined,
  CheckCircleFilled,
  ClockCircleFilled,
  ExclamationCircleFilled,
  MinusCircleFilled,
  CloudServerOutlined,
  BookOutlined,
  BarChartOutlined,
  LinkOutlined,
} from '@ant-design/icons';
import {
  listCadastros,
  createCadastro,
  updateCadastro,
  deleteCadastro,
  updateCadastroEtapa,
  getCadastrosStats,
  getMunicipiosOptions,
  getProjetosGeraisOptions,
} from '../../api/datModule';
import {
  STATUS_OPTIONS,
  PLATAFORMAS,
  UF_OPTIONS,
  DEFAULT_FILTERS,
} from './Cadastros/constants';
import { getColumnsFormar, getColumnsAvaliar } from './Cadastros/columns';
import dayjs from 'dayjs';

const { Title, Text } = Typography;

// ============================================================
// TYPE DEFINITIONS
// ============================================================

interface CadastroRecord {
  id: number;
  municipio: number;
  municipio_nome: string;
  projeto_geral: number;
  projeto_geral_nome: string;
  plataforma: 'FORMAR' | 'AVALIAR';
  quantidade_alunos: number | null;
  quantidade_professores: number | null;
  quantidade_codigos: number | null;
  [key: string]: any;
}

interface CadastrosFilters {
  search: string;
  uf: string | undefined;
  municipio: number | undefined;
  projeto_geral: number | undefined;
  status_etapa: string | undefined;
}

interface CadastroFormValues {
  plataforma: 'FORMAR' | 'AVALIAR';
  projeto_geral: number;
  municipio: number;
  [key: string]: any;
}

interface CadastrosStats {
  total_formar: number;
  total_avaliar: number;
  pendentes: number;
  em_andamento: number;
  concluidos: number;
}

interface MunicipioOption {
  id: number;
  nome: string;
  uf: string;
}

interface ProjetoGeralOption {
  id: number;
  nome: string;
}


export default function CadastrosPage(): JSX.Element {
  const [activeTab, setActiveTab] = useState<'FORMAR' | 'AVALIAR'>('FORMAR');

  // Options for dropdowns
  const [municipios, setMunicipios] = useState<MunicipioOption[]>([]);
  const [projetosGerais, setProjetosGerais] = useState<ProjetoGeralOption[]>([]);

  // Modal states
  const [modalVisible, setModalVisible] = useState<boolean>(false);
  const [editingCadastro, setEditingCadastro] = useState<CadastroRecord | null>(null);

  const [form] = Form.useForm<CadastroFormValues>();

  const {
    data: cadastros,
    stats,
    loading,
    filters,
    setFilters,
    pagination,
    fetchData,
    handleClearFilters,
    handleTableChange,
    refresh,
  } = useTableFilters<CadastrosFilters, CadastroRecord, CadastrosStats>({
    defaultFilters: DEFAULT_FILTERS as CadastrosFilters,
    listFn: listCadastros as unknown as (params: TableFilterParams) => Promise<PaginatedResponse<CadastroRecord>>,
    statsFn: getCadastrosStats as unknown as (params: TableFilterParams) => Promise<CadastrosStats>,
    buildParams: (f) => ({
      ...(f.search && { search: f.search }),
      ...(f.uf && { uf: f.uf }),
      ...(f.municipio !== undefined && { municipio_id: f.municipio }),
      ...(f.projeto_geral !== undefined && { projeto_geral_id: f.projeto_geral }),
      ...(f.status_etapa && { status_etapa: f.status_etapa }),
      plataforma: activeTab,
    }),
    defaultOrdering: '-updated_at',
    entityName: 'cadastros',
  });

  // Refetch when tab changes (activeTab lives outside filters to avoid being cleared).
  useEffect(() => {
    void fetchData(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab]);

  // Load options on mount
  useEffect(() => {
    const loadOptions = async () => {
      try {
        const [munData, pgData] = await Promise.all([
          getMunicipiosOptions(),
          getProjetosGeraisOptions(),
        ]);
        setMunicipios((munData as any).results || munData || []);
        setProjetosGerais((pgData as any).results || pgData || []);
      } catch (error) {
        message.error(`Erro ao carregar opções: ${(error as Error).message}`);
      }
    };
    loadOptions();
  }, []);

  // CRUD handlers
  const handleCreate = () => {
    setEditingCadastro(null);
    form.resetFields();
    form.setFieldsValue({ plataforma: activeTab });
    setModalVisible(true);
  };

  const handleEdit = (record: CadastroRecord) => {
    setEditingCadastro(record);
    form.setFieldsValue({
      ...record,
      data_criacao_curso: record.data_criacao_curso ? dayjs(record.data_criacao_curso) : null,
      data_chaves: record.data_chaves ? dayjs(record.data_chaves) : null,
      data_instrucoes: record.data_instrucoes ? dayjs(record.data_instrucoes) : null,
      data_envio: record.data_envio ? dayjs(record.data_envio) : null,
      data_recebidos: record.data_recebidos ? dayjs(record.data_recebidos) : null,
      data_validados: record.data_validados ? dayjs(record.data_validados) : null,
      data_importados: record.data_importados ? dayjs(record.data_importados) : null,
    });
    setModalVisible(true);
  };

  const handleSave = async (values: CadastroFormValues) => {
    try {
      const payload = {
        ...values,
        data_criacao_curso: values.data_criacao_curso?.format('YYYY-MM-DD') || null,
        data_chaves: values.data_chaves?.format('YYYY-MM-DD') || null,
        data_instrucoes: values.data_instrucoes?.format('YYYY-MM-DD') || null,
        data_envio: values.data_envio?.format('YYYY-MM-DD') || null,
        data_recebidos: values.data_recebidos?.format('YYYY-MM-DD') || null,
        data_validados: values.data_validados?.format('YYYY-MM-DD') || null,
        data_importados: values.data_importados?.format('YYYY-MM-DD') || null,
      };

      if (editingCadastro) {
        await updateCadastro(editingCadastro.id, payload);
        message.success('Cadastro atualizado com sucesso');
      } else {
        await createCadastro(payload);
        message.success('Cadastro criado com sucesso');
      }
      setModalVisible(false);
      form.resetFields();
      void refresh();
    } catch (error) {
      message.error(`Erro: ${(error as Error).message}`);
    }
  };

  const handleDelete = (record: CadastroRecord) => {
    Modal.confirm({
      title: 'Confirmar exclusão',
      content: `Excluir cadastro de "${record.municipio_nome}"?`,
      okText: 'Sim, excluir',
      okType: 'danger',
      cancelText: 'Cancelar',
      onOk: async () => {
        try {
          await deleteCadastro(record.id);
          message.success('Cadastro excluído com sucesso');
          void refresh();
        } catch (error) {
          message.error(`Erro ao excluir: ${(error as Error).message}`);
        }
      },
    });
  };

  // Quick status update
  const handleQuickStatusUpdate = async (record: CadastroRecord, etapa: string, newStatus: string) => {
    try {
      await updateCadastroEtapa(record.id, etapa, newStatus);
      message.success('Status atualizado');
      void refresh();
    } catch (error) {
      message.error(`Erro: ${(error as Error).message}`);
    }
  };

  // Issue #303: Column definitions extracted to ./Cadastros/columns.jsx
  const columnHandlers = {
    onQuickStatusUpdate: handleQuickStatusUpdate,
    onEdit: handleEdit,
    onDelete: handleDelete,
  };

  const currentColumns =
    activeTab === 'FORMAR'
      ? getColumnsFormar(columnHandlers as any)
      : getColumnsAvaliar(columnHandlers as any);
  const currentPlataforma = PLATAFORMAS[activeTab];

  return (
    <section className="p-6 bg-gray-100" style={{ minHeight: 'calc(100vh - 64px)' }} aria-labelledby="cadastros-title">
      {/* Header */}
      <header className="mb-6">
        <div className="flex justify-between items-start mb-2">
          <div>
            <Title level={3} className="m-0" id="cadastros-title">
              <CloudServerOutlined className="mr-2" />
              Gestão de Cadastros em Plataformas
            </Title>
            <Text type="secondary">
              Acompanhamento de workflows nas plataformas FORMAR e AVALIAR
            </Text>
          </div>
          <Space>
            <Button icon={<DownloadOutlined />}>Exportar</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              Novo Cadastro
            </Button>
          </Space>
        </div>
      </header>

      {/* Tabs for FORMAR / AVALIAR */}
      <Card className="mb-4">
        <Tabs
          activeKey={activeTab}
          onChange={(key) => setActiveTab(key as 'FORMAR' | 'AVALIAR')}
          items={[
            {
              key: 'FORMAR',
              label: (
                <Space>
                  <BookOutlined className="text-blue-500" />
                  <span>FORMAR</span>
                  <Badge count={stats?.total_formar || 0} style={{ backgroundColor: '#1890ff' }} />
                </Space>
              ),
            },
            {
              key: 'AVALIAR',
              label: (
                <Space>
                  <BarChartOutlined className="text-green-500" />
                  <span>AVALIAR</span>
                  <Badge count={stats?.total_avaliar || 0} style={{ backgroundColor: '#52c41a' }} />
                </Space>
              ),
            },
          ]}
        />

        {/* Stats Cards */}
        {stats && (
          <Row gutter={16} className="mt-4">
            <Col xs={24} sm={12} md={6}>
              <Card size="small">
                <Statistic
                  title="Total Cadastros"
                  value={activeTab === 'FORMAR' ? stats.total_formar : stats.total_avaliar}
                  prefix={currentPlataforma.icon}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Card size="small">
                <Statistic
                  title="Pendentes"
                  value={stats.pendentes || 0}
                  valueStyle={{ color: '#faad14' }}
                  prefix={<ExclamationCircleFilled />}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Card size="small">
                <Statistic
                  title="Em Andamento"
                  value={stats.em_andamento || 0}
                  valueStyle={{ color: '#1890ff' }}
                  prefix={<ClockCircleFilled />}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Card size="small">
                <Statistic
                  title="Concluídos"
                  value={stats.concluidos || 0}
                  valueStyle={{ color: '#52c41a' }}
                  prefix={<CheckCircleFilled />}
                />
              </Card>
            </Col>
          </Row>
        )}
      </Card>

      {/* Filters Card */}
      <nav aria-label="Filtros de busca">
      <Card className="mb-4" bodyStyle={{ paddingBottom: 12 }}>
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} md={8} lg={5}>
            <div className="mb-1">
              <Text type="secondary" style={{ fontSize: 12, textTransform: 'uppercase' }}>
                Buscar
              </Text>
            </div>
            <Input.Search
              placeholder="Município, projeto..."
              allowClear
              value={filters.search}
              onChange={(e) => setFilters((prev) => ({ ...prev, search: e.target.value }))}
              onSearch={() => fetchData(1)}
            />
          </Col>
          <Col xs={24} sm={12} md={8} lg={4}>
            <div className="mb-1">
              <Text type="secondary" style={{ fontSize: 12, textTransform: 'uppercase' }}>
                Projeto
              </Text>
            </div>
            <Select
              style={{ width: '100%' }}
              placeholder="Todos"
              allowClear
              showSearch
              optionFilterProp="label"
              value={filters.projeto_geral}
              onChange={(val) => setFilters((prev) => ({ ...prev, projeto_geral: val }))}
              options={projetosGerais.map((p) => ({ label: p.nome, value: p.id }))}
            />
          </Col>
          <Col xs={24} sm={12} md={8} lg={3}>
            <div className="mb-1">
              <Text type="secondary" style={{ fontSize: 12, textTransform: 'uppercase' }}>
                UF
              </Text>
            </div>
            <Select
              style={{ width: '100%' }}
              placeholder="Todos"
              allowClear
              value={filters.uf}
              onChange={(val) => setFilters((prev) => ({ ...prev, uf: val }))}
              options={UF_OPTIONS}
              showSearch
            />
          </Col>
          <Col xs={24} sm={12} md={8} lg={5}>
            <div className="mb-1">
              <Text type="secondary" style={{ fontSize: 12, textTransform: 'uppercase' }}>
                Município
              </Text>
            </div>
            <Select
              style={{ width: '100%' }}
              placeholder="Buscar..."
              allowClear
              showSearch
              optionFilterProp="label"
              value={filters.municipio}
              onChange={(val) => setFilters((prev) => ({ ...prev, municipio: val }))}
              options={municipios.map((m) => ({ label: `${m.nome} - ${m.uf}`, value: m.id }))}
            />
          </Col>
          <Col xs={24} sm={12} md={8} lg={4}>
            <div className="mb-1">
              <Text type="secondary" style={{ fontSize: 12, textTransform: 'uppercase' }}>
                Status
              </Text>
            </div>
            <Select
              style={{ width: '100%' }}
              placeholder="Todos"
              allowClear
              value={filters.status_etapa}
              onChange={(val) => setFilters((prev) => ({ ...prev, status_etapa: val }))}
              options={[
                { label: 'Pendentes', value: 'pendente' },
                { label: 'Em Andamento', value: 'em_andamento' },
                { label: 'Concluídos', value: 'concluido' },
              ]}
            />
          </Col>
        </Row>
        <Divider className="my-4 mb-3" />
        <div className="flex justify-end gap-2">
          <Button icon={<ClearOutlined />} onClick={handleClearFilters}>
            Limpar
          </Button>
          <Button icon={<ReloadOutlined />} onClick={() => fetchData(1)} loading={loading}>
            Atualizar
          </Button>
          <Button type="primary" icon={<FilterOutlined />} onClick={() => fetchData(1)}>
            Filtrar
          </Button>
        </div>
      </Card>
      </nav>

      {/* Table Card */}
      <section aria-label="Resultados da busca">
      <Card
        bodyStyle={{ padding: 0 }}
        title={
          <Space>
            {currentPlataforma.icon}
            <Text strong>Cadastros {currentPlataforma.label}:</Text>
            <Text type="danger" strong>{pagination.total}</Text>
            <Text>registros</Text>
          </Space>
        }
        extra={
          <Button
            type="link"
            icon={<LinkOutlined />}
            href={currentPlataforma.url}
            target="_blank"
          >
            Abrir {currentPlataforma.label}
          </Button>
        }
      >
        <Table
          columns={currentColumns as any}
          dataSource={cadastros}
          rowKey="id"
          loading={loading}
          scroll={{ x: activeTab === 'FORMAR' ? 1200 : 1100 }}
          pagination={{
            ...pagination,
            showSizeChanger: true,
            showTotal: (total, range) => `Mostrando ${range[0]} a ${range[1]} de ${total} cadastros`,
            onChange: handleTableChange,
          }}
          size="middle"
        />
      </Card>
      </section>

      {/* Legend */}
      <aside aria-label="Legenda de status">
      <Card className="mt-4" size="small">
        <Space size="large" wrap>
          <Text strong style={{ textTransform: 'uppercase', fontSize: 12 }}>
            Legenda (clique nos ícones para alterar):
          </Text>
          <Space>
            <CheckCircleFilled className="text-green-500" />
            <Text type="secondary">Concluído</Text>
          </Space>
          <Space>
            <ClockCircleFilled className="text-yellow-500" />
            <Text type="secondary">Em Andamento</Text>
          </Space>
          <Space>
            <ExclamationCircleFilled className="text-red-500" />
            <Text type="secondary">Pendente</Text>
          </Space>
          <Space>
            <MinusCircleFilled className="text-gray-400" />
            <Text type="secondary">N/A</Text>
          </Space>
        </Space>
      </Card>
      </aside>

      {/* Create/Edit Modal */}
      <Modal
        title={
          <div>
            <Title level={4} className="m-0">
              {editingCadastro ? 'Editar Cadastro' : 'Novo Cadastro'}
            </Title>
            <Text type="secondary" style={{ fontSize: 13 }}>
              Plataforma: {activeTab}
            </Text>
          </div>
        }
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={
          <div className="flex justify-between">
            <div>
              {editingCadastro && (
                <Button
                  danger
                  type="text"
                  icon={<DeleteOutlined />}
                  onClick={() => {
                    setModalVisible(false);
                    handleDelete(editingCadastro);
                  }}
                >
                  Excluir
                </Button>
              )}
            </div>
            <Space>
              <Button onClick={() => setModalVisible(false)}>Cancelar</Button>
              <Button type="primary" onClick={() => form.submit()}>
                Salvar
              </Button>
            </Space>
          </div>
        }
        width={900}
        styles={{ body: { maxHeight: 'calc(100vh - 250px)', overflowY: 'auto' } }}
      >
        <Form form={form} layout="vertical" autoComplete="off" onFinish={handleSave}>
          <Form.Item name="plataforma" hidden>
            <Input />
          </Form.Item>

          {/* Identificação */}
          <Card size="small" title="Identificação" className="mb-4">
            <Row gutter={16}>
              <Col xs={24} sm={12}>
                <Form.Item
                  name="projeto_geral"
                  label="Projeto"
                  rules={[{ required: true, message: 'Selecione o projeto' }]}
                >
                  <Select
                    placeholder="Selecione..."
                    showSearch
                    optionFilterProp="label"
                    options={projetosGerais.map((p) => ({ label: p.nome, value: p.id }))}
                  />
                </Form.Item>
              </Col>
              <Col xs={24} sm={12}>
                <Form.Item
                  name="municipio"
                  label="Município"
                  rules={[{ required: true, message: 'Selecione o município' }]}
                >
                  <Select
                    placeholder="Buscar município..."
                    showSearch
                    optionFilterProp="label"
                    options={municipios.map((m) => ({ label: `${m.nome} - ${m.uf}`, value: m.id }))}
                  />
                </Form.Item>
              </Col>
            </Row>
          </Card>

          {/* Status FORMAR */}
          {activeTab === 'FORMAR' && (
            <Card
              size="small"
              title={
                <Space>
                  <BookOutlined className="text-blue-500" />
                  <span>Workflow FORMAR</span>
                </Space>
              }
              className="mb-4"
            >
              <Row gutter={16}>
                <Col xs={12} sm={6}>
                  <Form.Item name="status_criacao_curso" label="Criação Curso">
                    <Select placeholder="Status" options={STATUS_OPTIONS} allowClear />
                  </Form.Item>
                  <Form.Item name="data_criacao_curso">
                    <DatePicker style={{ width: '100%' }} format="DD/MM/YYYY" placeholder="Data" />
                  </Form.Item>
                </Col>
                <Col xs={12} sm={6}>
                  <Form.Item name="status_chaves" label="Chaves">
                    <Select placeholder="Status" options={STATUS_OPTIONS} allowClear />
                  </Form.Item>
                  <Form.Item name="data_chaves">
                    <DatePicker style={{ width: '100%' }} format="DD/MM/YYYY" placeholder="Data" />
                  </Form.Item>
                </Col>
                <Col xs={12} sm={6}>
                  <Form.Item name="status_instrucoes" label="Instruções">
                    <Select placeholder="Status" options={STATUS_OPTIONS} allowClear />
                  </Form.Item>
                  <Form.Item name="data_instrucoes">
                    <DatePicker style={{ width: '100%' }} format="DD/MM/YYYY" placeholder="Data" />
                  </Form.Item>
                </Col>
                <Col xs={12} sm={6}>
                  <Form.Item name="status_envio" label="Envio">
                    <Select placeholder="Status" options={STATUS_OPTIONS} allowClear />
                  </Form.Item>
                  <Form.Item name="data_envio">
                    <DatePicker style={{ width: '100%' }} format="DD/MM/YYYY" placeholder="Data" />
                  </Form.Item>
                </Col>
              </Row>
            </Card>
          )}

          {/* Status AVALIAR */}
          {activeTab === 'AVALIAR' && (
            <Card
              size="small"
              title={
                <Space>
                  <BarChartOutlined className="text-green-500" />
                  <span>Workflow AVALIAR</span>
                </Space>
              }
              className="mb-4"
            >
              <Row gutter={16}>
                <Col xs={24} sm={8}>
                  <Form.Item name="status_recebidos" label="Recebidos">
                    <Select placeholder="Status" options={STATUS_OPTIONS} allowClear />
                  </Form.Item>
                  <Form.Item name="quantidade_recebidos" label="Quantidade">
                    <InputNumber min={0} style={{ width: '100%' }} placeholder="0" />
                  </Form.Item>
                  <Form.Item name="data_recebidos">
                    <DatePicker style={{ width: '100%' }} format="DD/MM/YYYY" placeholder="Data" />
                  </Form.Item>
                </Col>
                <Col xs={24} sm={8}>
                  <Form.Item name="status_validados" label="Validados">
                    <Select placeholder="Status" options={STATUS_OPTIONS} allowClear />
                  </Form.Item>
                  <Form.Item name="quantidade_validados" label="Quantidade">
                    <InputNumber min={0} style={{ width: '100%' }} placeholder="0" />
                  </Form.Item>
                  <Form.Item name="data_validados">
                    <DatePicker style={{ width: '100%' }} format="DD/MM/YYYY" placeholder="Data" />
                  </Form.Item>
                </Col>
                <Col xs={24} sm={8}>
                  <Form.Item name="status_importados" label="Importados">
                    <Select placeholder="Status" options={STATUS_OPTIONS} allowClear />
                  </Form.Item>
                  <Form.Item name="quantidade_importados" label="Quantidade">
                    <InputNumber min={0} style={{ width: '100%' }} placeholder="0" />
                  </Form.Item>
                  <Form.Item name="data_importados">
                    <DatePicker style={{ width: '100%' }} format="DD/MM/YYYY" placeholder="Data" />
                  </Form.Item>
                </Col>
              </Row>
            </Card>
          )}

          {/* Links */}
          <Card size="small" title="Links" className="mb-4">
            <Row gutter={16}>
              <Col xs={24} sm={12}>
                <Form.Item name="link_planilha" label="Link da Planilha">
                  <Input placeholder="https://docs.google.com/spreadsheets/..." />
                </Form.Item>
              </Col>
              <Col xs={24} sm={12}>
                <Form.Item name="link_plataforma" label="Link da Plataforma">
                  <Input placeholder="https://..." />
                </Form.Item>
              </Col>
            </Row>
          </Card>

          {/* Observações */}
          <Form.Item name="observacoes" label="Observações">
            <Input.TextArea rows={3} placeholder="Observações sobre o cadastro..." />
          </Form.Item>
        </Form>
      </Modal>
    </section>
  );
}
