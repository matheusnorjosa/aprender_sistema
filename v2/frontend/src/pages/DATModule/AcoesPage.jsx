/**
 * DAT Module - Gestão de Ações
 *
 * Interface de gestão do ciclo de vida de projetos por município.
 * Fluxo: Carta → Contato → Reunião → Entrega
 *
 * Baseado na análise da planilha de controle - aba AÇÕES
 * 688 registros, 103 municípios, 88 projetos, 28 coordenadores
 */

import { useState, useEffect, useCallback } from 'react';
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
  DatePicker,
  Tooltip,
  Divider,
  Row,
  Col,
  Statistic,
  Progress,
} from 'antd';
import {
  ReloadOutlined,
  EditOutlined,
  PlusOutlined,
  DeleteOutlined,
  DownloadOutlined,
  FilterOutlined,
  ClearOutlined,
  CheckCircleFilled,
  ClockCircleFilled,
  ExclamationCircleFilled,
  MinusCircleFilled,
  MailOutlined,
  PhoneOutlined,
  TeamOutlined,
  SendOutlined,
  RocketOutlined,
} from '@ant-design/icons';
import {
  listAcoes,
  createAcao,
  updateAcao,
  deleteAcao,
  getAcoesStats,
  getMunicipiosOptions,
  getProjetosOptions,
  getCoordenadoresOptions,
} from '../../api/datModule';
import dayjs from 'dayjs';

const { Title, Text } = Typography;

// Status options para cada etapa
const STATUS_OPTIONS = [
  { label: 'Pendente', value: 'pendente' },
  { label: 'Em Andamento', value: 'em_andamento' },
  { label: 'Concluído', value: 'concluido' },
  { label: 'N/A', value: 'na' },
];

// Cores de status
const STATUS_COLORS = {
  pendente: 'orange',
  em_andamento: 'blue',
  concluido: 'green',
  na: 'default',
};

// UF options (Brazilian states)
const UF_OPTIONS = [
  'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
  'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN',
  'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO',
].map((uf) => ({ label: uf, value: uf }));

