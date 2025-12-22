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

import { useState, useEffect, useCallback } from 'react';
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
import dayjs from 'dayjs';

import {
  listPlanoFormacoes,
  createPlanoFormacoes,
  updatePlanoFormacoes,
  deletePlanoFormacoes,
  getPlanoFormacoesStats,
  getPlanoFormacoesCalendario,
  getPlanoFormacoesResumoProjeto,
  updateFormacaoInline,
  updateAcompanhamentoInline,
  updateProvaInline,
} from '../../api/datModule';
import { getMunicipiosOptions, getProjetosOptions, getCoordenadoresOptions } from '../../api/datModule';

const { Title, Text } = Typography;

// ============================================================
// CONSTANTS
// ============================================================

const MODALIDADE_OPTIONS = [
  { label: 'Presencial', value: 'presencial', icon: <EnvironmentOutlined />, color: 'green' },
  { label: 'Online', value: 'online', icon: <VideoCameraOutlined />, color: 'blue' },
];

const STATUS_OPTIONS = [
  { label: 'Agendada', value: 'agendada', color: 'blue' },
  { label: 'Realizada', value: 'realizada', color: 'green' },
  { label: 'Cancelada', value: 'cancelada', color: 'red' },
  { label: 'Reagendada', value: 'reagendada', color: 'purple' },
];

// ============================================================
// COMPONENT
// ============================================================

