/**
 * DAT Module - Gestão de Formações/Treinamentos
 *
 * Issue #303: Refactored - extracted constants, columns, and helpers to ./Formacoes/
 *
 * Interface de gestão do calendário de formações.
 * Agendamentos, formadores, locais e acompanhamento.
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Table,
  Button,
  Input,
  Space,
  Tag,
  Typography,
  Card,
  message,
  Select,
  Modal,
  Form,
  InputNumber,
  DatePicker,
  TimePicker,
  Divider,
  Row,
  Col,
  Statistic,
  Checkbox,
  Calendar,
  Badge,
} from 'antd';
import {
  ReloadOutlined,
  PlusOutlined,
  DownloadOutlined,
  FilterOutlined,
  ClearOutlined,
  CalendarOutlined,
  TableOutlined,
  TeamOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  DeleteOutlined,
} from '@ant-design/icons';
import {
  listFormacoes,
  createFormacao,
  updateFormacao,
  deleteFormacao,
  getFormacoesStats,
  getFormacoesCalendario,
  getMunicipiosOptions,
  getProjetosOptions,
  getCoordenadoresOptions,
} from '../../api/datModule';
import dayjs, { Dayjs } from 'dayjs';
import {
  STATUS_OPTIONS,
  MODALIDADE_OPTIONS,
  UF_OPTIONS,
  DEFAULT_FILTERS,
  VIEW_MODES,
} from './Formacoes/constants';
import { getColumns } from './Formacoes/columns';
import { renderStatusTag } from './Formacoes/helpers';

const { Title, Text } = Typography;

// ============================================================
// TYPE DEFINITIONS
// ============================================================

interface FormacaoRecord {
  id: number;
  projeto: number;
  projeto_nome: string;
  municipio: number;
  municipio_nome: string;
  uf: string;
  coordenador: number | null;
  coordenador_nome: string | null;
  data_formacao: string | null;
  horario_inicio: string | null;
  horario_fim: string | null;
  status: string | null;
  [key: string]: any;
}

interface FormacoesFilters {
  search: string;
  uf: string | undefined;
  municipio: number | undefined;
  projeto: number | undefined;
  coordenador: number | undefined;
  status: string | undefined;
  modalidade: string | undefined;
  data_inicio: any;
  data_fim: any;
}

interface FormacaoFormValues {
  projeto: number;
  municipio: number;
  coordenador: number | null;
  [key: string]: any;
}

interface FormacoesStats {
  total: number;
  este_mes: number;
  realizadas: number;
  total_participantes: number;
}

interface PaginationState {
  current: number;
  pageSize: number;
  total: number;
}

interface MunicipioOption {
  id: number;
  nome: string;
  uf: string;
}

interface ProjetoOption {
  id: number;
  nome: string;
}

interface CoordenadorOption {
  id: number;
  nome: string;
}

interface CalendarFormacaoItem {
  id: number;
  data_formacao: string;
  projeto_nome: string;
  municipio_nome: string;
  uf: string;
  status: string | null;
  [key: string]: any;
}


export default function FormacoesPage(): JSX.Element {
  const [formacoes, setFormacoes] = useState<FormacaoRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [pagination, setPagination] = useState<PaginationState>({ current: 1, pageSize: 15, total: 0 });
  const [stats, setStats] = useState<FormacoesStats | null>(null);
  const [viewMode, setViewMode] = useState<string>(VIEW_MODES.TABLE);
  const [calendarData, setCalendarData] = useState<CalendarFormacaoItem[]>([]);

  // Filter states - using DEFAULT_FILTERS from constants
  const [filters, setFilters] = useState<FormacoesFilters>(DEFAULT_FILTERS as FormacoesFilters);

  // Options for dropdowns
  const [municipios, setMunicipios] = useState<MunicipioOption[]>([]);
  const [projetos, setProjetos] = useState<ProjetoOption[]>([]);
  const [coordenadores, setCoordenadores] = useState<CoordenadorOption[]>([]);

  // Modal states
  const [modalVisible, setModalVisible] = useState<boolean>(false);
  const [editingFormacao, setEditingFormacao] = useState<FormacaoRecord | null>(null);

  const [form] = Form.useForm<FormacaoFormValues>();

  // Load options on mount
  useEffect(() => {
    const loadOptions = async () => {
      try {
        const [munData, projData, coordData] = await Promise.all([
          getMunicipiosOptions(),
          getProjetosOptions(),
          getCoordenadoresOptions(),
        ]);
        setMunicipios((munData as any).results || munData || []);
        setProjetos((projData as any).results || projData || []);
        setCoordenadores((coordData as any).results || coordData || []);
      } catch (error) {
        message.error(`Erro ao carregar opções: ${(error as Error).message}`);
      }
    };
    loadOptions();
  }, []);

  // Fetch data with filters
  const fetchData = useCallback(async (page = 1) => {
    setLoading(true);
    try {
      const params: any = {
        page,
        page_size: pagination.pageSize,
        ordering: 'data_formacao',
      };

      // Apply filters
      if (filters.search) params.search = filters.search;
      if (filters.uf) params.uf = filters.uf;
      if (filters.municipio) params.municipio_id = filters.municipio;
      if (filters.projeto) params.projeto_id = filters.projeto;
      if (filters.coordenador) params.coordenador_id = filters.coordenador;
      if (filters.status) params.status = filters.status;
      if (filters.modalidade) params.modalidade = filters.modalidade;
      if (filters.data_inicio) params.data_inicio = filters.data_inicio.format('YYYY-MM-DD');
      if (filters.data_fim) params.data_fim = filters.data_fim.format('YYYY-MM-DD');

      const [data, statsData] = await Promise.all([
        listFormacoes(params),
        getFormacoesStats(params),
      ]);

      setFormacoes((data as any).results || data || []);
      setPagination((prev) => ({
        ...prev,
        current: page,
        total: data.count || ((data as any).results || data || []).length,
      }));
      setStats(statsData as unknown as FormacoesStats);

      // Load calendar data if in calendar view
      if (viewMode === VIEW_MODES.CALENDAR) {
        const calData = await getFormacoesCalendario(params);
        setCalendarData((calData as any).results || calData || []);
      }
    } catch (error) {
      message.error(`Erro ao carregar dados: ${(error as Error).message}`);
    } finally {
      setLoading(false);
    }
  }, [filters, pagination.pageSize, viewMode]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Clear all filters
  const handleClearFilters = () => {
    setFilters(DEFAULT_FILTERS);
  };

  // CRUD handlers
  const handleCreate = () => {
    setEditingFormacao(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (record: FormacaoRecord) => {
    setEditingFormacao(record);
    form.setFieldsValue({
      ...record,
      data_formacao: record.data_formacao ? dayjs(record.data_formacao) : null,
      horario_inicio: record.horario_inicio ? dayjs(record.horario_inicio, 'HH:mm') : null,
      horario_fim: record.horario_fim ? dayjs(record.horario_fim, 'HH:mm') : null,
    });
    setModalVisible(true);
  };

  const handleSave = async (values: FormacaoFormValues) => {
    try {
      const payload = {
        ...values,
        data_formacao: values.data_formacao?.format('YYYY-MM-DD') || null,
        horario_inicio: values.horario_inicio?.format('HH:mm') || null,
        horario_fim: values.horario_fim?.format('HH:mm') || null,
      };

      if (editingFormacao) {
        await updateFormacao(editingFormacao.id, payload);
        message.success('Formação atualizada com sucesso');
      } else {
        await createFormacao(payload);
        message.success('Formação criada com sucesso');
      }
      setModalVisible(false);
      form.resetFields();
      fetchData(pagination.current);
    } catch (error) {
      message.error(`Erro: ${(error as Error).message}`);
    }
  };

  const handleDelete = (record: FormacaoRecord) => {
    Modal.confirm({
      title: 'Confirmar exclusão',
      content: `Excluir formação de "${record.projeto_nome}" em "${record.municipio_nome}"?`,
      okText: 'Sim, excluir',
      okType: 'danger',
      cancelText: 'Cancelar',
      onOk: async () => {
        try {
          await deleteFormacao(record.id);
          message.success('Formação excluída com sucesso');
          fetchData(pagination.current);
        } catch (error) {
          message.error(`Erro ao excluir: ${(error as Error).message}`);
        }
      },
    });
  };

  // Calendar cell renderer
  const dateCellRender = (date: Dayjs) => {
    const dayFormacoes = calendarData.filter(
      (f) => dayjs(f.data_formacao).isSame(date, 'day')
    );

    if (dayFormacoes.length === 0) return null;

    return (
      <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
        {dayFormacoes.slice(0, 3).map((item) => {
          const statusConfig = STATUS_OPTIONS.find((s) => s.value === item.status);
          return (
            <li key={item.id}>
              <Badge
                status={statusConfig?.color === 'green' ? 'success' : statusConfig?.color === 'red' ? 'error' : 'processing'}
                text={
                  <Text style={{ fontSize: 11 }} ellipsis>
                    {item.projeto_nome}
                  </Text>
                }
              />
            </li>
          );
        })}
        {dayFormacoes.length > 3 && (
          <li>
            <Text type="secondary" style={{ fontSize: 11 }}>
              +{dayFormacoes.length - 3} mais
            </Text>
          </li>
        )}
      </ul>
    );
  };

  // Table columns - using extracted getColumns from ./Formacoes/columns (memoized §16 Epic #459)
  const columns = useMemo(
    () => getColumns({ onEdit: handleEdit, onDelete: handleDelete } as any),
    [handleEdit, handleDelete]
  );

  return (
    <div className="p-6 bg-gray-100" style={{ minHeight: 'calc(100vh - 64px)' }}>
      {/* Header */}
      <div className="mb-6">
        <div className="flex justify-between items-start mb-2">
          <div>
            <Title level={3} className="m-0">
              <CalendarOutlined className="mr-2" />
              Gestão de Formações
            </Title>
            <Text type="secondary">
              Calendário de treinamentos e acompanhamento de execução
            </Text>
          </div>
          <Space>
            <Button.Group>
              <Button
                type={viewMode === VIEW_MODES.TABLE ? 'primary' : 'default'}
                icon={<TableOutlined />}
                onClick={() => setViewMode(VIEW_MODES.TABLE)}
              >
                Lista
              </Button>
              <Button
                type={viewMode === VIEW_MODES.CALENDAR ? 'primary' : 'default'}
                icon={<CalendarOutlined />}
                onClick={() => setViewMode(VIEW_MODES.CALENDAR)}
              >
                Calendário
              </Button>
            </Button.Group>
            <Button icon={<DownloadOutlined />}>Exportar</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              Nova Formação
            </Button>
          </Space>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <Row gutter={16} className="mb-4">
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="Total Formações"
                value={stats.total || pagination.total}
                prefix={<CalendarOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="Este Mês"
                value={stats.este_mes || 0}
                valueStyle={{ color: '#1890ff' }}
                prefix={<ClockCircleOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="Realizadas"
                value={stats.realizadas || 0}
                valueStyle={{ color: '#52c41a' }}
                prefix={<CheckCircleOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="Participantes"
                value={stats.total_participantes || 0}
                prefix={<TeamOutlined />}
                formatter={(value) => value.toLocaleString('pt-BR')}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* Filters Card */}
      <Card className="mb-4" bodyStyle={{ paddingBottom: 12 }}>
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} md={6} lg={4}>
            <div className="mb-1">
              <Text type="secondary" style={{ fontSize: 12, textTransform: 'uppercase' }}>
                Buscar
              </Text>
            </div>
            <Input.Search
              placeholder="Município, projeto..."
              allowClear
              value={filters.search}
              onChange={(e) => setFilters((prev: any) => ({ ...prev, search: e.target.value }))}
              onSearch={() => fetchData(1)}
            />
          </Col>
          <Col xs={12} sm={6} md={4} lg={3}>
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
              value={filters.projeto}
              onChange={(val) => setFilters((prev: any) => ({ ...prev, projeto: val }))}
              options={projetos.map((p) => ({ label: p.nome, value: p.id }))}
            />
          </Col>
          <Col xs={12} sm={6} md={4} lg={3}>
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
              onChange={(val) => setFilters((prev: any) => ({ ...prev, uf: val }))}
              options={UF_OPTIONS}
              showSearch
            />
          </Col>
          <Col xs={24} sm={12} md={6} lg={4}>
            <div className="mb-1">
              <Text type="secondary" style={{ fontSize: 12, textTransform: 'uppercase' }}>
                Coordenador
              </Text>
            </div>
            <Select
              style={{ width: '100%' }}
              placeholder="Todos"
              allowClear
              showSearch
              optionFilterProp="label"
              value={filters.coordenador}
              onChange={(val) => setFilters((prev: any) => ({ ...prev, coordenador: val }))}
              options={coordenadores.map((c) => ({ label: c.nome, value: c.id }))}
            />
          </Col>
          <Col xs={12} sm={6} md={4} lg={3}>
            <div className="mb-1">
              <Text type="secondary" style={{ fontSize: 12, textTransform: 'uppercase' }}>
                Status
              </Text>
            </div>
            <Select
              style={{ width: '100%' }}
              placeholder="Todos"
              allowClear
              value={filters.status}
              onChange={(val) => setFilters((prev: any) => ({ ...prev, status: val }))}
              options={STATUS_OPTIONS}
            />
          </Col>
          <Col xs={12} sm={6} md={4} lg={3}>
            <div className="mb-1">
              <Text type="secondary" style={{ fontSize: 12, textTransform: 'uppercase' }}>
                Modalidade
              </Text>
            </div>
            <Select
              style={{ width: '100%' }}
              placeholder="Todas"
              allowClear
              value={filters.modalidade}
              onChange={(val) => setFilters((prev: any) => ({ ...prev, modalidade: val }))}
              options={MODALIDADE_OPTIONS}
            />
          </Col>
          <Col xs={12} sm={6} md={4} lg={4}>
            <div className="mb-1">
              <Text type="secondary" style={{ fontSize: 12, textTransform: 'uppercase' }}>
                Período
              </Text>
            </div>
            <DatePicker.RangePicker
              style={{ width: '100%' }}
              format="DD/MM/YYYY"
              value={[filters.data_inicio, filters.data_fim]}
              onChange={(dates) =>
                setFilters((prev: any) => ({
                  ...prev,
                  data_inicio: dates?.[0] || undefined,
                  data_fim: dates?.[1] || undefined,
                }))
              }
            />
          </Col>
        </Row>
        <Divider style={{ margin: '16px 0 12px' }} />
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

      {/* Content - Table or Calendar */}
      {viewMode === VIEW_MODES.TABLE ? (
        <Card
          bodyStyle={{ padding: 0 }}
          title={
            <Space>
              <Text strong>Formações:</Text>
              <Text type="danger" strong>{pagination.total}</Text>
              <Text>registros</Text>
            </Space>
          }
        >
          <Table
            columns={columns as any}
            dataSource={formacoes}
            rowKey="id"
            loading={loading}
            scroll={{ x: 1400 }}
            pagination={{
              ...pagination,
              showSizeChanger: true,
              showTotal: (total, range) => `Mostrando ${range[0]} a ${range[1]} de ${total} formações`,
              onChange: (page, pageSize) => {
                setPagination((prev) => ({ ...prev, current: page, pageSize }));
                fetchData(page);
              },
            }}
            size="middle"
          />
        </Card>
      ) : (
        <Card title="Calendário de Formações">
          <Calendar
            cellRender={dateCellRender}
            onSelect={(date) => {
              const dayFormacoes = calendarData.filter(
                (f) => dayjs(f.data_formacao).isSame(date, 'day')
              );
              if (dayFormacoes.length > 0) {
                Modal.info({
                  title: `Formações em ${date.format('DD/MM/YYYY')}`,
                  width: 600,
                  content: (
                    <div style={{ maxHeight: 400, overflow: 'auto' }}>
                      {dayFormacoes.map((f) => (
                        <Card
                          key={f.id}
                          size="small"
                          style={{ marginBottom: 8 }}
                          actions={[
                            <Button
                              type="link"
                              size="small"
                              onClick={() => {
                                Modal.destroyAll();
                                handleEdit(f as any);
                              }}
                            >
                              Editar
                            </Button>,
                          ]}
                        >
                          <Space direction="vertical" size={0}>
                            <Text strong>{f.projeto_nome}</Text>
                            <Text>{f.municipio_nome} - {f.uf}</Text>
                            <Text type="secondary">
                              {f.horario_inicio} - {f.horario_fim} | {f.formador_nome}
                            </Text>
                            {renderStatusTag(f.status)}
                          </Space>
                        </Card>
                      ))}
                    </div>
                  ),
                });
              }
            }}
          />
        </Card>
      )}

      {/* Legend */}
      <Card className="mt-4" size="small">
        <Space size="large" wrap>
          <Text strong style={{ textTransform: 'uppercase', fontSize: 12 }}>
            Status:
          </Text>
          {STATUS_OPTIONS.map((s) => (
            <Tag key={s.value} color={s.color}>{s.label}</Tag>
          ))}
        </Space>
      </Card>

      {/* Create/Edit Modal */}
      <Modal
        title={
          <div>
            <Title level={4} className="m-0">
              {editingFormacao ? 'Editar Formação' : 'Nova Formação'}
            </Title>
            <Text type="secondary" style={{ fontSize: 13 }}>
              Agendamento e acompanhamento de treinamentos
            </Text>
          </div>
        }
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={
          <div className="flex justify-between">
            <div>
              {editingFormacao && (
                <Button
                  danger
                  type="text"
                  icon={<DeleteOutlined />}
                  onClick={() => {
                    setModalVisible(false);
                    handleDelete(editingFormacao);
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
        <Form form={form} layout="vertical" onFinish={handleSave}>
          {/* Identificação */}
          <Card size="small" title="Identificação" className="mb-4">
            <Row gutter={16}>
              <Col xs={24} sm={8}>
                <Form.Item
                  name="projeto"
                  label="Projeto"
                  rules={[{ required: true, message: 'Selecione o projeto' }]}
                >
                  <Select
                    placeholder="Selecione..."
                    showSearch
                    optionFilterProp="label"
                    options={projetos.map((p) => ({ label: p.nome, value: p.id }))}
                  />
                </Form.Item>
              </Col>
              <Col xs={24} sm={8}>
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
              <Col xs={24} sm={8}>
                <Form.Item name="coordenador" label="Coordenador">
                  <Select
                    placeholder="Selecione..."
                    showSearch
                    optionFilterProp="label"
                    allowClear
                    options={coordenadores.map((c) => ({ label: c.nome, value: c.id }))}
                  />
                </Form.Item>
              </Col>
            </Row>
          </Card>

          {/* Agendamento */}
          <Card size="small" title="Agendamento" className="mb-4">
            <Row gutter={16}>
              <Col xs={12} sm={6}>
                <Form.Item
                  name="data_formacao"
                  label="Data"
                  rules={[{ required: true, message: 'Informe a data' }]}
                >
                  <DatePicker style={{ width: '100%' }} format="DD/MM/YYYY" />
                </Form.Item>
              </Col>
              <Col xs={12} sm={6}>
                <Form.Item
                  name="horario_inicio"
                  label="Início"
                  rules={[{ required: true, message: 'Informe o horário' }]}
                >
                  <TimePicker style={{ width: '100%' }} format="HH:mm" />
                </Form.Item>
              </Col>
              <Col xs={12} sm={6}>
                <Form.Item
                  name="horario_fim"
                  label="Fim"
                  rules={[{ required: true, message: 'Informe o horário' }]}
                >
                  <TimePicker style={{ width: '100%' }} format="HH:mm" />
                </Form.Item>
              </Col>
              <Col xs={12} sm={6}>
                <Form.Item
                  name="modalidade"
                  label="Modalidade"
                  rules={[{ required: true, message: 'Selecione a modalidade' }]}
                >
                  <Select placeholder="Selecione..." options={MODALIDADE_OPTIONS} />
                </Form.Item>
              </Col>
            </Row>
          </Card>

          {/* Local */}
          <Card size="small" title="Local e Formador" className="mb-4">
            <Row gutter={16}>
              <Col xs={24} sm={12}>
                <Form.Item name="local_formacao" label="Local">
                  <Input placeholder="Nome do local..." />
                </Form.Item>
              </Col>
              <Col xs={24} sm={12}>
                <Form.Item name="endereco" label="Endereço">
                  <Input placeholder="Endereço completo..." />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col xs={24} sm={12}>
                <Form.Item name="formador_nome" label="Nome do Formador">
                  <Input placeholder="Nome do formador..." />
                </Form.Item>
              </Col>
              <Col xs={24} sm={12}>
                <Form.Item name="formador_contato" label="Contato do Formador">
                  <Input placeholder="Telefone ou email..." />
                </Form.Item>
              </Col>
            </Row>
            <Form.Item name="link_online" label="Link da Reunião (para formações online/híbridas)">
              <Input placeholder="https://meet.google.com/..." />
            </Form.Item>
          </Card>

          {/* Participantes */}
          <Card size="small" title="Participantes" className="mb-4">
            <Row gutter={16}>
              <Col xs={8}>
                <Form.Item name="quantidade_prevista" label="Prevista">
                  <InputNumber min={0} style={{ width: '100%' }} placeholder="0" />
                </Form.Item>
              </Col>
              <Col xs={8}>
                <Form.Item name="quantidade_confirmada" label="Confirmada">
                  <InputNumber min={0} style={{ width: '100%' }} placeholder="0" />
                </Form.Item>
              </Col>
              <Col xs={8}>
                <Form.Item name="quantidade_presente" label="Presente">
                  <InputNumber min={0} style={{ width: '100%' }} placeholder="0" />
                </Form.Item>
              </Col>
            </Row>
          </Card>

          {/* Status e Documentação */}
          <Card size="small" title="Status e Documentação" className="mb-4">
            <Row gutter={16}>
              <Col xs={24} sm={8}>
                <Form.Item name="status" label="Status">
                  <Select placeholder="Selecione..." options={STATUS_OPTIONS} />
                </Form.Item>
              </Col>
              <Col xs={24} sm={16}>
                <div style={{ paddingTop: 30 }}>
                  <Space>
                    <Form.Item name="material_preparado" valuePropName="checked" noStyle>
                      <Checkbox>Material preparado</Checkbox>
                    </Form.Item>
                    <Form.Item name="material_enviado" valuePropName="checked" noStyle>
                      <Checkbox>Material enviado</Checkbox>
                    </Form.Item>
                  </Space>
                </div>
              </Col>
            </Row>
            <Divider style={{ margin: '12px 0' }} />
            <Text type="secondary" style={{ fontSize: 12 }}>Pós-formação:</Text>
            <div className="mt-2">
              <Space>
                <Form.Item name="lista_presenca_enviada" valuePropName="checked" noStyle>
                  <Checkbox>Lista de presença</Checkbox>
                </Form.Item>
                <Form.Item name="relatorio_enviado" valuePropName="checked" noStyle>
                  <Checkbox>Relatório</Checkbox>
                </Form.Item>
                <Form.Item name="fotos_enviadas" valuePropName="checked" noStyle>
                  <Checkbox>Fotos</Checkbox>
                </Form.Item>
              </Space>
            </div>
          </Card>

          {/* Observações */}
          <Form.Item name="observacoes" label="Observações">
            <Input.TextArea rows={3} placeholder="Observações sobre a formação..." />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
