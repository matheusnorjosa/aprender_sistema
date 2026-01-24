/**
 * Plano de Formacoes - AS v2
 *
 * Pagina de gestao do plano anual de formacoes por Municipio + Projeto.
 * Cada linha representa uma combinacao unica de municipio/projeto com ate 15 formacoes.
 *
 * Visualizacoes:
 * - Plano Anual (tabela com scroll horizontal)
 * - Calendario (FullCalendar)
 * - Resumo por Projeto
 *
 * Ref: prompt-pagina-formacoes.md
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Table,
  Card,
  Button,
  Space,
  Typography,
  Row,
  Col,
  Statistic,
  Select,
  Input,
  Tag,
  Modal,
  Form,
  DatePicker,
  InputNumber,
  message,
  Tooltip,
  Divider,
  Checkbox,
  Tabs,
} from 'antd';
import {
  PlusOutlined,
  ReloadOutlined,
  FilterOutlined,
  ClearOutlined,
  CalendarOutlined,
  TableOutlined,
  ProjectOutlined,
  EditOutlined,
  DeleteOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  EnvironmentOutlined,
  VideoCameraOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import dayjs, { Dayjs } from 'dayjs';

import {
  listPlanoFormacoes,
  createPlanoFormacoes,
  updatePlanoFormacoes,
  deletePlanoFormacoes,
  getPlanoFormacoesStats,
  updateFormacaoInline,
  // TODO: Implementar views de Calendario e Resumo por Projeto
  // getPlanoFormacoesCalendario,
  // getPlanoFormacoesResumoProjeto,
  // updateAcompanhamentoInline,
  // updateProvaInline,
} from '../../api/datModule';
import { getMunicipiosOptions, getProjetosOptions, getCoordenadoresOptions } from '../../api/datModule';

const { Title, Text } = Typography;

// ============================================================
// TYPE DEFINITIONS
// ============================================================

interface FormacaoItem {
  id?: number;
  numero: number;
  data: string | null;
  ch: number;
  modalidade: string | null;
  realizada: boolean;
}

interface AcompanhamentoItem {
  id?: number;
  tipo: string;
  data: string | null;
  realizado: boolean;
}

interface ProvaItem {
  id?: number;
  numero: number;
  data: string | null;
  realizada: boolean;
}

interface PlanoFormacaoRecord {
  id: number;
  municipio: number;
  municipio_nome: string;
  municipio_uf: string;
  projeto: number;
  projeto_nome: string;
  coordenador: number | null;
  coordenador_nome: string | null;
  ch_estudo: number | null;
  ch_anual: number;
  observacoes: string | null;
  formacoes_list: FormacaoItem[];
  acompanhamentos_list: AcompanhamentoItem[];
  provas_list: ProvaItem[];
}

interface PlanoFormacaoFormValues {
  municipio: number;
  projeto: number;
  coordenador: number | null;
  ch_estudo: number | null;
  observacoes: string | null;
}

interface FormacaoInlineFormValues {
  data_formacao: Dayjs | null;
  carga_horaria: number | null;
  modalidade: string | null;
  realizada: boolean;
}

interface PlanoFormacoesStats {
  total_planos: number;
  total_formacoes: number;
  total_realizadas: number;
  taxa_realizacao: string;
  ch_total: number;
}

interface MunicipioOption {
  id: number;
  nome: string;
}

interface ProjetoOption {
  id: number;
  nome: string;
}

interface CoordenadorOption {
  id: number;
  nome: string;
}

interface EditingFormacaoState {
  plano: PlanoFormacaoRecord;
  formacao: FormacaoItem;
}


// ============================================================
// CONSTANTS
// ============================================================

const MODALIDADE_OPTIONS = [
  { label: 'Presencial', value: 'presencial', icon: <EnvironmentOutlined />, color: 'green' },
  { label: 'Online', value: 'online', icon: <VideoCameraOutlined />, color: 'blue' },
];

// ============================================================
// COMPONENT
// ============================================================

export default function PlanoFormacoesPage(): JSX.Element {
  // Data state
  const [planos, setPlanos] = useState<PlanoFormacaoRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 15,
    total: 0,
  });
  const [stats, setStats] = useState<PlanoFormacoesStats | null>(null);

  // Options state
  const [municipios, setMunicipios] = useState<MunicipioOption[]>([]);
  const [projetos, setProjetos] = useState<ProjetoOption[]>([]);
  const [coordenadores, setCoordenadores] = useState<CoordenadorOption[]>([]);

  // Filter state
  const [filters, setFilters] = useState({
    search: '',
    uf: undefined,
    municipio: undefined,
    projeto: undefined,
    coordenador: undefined,
  });

  // View mode
  const [viewMode, setViewMode] = useState<'table' | 'calendar' | 'resumo'>('table'); // 'table' | 'calendar' | 'resumo'

  // Modal state
  const [modalVisible, setModalVisible] = useState<boolean>(false);
  const [editingPlano, setEditingPlano] = useState<PlanoFormacaoRecord | null>(null);
  const [form] = Form.useForm<PlanoFormacaoFormValues>();

  // Formacao edit modal
  const [formacaoModalVisible, setFormacaoModalVisible] = useState<boolean>(false);
  const [editingFormacao, setEditingFormacao] = useState<EditingFormacaoState | null>(null);
  const [formacaoForm] = Form.useForm<FormacaoInlineFormValues>();

  // Detail modal
  const [detailModalVisible, setDetailModalVisible] = useState<boolean>(false);
  const [detailPlano, setDetailPlano] = useState<PlanoFormacaoRecord | null>(null);

  // ============================================================
  // DATA LOADING
  // ============================================================

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
        message.error(`Erro ao carregar opcoes: ${(error as Error).message}`);
      }
    };
    loadOptions();
  }, []);

  // Fetch data
  const fetchData = useCallback(async (page = 1) => {
    setLoading(true);
    try {
      const params: any = {
        page,
        page_size: pagination.pageSize,
        ordering: 'municipio__nome,projeto__nome',
      };

      if (filters.search) params.search = filters.search;
      if (filters.uf) params.uf = filters.uf;
      if (filters.municipio) params.municipio = filters.municipio;
      if (filters.projeto) params.projeto = filters.projeto;
      if (filters.coordenador) params.coordenador = filters.coordenador;

      const [data, statsData] = await Promise.all([
        listPlanoFormacoes(params),
        getPlanoFormacoesStats(params),
      ]);

      setPlanos((data as any).results || data || []);
      setPagination((prev) => ({
        ...prev,
        current: page,
        total: data.count || ((data as any).results || data || []).length,
      }));
      setStats(statsData as unknown as PlanoFormacoesStats);
    } catch (error) {
      message.error(`Erro ao carregar dados: ${(error as Error).message}`);
    } finally {
      setLoading(false);
    }
  }, [filters, pagination.pageSize]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // ============================================================
  // HANDLERS
  // ============================================================

  const handleClearFilters = () => {
    setFilters({
      search: '',
      uf: undefined,
      municipio: undefined,
      projeto: undefined,
      coordenador: undefined,
    });
  };

  const handleCreate = () => {
    setEditingPlano(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (record: PlanoFormacaoRecord) => {
    setEditingPlano(record);
    form.setFieldsValue({
      municipio: record.municipio,
      projeto: record.projeto,
      coordenador: record.coordenador,
      ch_estudo: record.ch_estudo,
      observacoes: record.observacoes,
    });
    setModalVisible(true);
  };

  const handleDelete = (record: PlanoFormacaoRecord) => {
    Modal.confirm({
      title: 'Confirmar exclusao',
      content: `Excluir plano de "${record.municipio_nome}" - "${record.projeto_nome}"? Esta acao ira remover todas as formacoes, acompanhamentos e provas associadas.`,
      okText: 'Sim, excluir',
      okType: 'danger',
      cancelText: 'Cancelar',
      onOk: async () => {
        try {
          await deletePlanoFormacoes(record.id);
          message.success('Plano excluido com sucesso');
          fetchData(pagination.current);
        } catch (error) {
          message.error(`Erro ao excluir: ${(error as Error).message}`);
        }
      },
    });
  };

  const handleSave = async (values: PlanoFormacaoFormValues) => {
    try {
      if (editingPlano) {
        await updatePlanoFormacoes(editingPlano.id, values as any);
        message.success('Plano atualizado com sucesso');
      } else {
        await createPlanoFormacoes(values as any);
        message.success('Plano criado com sucesso');
      }
      setModalVisible(false);
      form.resetFields();
      fetchData(pagination.current);
    } catch (error) {
      message.error(`Erro: ${(error as Error).message}`);
    }
  };

  const handleViewDetail = (record: PlanoFormacaoRecord) => {
    setDetailPlano(record);
    setDetailModalVisible(true);
  };

  // Formacao cell click
  const handleFormacaoClick = (plano: PlanoFormacaoRecord, formacao: FormacaoItem) => {
    setEditingFormacao({ plano, formacao });
    formacaoForm.setFieldsValue({
      data_formacao: formacao.data ? dayjs(formacao.data) : null,
      carga_horaria: formacao.ch,
      modalidade: formacao.modalidade,
      realizada: formacao.realizada,
    });
    setFormacaoModalVisible(true);
  };

  const handleFormacaoSave = async (values: FormacaoInlineFormValues) => {
    if (!editingFormacao) return;
    try {
      const payload = {
        ...values,
        data_formacao: values.data_formacao?.format('YYYY-MM-DD') || null,
      };
      await updateFormacaoInline(editingFormacao.plano.id, editingFormacao.formacao.numero, payload);
      message.success('Formacao atualizada');
      setFormacaoModalVisible(false);
      fetchData(pagination.current);
    } catch (error) {
      message.error(`Erro: ${(error as Error).message}`);
    }
  };

  // ============================================================
  // RENDER HELPERS
  // ============================================================

  const renderFormacaoCell = (plano: PlanoFormacaoRecord, formacao: FormacaoItem | undefined) => {
    if (!formacao) return <Text type="secondary">-</Text>;

    const hasData = formacao.data;
    const modalidadeConfig = MODALIDADE_OPTIONS.find((m) => m.value === formacao.modalidade);

    return (
      <div
        style={{ textAlign: 'center', cursor: 'pointer', padding: 4 }}
        onClick={() => handleFormacaoClick(plano, formacao)}
      >
        {hasData ? (
          <>
            <div style={{ fontSize: 12, fontWeight: 500 }}>
              {dayjs(formacao.data).format('DD/MM')}
            </div>
            <Tag
              color={modalidadeConfig?.color || 'default'}
              style={{ fontSize: 10, margin: 0 }}
            >
              {formacao.ch}h {formacao.modalidade === 'online' ? 'Onl.' : 'Pres.'}
            </Tag>
            {formacao.realizada && (
              <CheckCircleOutlined className="text-green-500 text-[10px] ml-0.5" />
            )}
          </>
        ) : (
          <Text type="secondary" style={{ fontSize: 11 }}>-</Text>
        )}
      </div>
    );
  };

  const renderAcompanhamentoCell = (plano: PlanoFormacaoRecord, index: number) => {
    const acomp = plano.acompanhamentos_list?.[index];
    if (!acomp) return <Text type="secondary">-</Text>;

    return (
      <div style={{ textAlign: 'center' }}>
        {acomp.realizado ? (
          <CheckCircleOutlined className="text-green-500" />
        ) : (
          <ClockCircleOutlined className="text-gray-400" />
        )}
        {acomp.data && (
          <div style={{ fontSize: 10 }}>{dayjs(acomp.data).format('DD/MM')}</div>
        )}
      </div>
    );
  };

  const renderProvaCell = (plano: PlanoFormacaoRecord, index: number) => {
    const prova = plano.provas_list?.[index];
    if (!prova) return <Text type="secondary">-</Text>;

    return (
      <div style={{ textAlign: 'center' }}>
        {prova.realizada ? (
          <CheckCircleOutlined className="text-green-500" />
        ) : (
          <ClockCircleOutlined className="text-gray-400" />
        )}
        {prova.data && (
          <div style={{ fontSize: 10 }}>{dayjs(prova.data).format('DD/MM')}</div>
        )}
      </div>
    );
  };

  // ============================================================
  // TABLE COLUMNS (memoized §16 Epic #459)
  // ============================================================

  const columns = useMemo(() => [
    {
      title: 'Municipio',
      dataIndex: 'municipio_nome',
      key: 'municipio',
      width: 150,
      fixed: 'left' as const,
      render: (nome: string, record: PlanoFormacaoRecord) => (
        <div>
          <Text strong>{nome}</Text>
          <div style={{ fontSize: 11, color: '#888' }}>{record.municipio_uf}</div>
        </div>
      ),
    },
    {
      title: 'Coord.',
      dataIndex: 'coordenador_nome',
      key: 'coordenador',
      width: 100,
      fixed: 'left' as const,
      ellipsis: true,
      render: (nome: string | null) => nome || <Text type="secondary">-</Text>,
    },
    {
      title: 'Projeto',
      dataIndex: 'projeto_nome',
      key: 'projeto',
      width: 150,
      fixed: 'left' as const,
      ellipsis: true,
    },
    // 15 formacoes columns
    ...Array.from({ length: 15 }, (_, i) => ({
      title: `F${i + 1}`,
      key: `f${i + 1}`,
      width: 70,
      align: 'center' as const,
      render: (_: unknown, record: PlanoFormacaoRecord) => {
        const formacao = record.formacoes_list?.find((f) => f.numero === i + 1);
        return renderFormacaoCell(record, formacao);
      },
    })),
    {
      title: 'CH',
      dataIndex: 'ch_anual',
      key: 'ch_anual',
      width: 60,
      align: 'center' as const,
      render: (ch: number) => <Text strong>{ch}h</Text>,
    },
    {
      title: 'A1',
      key: 'a1',
      width: 50,
      align: 'center' as const,
      render: (_: unknown, record: PlanoFormacaoRecord) => renderAcompanhamentoCell(record, 0),
    },
    {
      title: 'A2',
      key: 'a2',
      width: 50,
      align: 'center' as const,
      render: (_: unknown, record: PlanoFormacaoRecord) => renderAcompanhamentoCell(record, 1),
    },
    {
      title: 'P1',
      key: 'p1',
      width: 50,
      align: 'center' as const,
      render: (_: unknown, record: PlanoFormacaoRecord) => renderProvaCell(record, 0),
    },
    {
      title: 'P2',
      key: 'p2',
      width: 50,
      align: 'center' as const,
      render: (_: unknown, record: PlanoFormacaoRecord) => renderProvaCell(record, 1),
    },
    {
      title: 'P3',
      key: 'p3',
      width: 50,
      align: 'center' as const,
      render: (_: unknown, record: PlanoFormacaoRecord) => renderProvaCell(record, 2),
    },
    {
      title: 'Acoes',
      key: 'acoes',
      width: 100,
      fixed: 'right' as const,
      render: (_: unknown, record: PlanoFormacaoRecord) => (
        <Space size="small">
          <Tooltip title="Ver detalhes">
            <Button
              type="text"
              size="small"
              icon={<InfoCircleOutlined />}
              onClick={() => handleViewDetail(record)}
              aria-label="Ver detalhes do plano"
            />
          </Tooltip>
          <Tooltip title="Editar">
            <Button
              type="text"
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
              aria-label="Editar plano de formações"
            />
          </Tooltip>
          <Tooltip title="Excluir">
            <Button
              type="text"
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(record)}
              aria-label="Excluir plano de formações"
            />
          </Tooltip>
        </Space>
      ),
    },
  ], []);

  // ============================================================
  // RENDER
  // ============================================================

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6 flex justify-between items-center">
        <div>
          <Title level={3} className="m-0">Plano de Formacoes</Title>
          <Text type="secondary">Gestao do plano anual de formacoes por municipio e projeto</Text>
        </div>
        <Space>
          <Button.Group>
            <Button
              type={viewMode === 'table' ? 'primary' : 'default'}
              icon={<TableOutlined />}
              onClick={() => setViewMode('table')}
            >
              Tabela
            </Button>
            <Button
              type={viewMode === 'calendar' ? 'primary' : 'default'}
              icon={<CalendarOutlined />}
              onClick={() => setViewMode('calendar')}
            >
              Calendario
            </Button>
            <Button
              type={viewMode === 'resumo' ? 'primary' : 'default'}
              icon={<ProjectOutlined />}
              onClick={() => setViewMode('resumo')}
            >
              Resumo
            </Button>
          </Button.Group>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            Novo Plano
          </Button>
        </Space>
      </div>

      {/* Stats Cards */}
      {stats && (
        <Row gutter={16} className="mb-4">
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="Planos Ativos"
                value={stats.total_planos}
                prefix={<ProjectOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title={`Formações ${new Date().getFullYear()}`}
                value={stats.total_formacoes}
                prefix={<CalendarOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="Realizadas"
                value={stats.total_realizadas}
                suffix={`(${stats.taxa_realizacao}%)`}
                valueStyle={{ color: '#52c41a' }}
                prefix={<CheckCircleOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="CH Total"
                value={stats.ch_total}
                suffix="h"
                prefix={<ClockCircleOutlined />}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* Filters */}
      <Card className="mb-4" bodyStyle={{ paddingBottom: 12 }}>
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} md={6} lg={4}>
            <div className="mb-1">
              <Text type="secondary" style={{ fontSize: 12, textTransform: 'uppercase' }}>Buscar</Text>
            </div>
            <Input.Search
              placeholder="Municipio, projeto..."
              allowClear
              value={filters.search}
              onChange={(e) => setFilters((prev: any) => ({ ...prev, search: e.target.value }))}
              onSearch={() => fetchData(1)}
            />
          </Col>
          <Col xs={12} sm={6} md={4} lg={3}>
            <div className="mb-1">
              <Text type="secondary" style={{ fontSize: 12, textTransform: 'uppercase' }}>Municipio</Text>
            </div>
            <Select
              style={{ width: '100%' }}
              placeholder="Todos"
              allowClear
              showSearch
              optionFilterProp="label"
              value={filters.municipio}
              onChange={(val) => setFilters((prev: any) => ({ ...prev, municipio: val }))}
              options={municipios.map((m) => ({ label: m.nome, value: m.id }))}
            />
          </Col>
          <Col xs={12} sm={6} md={4} lg={3}>
            <div className="mb-1">
              <Text type="secondary" style={{ fontSize: 12, textTransform: 'uppercase' }}>Projeto</Text>
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
              <Text type="secondary" style={{ fontSize: 12, textTransform: 'uppercase' }}>Coordenador</Text>
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
        </Row>
        <Divider className="my-4 mb-3" />
        <div className="flex justify-end gap-2">
          <Button icon={<ClearOutlined />} onClick={handleClearFilters}>Limpar</Button>
          <Button icon={<ReloadOutlined />} onClick={() => fetchData(1)} loading={loading}>Atualizar</Button>
          <Button type="primary" icon={<FilterOutlined />} onClick={() => fetchData(1)}>Filtrar</Button>
        </div>
      </Card>

      {/* Main Content */}
      {viewMode === 'table' && (
        <Card>
          <Table
            columns={columns as any}
            dataSource={planos}
            rowKey="id"
            loading={loading}
            scroll={{ x: 2200 }}
            pagination={{
              ...pagination,
              showSizeChanger: true,
              showTotal: (total, range) => `Mostrando ${range[0]} a ${range[1]} de ${total}`,
              onChange: (page, pageSize) => {
                setPagination((prev) => ({ ...prev, current: page, pageSize }));
                fetchData(page);
              },
            }}
            size="small"
          />
        </Card>
      )}

      {viewMode === 'calendar' && (
        <Card>
          <Text type="secondary">Visualizacao de calendario em desenvolvimento...</Text>
        </Card>
      )}

      {viewMode === 'resumo' && (
        <Card>
          <Text type="secondary">Resumo por projeto em desenvolvimento...</Text>
        </Card>
      )}

      {/* Create/Edit Modal */}
      <Modal
        title={editingPlano ? 'Editar Plano' : 'Novo Plano'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={
          <Space>
            <Button onClick={() => setModalVisible(false)}>Cancelar</Button>
            <Button type="primary" onClick={() => form.submit()}>Salvar</Button>
          </Space>
        }
        width={600}
      >
        <Form form={form} layout="vertical" onFinish={handleSave}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="municipio"
                label="Municipio"
                rules={[{ required: true, message: 'Selecione o municipio' }]}
              >
                <Select
                  placeholder="Selecione..."
                  showSearch
                  optionFilterProp="label"
                  disabled={!!editingPlano}
                  options={municipios.map((m) => ({ label: m.nome, value: m.id }))}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="projeto"
                label="Projeto"
                rules={[{ required: true, message: 'Selecione o projeto' }]}
              >
                <Select
                  placeholder="Selecione..."
                  showSearch
                  optionFilterProp="label"
                  disabled={!!editingPlano}
                  options={projetos.map((p) => ({ label: p.nome, value: p.id }))}
                />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="coordenador" label="Coordenador">
                <Select
                  placeholder="Selecione..."
                  showSearch
                  allowClear
                  optionFilterProp="label"
                  options={coordenadores.map((c) => ({ label: c.nome, value: c.id }))}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="ch_estudo" label="CH Estudo (horas)">
                <InputNumber style={{ width: '100%' }} min={0} step={0.5} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="observacoes" label="Observacoes">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>

      {/* Formacao Edit Modal */}
      <Modal
        title={`Editar Formacao ${editingFormacao?.formacao?.numero || ''}`}
        open={formacaoModalVisible}
        onCancel={() => setFormacaoModalVisible(false)}
        footer={
          <Space>
            <Button onClick={() => setFormacaoModalVisible(false)}>Cancelar</Button>
            <Button type="primary" onClick={() => formacaoForm.submit()}>Salvar</Button>
          </Space>
        }
        width={400}
      >
        <Form form={formacaoForm} layout="vertical" onFinish={handleFormacaoSave}>
          <Form.Item name="data_formacao" label="Data">
            <DatePicker style={{ width: '100%' }} format="DD/MM/YYYY" />
          </Form.Item>
          <Form.Item name="carga_horaria" label="Carga Horaria (horas)">
            <InputNumber style={{ width: '100%' }} min={0.5} max={24} step={0.5} />
          </Form.Item>
          <Form.Item name="modalidade" label="Modalidade">
            <Select
              options={MODALIDADE_OPTIONS.map((m) => ({ label: m.label, value: m.value }))}
            />
          </Form.Item>
          <Form.Item name="realizada" valuePropName="checked">
            <Checkbox>Realizada</Checkbox>
          </Form.Item>
        </Form>
      </Modal>

      {/* Detail Modal */}
      <Modal
        title={`Detalhes: ${detailPlano?.municipio_nome} - ${detailPlano?.projeto_nome}`}
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={<Button onClick={() => setDetailModalVisible(false)}>Fechar</Button>}
        width={800}
      >
        {detailPlano && (
          <Tabs
            items={[
              {
                key: 'formacoes',
                label: 'Formacoes',
                children: (
                  <Table
                    dataSource={detailPlano.formacoes_list || []}
                    rowKey="id"
                    size="small"
                    pagination={false}
                    columns={[
                      { title: '#', dataIndex: 'numero', width: 50 },
                      { title: 'Data', dataIndex: 'data', render: (d) => d ? dayjs(d).format('DD/MM/YYYY') : '-' },
                      { title: 'CH', dataIndex: 'ch', render: (v) => `${v}h` },
                      { title: 'Modalidade', dataIndex: 'modalidade', render: (m) => m === 'online' ? 'Online' : 'Presencial' },
                      { title: 'Realizada', dataIndex: 'realizada', render: (v) => v ? <CheckCircleOutlined className="text-green-500" /> : '-' },
                    ]}
                  />
                ),
              },
              {
                key: 'acompanhamentos',
                label: 'Acompanhamentos',
                children: (
                  <Table
                    dataSource={detailPlano.acompanhamentos_list || []}
                    rowKey="id"
                    size="small"
                    pagination={false}
                    columns={[
                      { title: 'Tipo', dataIndex: 'tipo', render: (t) => t === 'primeiro' ? '1o Acomp.' : '2o Acomp.' },
                      { title: 'Data', dataIndex: 'data', render: (d) => d ? dayjs(d).format('DD/MM/YYYY') : '-' },
                      { title: 'Realizado', dataIndex: 'realizado', render: (v) => v ? <CheckCircleOutlined className="text-green-500" /> : '-' },
                    ]}
                  />
                ),
              },
              {
                key: 'provas',
                label: 'Provas',
                children: (
                  <Table
                    dataSource={detailPlano.provas_list || []}
                    rowKey="id"
                    size="small"
                    pagination={false}
                    columns={[
                      { title: '#', dataIndex: 'numero', width: 50 },
                      { title: 'Data', dataIndex: 'data', render: (d) => d ? dayjs(d).format('DD/MM/YYYY') : '-' },
                      { title: 'Realizada', dataIndex: 'realizada', render: (v) => v ? <CheckCircleOutlined className="text-green-500" /> : '-' },
                    ]}
                  />
                ),
              },
            ]}
          />
        )}
      </Modal>
    </div>
  );
}