export default function PlanoFormacoesPage() {
  // Data state
  const [planos, setPlanos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 15,
    total: 0,
  });
  const [stats, setStats] = useState(null);

  // Options state
  const [municipios, setMunicipios] = useState([]);
  const [projetos, setProjetos] = useState([]);
  const [coordenadores, setCoordenadores] = useState([]);

  // Filter state
  const [filters, setFilters] = useState({
    search: '',
    uf: undefined,
    municipio: undefined,
    projeto: undefined,
    coordenador: undefined,
  });

  // View mode
  const [viewMode, setViewMode] = useState('table'); // 'table' | 'calendar' | 'resumo'

  // Modal state
  const [modalVisible, setModalVisible] = useState(false);
  const [editingPlano, setEditingPlano] = useState(null);
  const [form] = Form.useForm();

  // Formacao edit modal
  const [formacaoModalVisible, setFormacaoModalVisible] = useState(false);
  const [editingFormacao, setEditingFormacao] = useState(null);
  const [formacaoForm] = Form.useForm();

  // Detail modal
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [detailPlano, setDetailPlano] = useState(null);

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
        setMunicipios(munData.results || munData || []);
        setProjetos(projData.results || projData || []);
        setCoordenadores(coordData.results || coordData || []);
      } catch (error) {
        message.error(`Erro ao carregar opcoes: ${error.message}`);
      }
    };
    loadOptions();
  }, []);

  // Fetch data
  const fetchData = useCallback(async (page = 1) => {
    setLoading(true);
    try {
      const params = {
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

      setPlanos(data.results || data || []);
      setPagination((prev) => ({
        ...prev,
        current: page,
        total: data.count || (data.results || data || []).length,
      }));
      setStats(statsData);
    } catch (error) {
      message.error(`Erro ao carregar dados: ${error.message}`);
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

  const handleEdit = (record) => {
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

  const handleDelete = (record) => {
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
          message.error(`Erro ao excluir: ${error.message}`);
        }
      },
    });
  };

  const handleSave = async (values) => {
    try {
      if (editingPlano) {
        await updatePlanoFormacoes(editingPlano.id, values);
        message.success('Plano atualizado com sucesso');
      } else {
        await createPlanoFormacoes(values);
        message.success('Plano criado com sucesso');
      }
      setModalVisible(false);
      form.resetFields();
      fetchData(pagination.current);
    } catch (error) {
      message.error(`Erro: ${error.message}`);
    }
  };

  const handleViewDetail = (record) => {
    setDetailPlano(record);
    setDetailModalVisible(true);
  };

  // Formacao cell click
  const handleFormacaoClick = (plano, formacao) => {
    setEditingFormacao({ plano, formacao });
    formacaoForm.setFieldsValue({
      data_formacao: formacao.data ? dayjs(formacao.data) : null,
      carga_horaria: formacao.ch,
      modalidade: formacao.modalidade,
      realizada: formacao.realizada,
    });
    setFormacaoModalVisible(true);
  };

  const handleFormacaoSave = async (values) => {
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
      message.error(`Erro: ${error.message}`);
    }
  };

  // ============================================================
  // RENDER HELPERS
  // ============================================================

  const renderFormacaoCell = (plano, formacao) => {
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
              <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 10, marginLeft: 2 }} />
            )}
          </>
        ) : (
          <Text type="secondary" style={{ fontSize: 11 }}>-</Text>
        )}
      </div>
    );
  };

  const renderAcompanhamentoCell = (plano, index) => {
    const acomp = plano.acompanhamentos_list?.[index];
    if (!acomp) return <Text type="secondary">-</Text>;

    return (
      <div style={{ textAlign: 'center' }}>
        {acomp.realizado ? (
          <CheckCircleOutlined style={{ color: '#52c41a' }} />
        ) : (
          <ClockCircleOutlined style={{ color: '#999' }} />
        )}
        {acomp.data && (
          <div style={{ fontSize: 10 }}>{dayjs(acomp.data).format('DD/MM')}</div>
        )}
      </div>
    );
  };

  const renderProvaCell = (plano, index) => {
    const prova = plano.provas_list?.[index];
    if (!prova) return <Text type="secondary">-</Text>;

    return (
      <div style={{ textAlign: 'center' }}>
        {prova.realizada ? (
          <CheckCircleOutlined style={{ color: '#52c41a' }} />
        ) : (
          <ClockCircleOutlined style={{ color: '#999' }} />
        )}
        {prova.data && (
          <div style={{ fontSize: 10 }}>{dayjs(prova.data).format('DD/MM')}</div>
        )}
      </div>
    );
  };

  // ============================================================
  // TABLE COLUMNS
  // ============================================================

  const columns = [
    {
      title: 'Municipio',
      dataIndex: 'municipio_nome',
      key: 'municipio',
      width: 150,
      fixed: 'left',
      render: (nome, record) => (
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
      fixed: 'left',
      ellipsis: true,
      render: (nome) => nome || <Text type="secondary">-</Text>,
    },
    {
      title: 'Projeto',
      dataIndex: 'projeto_nome',
      key: 'projeto',
      width: 150,
      fixed: 'left',
      ellipsis: true,
    },
    // 15 formacoes columns
    ...Array.from({ length: 15 }, (_, i) => ({
      title: `F${i + 1}`,
      key: `f${i + 1}`,
      width: 70,
      align: 'center',
      render: (_, record) => {
        const formacao = record.formacoes_list?.find((f) => f.numero === i + 1);
        return renderFormacaoCell(record, formacao);
      },
    })),
    {
      title: 'CH',
      dataIndex: 'ch_anual',
      key: 'ch_anual',
      width: 60,
      align: 'center',
      render: (ch) => <Text strong>{ch}h</Text>,
    },
    {
      title: 'A1',
      key: 'a1',
      width: 50,
      align: 'center',
      render: (_, record) => renderAcompanhamentoCell(record, 0),
    },
    {
      title: 'A2',
      key: 'a2',
      width: 50,
      align: 'center',
      render: (_, record) => renderAcompanhamentoCell(record, 1),
    },
    {
      title: 'P1',
      key: 'p1',
      width: 50,
      align: 'center',
      render: (_, record) => renderProvaCell(record, 0),
    },
    {
      title: 'P2',
      key: 'p2',
      width: 50,
      align: 'center',
      render: (_, record) => renderProvaCell(record, 1),
    },
    {
      title: 'P3',
      key: 'p3',
      width: 50,
      align: 'center',
      render: (_, record) => renderProvaCell(record, 2),
    },
    {
      title: 'Acoes',
      key: 'acoes',
      width: 100,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="Ver detalhes">
            <Button
              type="text"
              size="small"
              icon={<InfoCircleOutlined />}
              onClick={() => handleViewDetail(record)}
            />
          </Tooltip>
          <Tooltip title="Editar">
            <Button
              type="text"
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          <Tooltip title="Excluir">
            <Button
              type="text"
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(record)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  // ============================================================
  // RENDER
  // ============================================================

  return (
    <div style={{ padding: 24 }}>
      {/* Header */}
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <Title level={3} style={{ margin: 0 }}>Plano de Formacoes</Title>
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
        <Row gutter={16} style={{ marginBottom: 16 }}>
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
                title="Formacoes 2025"
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
      <Card style={{ marginBottom: 16 }} bodyStyle={{ paddingBottom: 12 }}>
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} md={6} lg={4}>
            <div style={{ marginBottom: 4 }}>
              <Text type="secondary" style={{ fontSize: 12, textTransform: 'uppercase' }}>Buscar</Text>
            </div>
            <Input.Search
              placeholder="Municipio, projeto..."
              allowClear
              value={filters.search}
              onChange={(e) => setFilters((prev) => ({ ...prev, search: e.target.value }))}
              onSearch={() => fetchData(1)}
            />
          </Col>
          <Col xs={12} sm={6} md={4} lg={3}>
            <div style={{ marginBottom: 4 }}>
              <Text type="secondary" style={{ fontSize: 12, textTransform: 'uppercase' }}>Municipio</Text>
            </div>
            <Select
              style={{ width: '100%' }}
              placeholder="Todos"
              allowClear
              showSearch
              optionFilterProp="label"
              value={filters.municipio}
              onChange={(val) => setFilters((prev) => ({ ...prev, municipio: val }))}
              options={municipios.map((m) => ({ label: m.nome, value: m.id }))}
            />
          </Col>
          <Col xs={12} sm={6} md={4} lg={3}>
            <div style={{ marginBottom: 4 }}>
              <Text type="secondary" style={{ fontSize: 12, textTransform: 'uppercase' }}>Projeto</Text>
            </div>
            <Select
              style={{ width: '100%' }}
              placeholder="Todos"
              allowClear
              showSearch
              optionFilterProp="label"
              value={filters.projeto}
              onChange={(val) => setFilters((prev) => ({ ...prev, projeto: val }))}
              options={projetos.map((p) => ({ label: p.nome, value: p.id }))}
            />
          </Col>
          <Col xs={12} sm={6} md={4} lg={3}>
            <div style={{ marginBottom: 4 }}>
              <Text type="secondary" style={{ fontSize: 12, textTransform: 'uppercase' }}>Coordenador</Text>
            </div>
            <Select
              style={{ width: '100%' }}
              placeholder="Todos"
              allowClear
              showSearch
              optionFilterProp="label"
              value={filters.coordenador}
              onChange={(val) => setFilters((prev) => ({ ...prev, coordenador: val }))}
              options={coordenadores.map((c) => ({ label: c.nome, value: c.id }))}
            />
          </Col>
        </Row>
        <Divider style={{ margin: '16px 0 12px' }} />
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
          <Button icon={<ClearOutlined />} onClick={handleClearFilters}>Limpar</Button>
          <Button icon={<ReloadOutlined />} onClick={() => fetchData(1)} loading={loading}>Atualizar</Button>
          <Button type="primary" icon={<FilterOutlined />} onClick={() => fetchData(1)}>Filtrar</Button>
        </div>
      </Card>

      {/* Main Content */}
      {viewMode === 'table' && (
        <Card>
          <Table
            columns={columns}
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
                      { title: 'Realizada', dataIndex: 'realizada', render: (v) => v ? <CheckCircleOutlined style={{ color: '#52c41a' }} /> : '-' },
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
                      { title: 'Realizado', dataIndex: 'realizado', render: (v) => v ? <CheckCircleOutlined style={{ color: '#52c41a' }} /> : '-' },
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
                      { title: 'Realizada', dataIndex: 'realizada', render: (v) => v ? <CheckCircleOutlined style={{ color: '#52c41a' }} /> : '-' },
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