export default function AcoesPage() {
  const [acoes, setAcoes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 15, total: 0 });
  const [stats, setStats] = useState(null);

  // Filter states
  const [filters, setFilters] = useState({
    search: '',
    uf: undefined,
    municipio: undefined,
    projeto: undefined,
    coordenador: undefined,
    status_geral: undefined,
  });

  // Options for dropdowns
  const [municipios, setMunicipios] = useState([]);
  const [projetos, setProjetos] = useState([]);
  const [coordenadores, setCoordenadores] = useState([]);

  // Modal states
  const [modalVisible, setModalVisible] = useState(false);
  const [editingAcao, setEditingAcao] = useState(null);

  const [form] = Form.useForm();

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
        message.error(`Erro ao carregar opções: ${error.message}`);
      }
    };
    loadOptions();
  }, []);

  // Fetch data with filters
  const fetchData = useCallback(async (page = 1) => {
    setLoading(true);
    try {
      const params = {
        page,
        page_size: pagination.pageSize,
        ordering: '-updated_at',
      };

      // Apply filters
      if (filters.search) params.search = filters.search;
      if (filters.uf) params.uf = filters.uf;
      if (filters.municipio) params.municipio_id = filters.municipio;
      if (filters.projeto) params.projeto_id = filters.projeto;
      if (filters.coordenador) params.coordenador_id = filters.coordenador;
      if (filters.status_geral) params.status_geral = filters.status_geral;

      const [data, statsData] = await Promise.all([
        listAcoes(params),
        getAcoesStats(params),
      ]);

      setAcoes(data.results || data || []);
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

  // Clear all filters
  const handleClearFilters = () => {
    setFilters({
      search: '',
      uf: undefined,
      municipio: undefined,
      projeto: undefined,
      coordenador: undefined,
      status_geral: undefined,
    });
  };

  // CRUD handlers
  const handleCreate = () => {
    setEditingAcao(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (record) => {
    setEditingAcao(record);
    form.setFieldsValue({
      ...record,
      data_carta: record.data_carta ? dayjs(record.data_carta) : null,
      data_contato: record.data_contato ? dayjs(record.data_contato) : null,
      data_reuniao: record.data_reuniao ? dayjs(record.data_reuniao) : null,
      data_entrega: record.data_entrega ? dayjs(record.data_entrega) : null,
    });
    setModalVisible(true);
  };

  const handleSave = async (values) => {
    try {
      const payload = {
        ...values,
        data_carta: values.data_carta ? values.data_carta.format('YYYY-MM-DD') : null,
        data_contato: values.data_contato ? values.data_contato.format('YYYY-MM-DD') : null,
        data_reuniao: values.data_reuniao ? values.data_reuniao.format('YYYY-MM-DD') : null,
        data_entrega: values.data_entrega ? values.data_entrega.format('YYYY-MM-DD') : null,
      };

      if (editingAcao) {
        await updateAcao(editingAcao.id, payload);
        message.success('Ação atualizada com sucesso');
      } else {
        await createAcao(payload);
        message.success('Ação criada com sucesso');
      }
      setModalVisible(false);
      form.resetFields();
      fetchData(pagination.current);
    } catch (error) {
      message.error(`Erro: ${error.message}`);
    }
  };

  const handleDelete = (record) => {
    Modal.confirm({
      title: 'Confirmar exclusão',
      content: `Excluir ação "${record.projeto_nome}" em "${record.municipio_nome}"?`,
      okText: 'Sim, excluir',
      okType: 'danger',
      cancelText: 'Cancelar',
      onOk: async () => {
        try {
          await deleteAcao(record.id);
          message.success('Ação excluída com sucesso');
          fetchData(pagination.current);
        } catch (error) {
          message.error(`Erro ao excluir: ${error.message}`);
        }
      },
    });
  };

  // Status icon renderer
  const renderStatusIcon = (status) => {
    switch (status) {
      case 'concluido':
        return <CheckCircleFilled style={{ color: '#52c41a', fontSize: 18 }} />;
      case 'em_andamento':
        return <ClockCircleFilled style={{ color: '#1890ff', fontSize: 18 }} />;
      case 'pendente':
        return <ExclamationCircleFilled style={{ color: '#faad14', fontSize: 18 }} />;
      case 'na':
        return <MinusCircleFilled style={{ color: '#999', fontSize: 18 }} />;
      default:
        return <MinusCircleFilled style={{ color: '#999', fontSize: 18 }} />;
    }
  };

  // Calculate progress based on status
  const calculateProgress = (record) => {
    const etapas = [
      record.status_carta,
      record.status_contato,
      record.status_reuniao,
      record.status_entrega,
    ];
    const concluidas = etapas.filter((s) => s === 'concluido').length;
    return Math.round((concluidas / 4) * 100);
  };

  // Table columns
  const columns = [
    {
      title: 'Município - UF',
      key: 'municipio_uf',
      width: 180,
      fixed: 'left',
      render: (_, record) => (
        <Text strong>
          {record.municipio_nome} - {record.municipio_uf}
        </Text>
      ),
    },
    {
      title: 'Projeto',
      dataIndex: 'projeto_nome',
      key: 'projeto',
      width: 150,
      render: (nome) => <Tag color="blue">{nome}</Tag>,
    },
    {
      title: 'Coordenador',
      dataIndex: 'coordenador_nome',
      key: 'coordenador',
      width: 150,
      ellipsis: true,
    },
    {
      title: 'Área',
      dataIndex: 'area',
      key: 'area',
      width: 100,
    },
    {
      title: (
        <Tooltip title="Carta Enviada">
          <Space>
            <MailOutlined />
            Carta
          </Space>
        </Tooltip>
      ),
      key: 'carta',
      width: 100,
      align: 'center',
      render: (_, record) => (
        <Space direction="vertical" size={0} align="center">
          {renderStatusIcon(record.status_carta)}
          <Text type="secondary" style={{ fontSize: 11 }}>
            {record.data_carta ? dayjs(record.data_carta).format('DD/MM') : '-'}
          </Text>
        </Space>
      ),
    },
    {
      title: (
        <Tooltip title="Contato Realizado">
          <Space>
            <PhoneOutlined />
            Contato
          </Space>
        </Tooltip>
      ),
      key: 'contato',
      width: 100,
      align: 'center',
      render: (_, record) => (
        <Space direction="vertical" size={0} align="center">
          {renderStatusIcon(record.status_contato)}
          <Text type="secondary" style={{ fontSize: 11 }}>
            {record.data_contato ? dayjs(record.data_contato).format('DD/MM') : '-'}
          </Text>
        </Space>
      ),
    },
    {
      title: (
        <Tooltip title="Reunião Realizada">
          <Space>
            <TeamOutlined />
            Reunião
          </Space>
        </Tooltip>
      ),
      key: 'reuniao',
      width: 100,
      align: 'center',
      render: (_, record) => (
        <Space direction="vertical" size={0} align="center">
          {renderStatusIcon(record.status_reuniao)}
          <Text type="secondary" style={{ fontSize: 11 }}>
            {record.data_reuniao ? dayjs(record.data_reuniao).format('DD/MM') : '-'}
          </Text>
        </Space>
      ),
    },
    {
      title: (
        <Tooltip title="Entrega Concluída">
          <Space>
            <SendOutlined />
            Entrega
          </Space>
        </Tooltip>
      ),
      key: 'entrega',
      width: 100,
      align: 'center',
      render: (_, record) => (
        <Space direction="vertical" size={0} align="center">
          {renderStatusIcon(record.status_entrega)}
          <Text type="secondary" style={{ fontSize: 11 }}>
            {record.data_entrega ? dayjs(record.data_entrega).format('DD/MM') : '-'}
          </Text>
        </Space>
      ),
    },
    {
      title: 'Progresso',
      key: 'progresso',
      width: 120,
      render: (_, record) => {
        const progress = calculateProgress(record);
        return (
          <Progress
            percent={progress}
            size="small"
            status={progress === 100 ? 'success' : 'active'}
            strokeColor={progress === 100 ? '#52c41a' : '#1890ff'}
          />
        );
      },
    },
    {
      title: 'Observações',
      dataIndex: 'observacoes',
      key: 'observacoes',
      width: 200,
      ellipsis: { showTitle: false },
      render: (val) => (
        <Tooltip title={val}>
          <Text type="secondary">{val || '-'}</Text>
        </Tooltip>
      ),
    },
    {
      title: 'Ações',
      key: 'acoes',
      width: 100,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
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

  return (
    <div style={{ padding: '24px', background: '#f0f2f5', minHeight: 'calc(100vh - 64px)' }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
          <div>
            <Title level={3} style={{ margin: 0 }}>
              <RocketOutlined style={{ marginRight: 8 }} />
              Gestão de Ações
            </Title>
            <Text type="secondary">
              Acompanhamento do ciclo de vida de projetos: Carta → Contato → Reunião → Entrega
            </Text>
          </div>
          <Space>
            <Button icon={<DownloadOutlined />}>Exportar</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              Nova Ação
            </Button>
          </Space>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="Total de Ações"
                value={stats.total || pagination.total}
                prefix={<RocketOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="Cartas Enviadas"
                value={stats.cartas_enviadas || 0}
                valueStyle={{ color: '#1890ff' }}
                prefix={<MailOutlined />}
                suffix={`/ ${stats.total || 0}`}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="Reuniões Realizadas"
                value={stats.reunioes_realizadas || 0}
                valueStyle={{ color: '#722ed1' }}
                prefix={<TeamOutlined />}
                suffix={`/ ${stats.total || 0}`}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="Entregas Concluídas"
                value={stats.entregas_concluidas || 0}
                valueStyle={{ color: '#52c41a' }}
                prefix={<CheckCircleFilled />}
                suffix={`/ ${stats.total || 0}`}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* Filters Card */}
      <Card style={{ marginBottom: 16 }} bodyStyle={{ paddingBottom: 12 }}>
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} md={8} lg={4}>
            <div style={{ marginBottom: 4 }}>
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
          <Col xs={24} sm={12} md={8} lg={3}>
            <div style={{ marginBottom: 4 }}>
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
            <div style={{ marginBottom: 4 }}>
              <Text type="secondary" style={{ fontSize: 12, textTransform: 'uppercase' }}>
                Município
              </Text>
            </div>
            <Select
              style={{ width: '100%' }}
              placeholder="Buscar município..."
              allowClear
              showSearch
              optionFilterProp="label"
              value={filters.municipio}
              onChange={(val) => setFilters((prev) => ({ ...prev, municipio: val }))}
              options={municipios.map((m) => ({ label: `${m.nome} - ${m.uf}`, value: m.id }))}
            />
          </Col>
          <Col xs={24} sm={12} md={8} lg={4}>
            <div style={{ marginBottom: 4 }}>
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
              onChange={(val) => setFilters((prev) => ({ ...prev, projeto: val }))}
              options={projetos.map((p) => ({ label: p.nome, value: p.id }))}
            />
          </Col>
          <Col xs={24} sm={12} md={8} lg={4}>
            <div style={{ marginBottom: 4 }}>
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
              onChange={(val) => setFilters((prev) => ({ ...prev, coordenador: val }))}
              options={coordenadores.map((c) => ({ label: c.nome, value: c.id }))}
            />
          </Col>
          <Col xs={24} sm={12} md={8} lg={4}>
            <div style={{ marginBottom: 4 }}>
              <Text type="secondary" style={{ fontSize: 12, textTransform: 'uppercase' }}>
                Status
              </Text>
            </div>
            <Select
              style={{ width: '100%' }}
              placeholder="Todos"
              allowClear
              value={filters.status_geral}
              onChange={(val) => setFilters((prev) => ({ ...prev, status_geral: val }))}
              options={[
                { label: 'Em Andamento', value: 'em_andamento' },
                { label: 'Concluídos', value: 'concluido' },
                { label: 'Pendentes', value: 'pendente' },
              ]}
            />
          </Col>
        </Row>
        <Divider style={{ margin: '16px 0 12px' }} />
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
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

      {/* Table Card */}
      <Card
        bodyStyle={{ padding: 0 }}
        title={
          <Space>
            <Text strong>Resultados:</Text>
            <Text type="danger" strong>{pagination.total}</Text>
            <Text>ações</Text>
          </Space>
        }
      >
        {/* Column Group Headers */}
        <div
          style={{
            display: 'flex',
            borderBottom: '1px solid #f0f0f0',
            background: '#fafafa',
            fontSize: 12,
            fontWeight: 600,
            textTransform: 'uppercase',
          }}
        >
          <div
            style={{
              flex: '0 0 480px',
              padding: '8px 16px',
              borderRight: '1px solid #f0f0f0',
            }}
          >
            Identificação
          </div>
          <div
            style={{
              flex: '0 0 400px',
              padding: '8px 16px',
              borderRight: '1px solid #f0f0f0',
              color: '#1890ff',
            }}
          >
            Fluxo: Carta → Contato → Reunião → Entrega
          </div>
          <div
            style={{
              flex: 1,
              padding: '8px 16px',
            }}
          >
            Detalhes
          </div>
        </div>

        <Table
          columns={columns}
          dataSource={acoes}
          rowKey="id"
          loading={loading}
          scroll={{ x: 1400 }}
          pagination={{
            ...pagination,
            showSizeChanger: true,
            showTotal: (total, range) => `Mostrando ${range[0]} a ${range[1]} de ${total} ações`,
            onChange: (page, pageSize) => {
              setPagination((prev) => ({ ...prev, current: page, pageSize }));
              fetchData(page);
            },
          }}
          size="middle"
        />
      </Card>

      {/* Legend */}
      <Card style={{ marginTop: 16 }} size="small">
        <Space size="large" wrap>
          <Text strong style={{ textTransform: 'uppercase', fontSize: 12 }}>
            Legenda:
          </Text>
          <Space>
            <CheckCircleFilled style={{ color: '#52c41a' }} />
            <Text type="secondary">Concluído</Text>
          </Space>
          <Space>
            <ClockCircleFilled style={{ color: '#1890ff' }} />
            <Text type="secondary">Em Andamento</Text>
          </Space>
          <Space>
            <ExclamationCircleFilled style={{ color: '#faad14' }} />
            <Text type="secondary">Pendente</Text>
          </Space>
          <Space>
            <MinusCircleFilled style={{ color: '#999' }} />
            <Text type="secondary">N/A</Text>
          </Space>
        </Space>
      </Card>

      {/* Create/Edit Modal */}
      <Modal
        title={
          <div>
            <Title level={4} style={{ margin: 0 }}>
              {editingAcao ? 'Editar Ação' : 'Nova Ação'}
            </Title>
            <Text type="secondary" style={{ fontSize: 13 }}>
              Gerenciamento do ciclo de vida do projeto
            </Text>
          </div>
        }
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <div>
              {editingAcao && (
                <Button
                  danger
                  type="text"
                  icon={<DeleteOutlined />}
                  onClick={() => {
                    setModalVisible(false);
                    handleDelete(editingAcao);
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
          {/* Dados Básicos */}
          <Card size="small" title="Identificação" style={{ marginBottom: 16 }}>
            <Row gutter={16}>
              <Col xs={24} sm={12}>
                <Form.Item
                  name="municipio"
                  label="Município"
                  rules={[{ required: true, message: 'Selecione o município' }]}
                >
                  <Select
                    placeholder="Selecione o município..."
                    showSearch
                    optionFilterProp="label"
                    options={municipios.map((m) => ({ label: `${m.nome} - ${m.uf}`, value: m.id }))}
                  />
                </Form.Item>
              </Col>
              <Col xs={24} sm={12}>
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
            </Row>
            <Row gutter={16}>
              <Col xs={24} sm={12}>
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
              <Col xs={24} sm={12}>
                <Form.Item name="area" label="Área">
                  <Input placeholder="Ex: DAT, Pedagógico..." />
                </Form.Item>
              </Col>
            </Row>
          </Card>

          {/* Fluxo de Status */}
          <Card size="small" title="Fluxo de Acompanhamento" style={{ marginBottom: 16 }}>
            <Row gutter={16}>
              {/* Carta */}
              <Col xs={24} sm={12} md={6}>
                <Card
                  size="small"
                  style={{ background: '#f6ffed', borderColor: '#b7eb8f' }}
                  title={
                    <Space>
                      <MailOutlined />
                      <span>1. Carta</span>
                    </Space>
                  }
                >
                  <Form.Item name="status_carta" label="Status">
                    <Select
                      placeholder="Selecione..."
                      options={STATUS_OPTIONS}
                      allowClear
                    />
                  </Form.Item>
                  <Form.Item name="data_carta" label="Data">
                    <DatePicker style={{ width: '100%' }} format="DD/MM/YYYY" />
                  </Form.Item>
                </Card>
              </Col>

              {/* Contato */}
              <Col xs={24} sm={12} md={6}>
                <Card
                  size="small"
                  style={{ background: '#e6f7ff', borderColor: '#91d5ff' }}
                  title={
                    <Space>
                      <PhoneOutlined />
                      <span>2. Contato</span>
                    </Space>
                  }
                >
                  <Form.Item name="status_contato" label="Status">
                    <Select
                      placeholder="Selecione..."
                      options={STATUS_OPTIONS}
                      allowClear
                    />
                  </Form.Item>
                  <Form.Item name="data_contato" label="Data">
                    <DatePicker style={{ width: '100%' }} format="DD/MM/YYYY" />
                  </Form.Item>
                </Card>
              </Col>

              {/* Reunião */}
              <Col xs={24} sm={12} md={6}>
                <Card
                  size="small"
                  style={{ background: '#f9f0ff', borderColor: '#d3adf7' }}
                  title={
                    <Space>
                      <TeamOutlined />
                      <span>3. Reunião</span>
                    </Space>
                  }
                >
                  <Form.Item name="status_reuniao" label="Status">
                    <Select
                      placeholder="Selecione..."
                      options={STATUS_OPTIONS}
                      allowClear
                    />
                  </Form.Item>
                  <Form.Item name="data_reuniao" label="Data">
                    <DatePicker style={{ width: '100%' }} format="DD/MM/YYYY" />
                  </Form.Item>
                </Card>
              </Col>

              {/* Entrega */}
              <Col xs={24} sm={12} md={6}>
                <Card
                  size="small"
                  style={{ background: '#fff7e6', borderColor: '#ffd591' }}
                  title={
                    <Space>
                      <SendOutlined />
                      <span>4. Entrega</span>
                    </Space>
                  }
                >
                  <Form.Item name="status_entrega" label="Status">
                    <Select
                      placeholder="Selecione..."
                      options={STATUS_OPTIONS}
                      allowClear
                    />
                  </Form.Item>
                  <Form.Item name="data_entrega" label="Data">
                    <DatePicker style={{ width: '100%' }} format="DD/MM/YYYY" />
                  </Form.Item>
                </Card>
              </Col>
            </Row>
          </Card>

          {/* Observações */}
          <Form.Item name="observacoes" label="Observações">
            <Input.TextArea rows={3} placeholder="Observações sobre a ação..." />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
