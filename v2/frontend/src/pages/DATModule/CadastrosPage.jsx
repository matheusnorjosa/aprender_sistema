/**
 * DAT Module - Gestão de Cadastros em Plataformas
 *
 * Interface de gestão de cadastros e workflows nas plataformas FORMAR e AVALIAR.
 * Workflow FORMAR: Criação Curso → Chaves → Instruções → Envio
 * Workflow AVALIAR: Recebidos → Validados → Importados
 *
 * Baseado na análise da planilha de controle - aba CADASTROS
 * 1.515 registros
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
  InputNumber,
  DatePicker,
  Tooltip,
  Divider,
  Row,
  Col,
  Statistic,
  Tabs,
  Steps,
  Badge,
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
import dayjs from 'dayjs';

const { Title, Text } = Typography;

// Status options
const STATUS_OPTIONS = [
  { label: 'Pendente', value: 'pendente' },
  { label: 'Em Andamento', value: 'em_andamento' },
  { label: 'Concluído', value: 'concluido' },
  { label: 'N/A', value: 'na' },
];

// Plataformas
const PLATAFORMAS = {
  FORMAR: {
    key: 'FORMAR',
    label: 'FORMAR',
    color: '#1890ff',
    icon: <BookOutlined />,
    url: 'https://www.aprenderformar.com.br/plataforma/',
    etapas: [
      { key: 'criacao_curso', label: 'Criação Curso' },
      { key: 'chaves', label: 'Chaves' },
      { key: 'instrucoes', label: 'Instruções' },
      { key: 'envio', label: 'Envio' },
    ],
  },
  AVALIAR: {
    key: 'AVALIAR',
    label: 'AVALIAR',
    color: '#52c41a',
    icon: <BarChartOutlined />,
    url: 'https://avaliar.aprenderformar.com.br/',
    etapas: [
      { key: 'recebidos', label: 'Recebidos' },
      { key: 'validados', label: 'Validados' },
      { key: 'importados', label: 'Importados' },
    ],
  },
};

// Projetos que usam AVALIAR
const PROJETOS_AVALIAR = [
  'ACERTA',
  'NOVO LENDO',
  'TEMA',
  'VIDA E...',
  'PROJETO AMMA',
  'SUPERATIVAR',
  'GESTÃO ESCOLAR',
];

// UF options
const UF_OPTIONS = [
  'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
  'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN',
  'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO',
].map((uf) => ({ label: uf, value: uf }));

export default function CadastrosPage() {
  const [cadastros, setCadastros] = useState([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 15, total: 0 });
  const [stats, setStats] = useState(null);
  const [activeTab, setActiveTab] = useState('FORMAR');

  // Filter states
  const [filters, setFilters] = useState({
    search: '',
    uf: undefined,
    municipio: undefined,
    projeto_geral: undefined,
    status_etapa: undefined,
  });

  // Options for dropdowns
  const [municipios, setMunicipios] = useState([]);
  const [projetosGerais, setProjetosGerais] = useState([]);

  // Modal states
  const [modalVisible, setModalVisible] = useState(false);
  const [editingCadastro, setEditingCadastro] = useState(null);

  const [form] = Form.useForm();

  // Load options on mount
  useEffect(() => {
    const loadOptions = async () => {
      try {
        const [munData, pgData] = await Promise.all([
          getMunicipiosOptions(),
          getProjetosGeraisOptions(),
        ]);
        setMunicipios(munData.results || munData || []);
        setProjetosGerais(pgData.results || pgData || []);
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
        plataforma: activeTab,
      };

      // Apply filters
      if (filters.search) params.search = filters.search;
      if (filters.uf) params.uf = filters.uf;
      if (filters.municipio) params.municipio_id = filters.municipio;
      if (filters.projeto_geral) params.projeto_geral_id = filters.projeto_geral;
      if (filters.status_etapa) params.status_etapa = filters.status_etapa;

      const [data, statsData] = await Promise.all([
        listCadastros(params),
        getCadastrosStats(params),
      ]);

      setCadastros(data.results || data || []);
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
  }, [filters, pagination.pageSize, activeTab]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Clear all filters
  const handleClearFilters = () => {
    setFilters({
      search: '',
      uf: undefined,
      municipio: undefined,
      projeto_geral: undefined,
      status_etapa: undefined,
    });
  };

  // CRUD handlers
  const handleCreate = () => {
    setEditingCadastro(null);
    form.resetFields();
    form.setFieldsValue({ plataforma: activeTab });
    setModalVisible(true);
  };

  const handleEdit = (record) => {
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

  const handleSave = async (values) => {
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
      fetchData(pagination.current);
    } catch (error) {
      message.error(`Erro: ${error.message}`);
    }
  };

  const handleDelete = (record) => {
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
          fetchData(pagination.current);
        } catch (error) {
          message.error(`Erro ao excluir: ${error.message}`);
        }
      },
    });
  };

  // Quick status update
  const handleQuickStatusUpdate = async (record, etapa, newStatus) => {
    try {
      await updateCadastroEtapa(record.id, etapa, newStatus);
      message.success('Status atualizado');
      fetchData(pagination.current);
    } catch (error) {
      message.error(`Erro: ${error.message}`);
    }
  };

  // Status icon renderer
  const renderStatusIcon = (status) => {
    switch (status) {
      case 'concluido':
        return <CheckCircleFilled style={{ color: '#52c41a', fontSize: 18 }} />;
      case 'em_andamento':
        return <ClockCircleFilled style={{ color: '#faad14', fontSize: 18 }} />;
      case 'pendente':
        return <ExclamationCircleFilled style={{ color: '#ff4d4f', fontSize: 18 }} />;
      case 'na':
        return <MinusCircleFilled style={{ color: '#999', fontSize: 18 }} />;
      default:
        return <MinusCircleFilled style={{ color: '#999', fontSize: 18 }} />;
    }
  };

  // Calculate progress for Steps component
  const getStepStatus = (status) => {
    switch (status) {
      case 'concluido':
        return 'finish';
      case 'em_andamento':
        return 'process';
      case 'pendente':
        return 'wait';
      default:
        return 'wait';
    }
  };

  // Calculate current step
  const getCurrentStep = (record, etapas) => {
    for (let i = 0; i < etapas.length; i++) {
      const status = record[`status_${etapas[i].key}`];
      if (status !== 'concluido') {
        return i;
      }
    }
    return etapas.length;
  };

  // Columns for FORMAR
  const columnsFormar = [
    {
      title: 'Projeto',
      dataIndex: 'projeto_geral_nome',
      key: 'projeto',
      width: 120,
      fixed: 'left',
      render: (nome) => <Tag color="blue">{nome}</Tag>,
    },
    {
      title: 'Município - UF',
      key: 'municipio_uf',
      width: 180,
      fixed: 'left',
      render: (_, record) => (
        <Text strong>
          {record.municipio_nome} - {record.uf}
        </Text>
      ),
    },
    {
      title: 'Alunos',
      dataIndex: 'quantidade_alunos',
      key: 'alunos',
      width: 80,
      align: 'right',
      render: (val) => val?.toLocaleString('pt-BR') || '-',
    },
    {
      title: 'Profs.',
      dataIndex: 'quantidade_professores',
      key: 'professores',
      width: 80,
      align: 'right',
      render: (val) => val?.toLocaleString('pt-BR') || '-',
    },
    {
      title: 'Códs',
      dataIndex: 'quantidade_codigos',
      key: 'codigos',
      width: 70,
      align: 'center',
      render: (val) => val ? <Tag>{val}</Tag> : '-',
    },
    {
      title: 'Criação Curso',
      key: 'criacao_curso',
      width: 110,
      align: 'center',
      render: (_, record) => (
        <Tooltip title="Clique para alterar status">
          <div
            style={{ cursor: 'pointer' }}
            onClick={() => {
              const newStatus = record.status_criacao_curso === 'concluido' ? 'pendente' : 'concluido';
              handleQuickStatusUpdate(record, 'criacao_curso', newStatus);
            }}
          >
            {renderStatusIcon(record.status_criacao_curso)}
            <div style={{ fontSize: 10, color: '#999' }}>
              {record.data_criacao_curso ? dayjs(record.data_criacao_curso).format('DD/MM') : '-'}
            </div>
          </div>
        </Tooltip>
      ),
    },
    {
      title: 'Chaves',
      key: 'chaves',
      width: 100,
      align: 'center',
      render: (_, record) => (
        <Tooltip title="Clique para alterar status">
          <div
            style={{ cursor: 'pointer' }}
            onClick={() => {
              const newStatus = record.status_chaves === 'concluido' ? 'pendente' : 'concluido';
              handleQuickStatusUpdate(record, 'chaves', newStatus);
            }}
          >
            {renderStatusIcon(record.status_chaves)}
            <div style={{ fontSize: 10, color: '#999' }}>
              {record.data_chaves ? dayjs(record.data_chaves).format('DD/MM') : '-'}
            </div>
          </div>
        </Tooltip>
      ),
    },
    {
      title: 'Instruções',
      key: 'instrucoes',
      width: 100,
      align: 'center',
      render: (_, record) => (
        <Tooltip title="Clique para alterar status">
          <div
            style={{ cursor: 'pointer' }}
            onClick={() => {
              const newStatus = record.status_instrucoes === 'concluido' ? 'pendente' : 'concluido';
              handleQuickStatusUpdate(record, 'instrucoes', newStatus);
            }}
          >
            {renderStatusIcon(record.status_instrucoes)}
            <div style={{ fontSize: 10, color: '#999' }}>
              {record.data_instrucoes ? dayjs(record.data_instrucoes).format('DD/MM') : '-'}
            </div>
          </div>
        </Tooltip>
      ),
    },
    {
      title: 'Envio',
      key: 'envio',
      width: 100,
      align: 'center',
      render: (_, record) => (
        <Tooltip title="Clique para alterar status">
          <div
            style={{ cursor: 'pointer' }}
            onClick={() => {
              const newStatus = record.status_envio === 'concluido' ? 'pendente' : 'concluido';
              handleQuickStatusUpdate(record, 'envio', newStatus);
            }}
          >
            {renderStatusIcon(record.status_envio)}
            <div style={{ fontSize: 10, color: '#999' }}>
              {record.data_envio ? dayjs(record.data_envio).format('DD/MM') : '-'}
            </div>
          </div>
        </Tooltip>
      ),
    },
    {
      title: 'Link',
      key: 'link',
      width: 60,
      align: 'center',
      render: (_, record) =>
        record.link_planilha ? (
          <Tooltip title="Abrir planilha">
            <Button
              type="link"
              size="small"
              icon={<LinkOutlined />}
              href={record.link_planilha}
              target="_blank"
              aria-label="Abrir planilha externa"
            />
          </Tooltip>
        ) : (
          '-'
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
              aria-label="Editar cadastro"
            />
          </Tooltip>
          <Tooltip title="Excluir">
            <Button
              type="text"
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(record)}
              aria-label="Excluir cadastro"
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  // Columns for AVALIAR
  const columnsAvaliar = [
    {
      title: 'Projeto',
      dataIndex: 'projeto_geral_nome',
      key: 'projeto',
      width: 120,
      fixed: 'left',
      render: (nome) => <Tag color="green">{nome}</Tag>,
    },
    {
      title: 'Município - UF',
      key: 'municipio_uf',
      width: 180,
      fixed: 'left',
      render: (_, record) => (
        <Text strong>
          {record.municipio_nome} - {record.uf}
        </Text>
      ),
    },
    {
      title: 'Recebidos',
      key: 'recebidos',
      width: 120,
      render: (_, record) => (
        <Space direction="vertical" size={0} align="center">
          <Tooltip title="Clique para alterar status">
            <div
              style={{ cursor: 'pointer' }}
              onClick={() => {
                const newStatus = record.status_recebidos === 'concluido' ? 'pendente' : 'concluido';
                handleQuickStatusUpdate(record, 'recebidos', newStatus);
              }}
            >
              {renderStatusIcon(record.status_recebidos)}
            </div>
          </Tooltip>
          <Text type="secondary">{record.quantidade_recebidos || 0}</Text>
        </Space>
      ),
    },
    {
      title: 'Validados',
      key: 'validados',
      width: 120,
      render: (_, record) => (
        <Space direction="vertical" size={0} align="center">
          <Tooltip title="Clique para alterar status">
            <div
              style={{ cursor: 'pointer' }}
              onClick={() => {
                const newStatus = record.status_validados === 'concluido' ? 'pendente' : 'concluido';
                handleQuickStatusUpdate(record, 'validados', newStatus);
              }}
            >
              {renderStatusIcon(record.status_validados)}
            </div>
          </Tooltip>
          <Text type="secondary">{record.quantidade_validados || 0}</Text>
        </Space>
      ),
    },
    {
      title: 'Importados',
      key: 'importados',
      width: 120,
      render: (_, record) => (
        <Space direction="vertical" size={0} align="center">
          <Tooltip title="Clique para alterar status">
            <div
              style={{ cursor: 'pointer' }}
              onClick={() => {
                const newStatus = record.status_importados === 'concluido' ? 'pendente' : 'concluido';
                handleQuickStatusUpdate(record, 'importados', newStatus);
              }}
            >
              {renderStatusIcon(record.status_importados)}
            </div>
          </Tooltip>
          <Text type="secondary">{record.quantidade_importados || 0}</Text>
        </Space>
      ),
    },
    {
      title: 'Progresso',
      key: 'progresso',
      width: 300,
      render: (_, record) => {
        const etapas = PLATAFORMAS.AVALIAR.etapas;
        const current = getCurrentStep(record, etapas);

        return (
          <Steps
            size="small"
            current={current}
            items={etapas.map((etapa) => ({
              title: etapa.label,
              status: getStepStatus(record[`status_${etapa.key}`]),
            }))}
          />
        );
      },
    },
    {
      title: 'Link',
      key: 'link',
      width: 60,
      align: 'center',
      render: (_, record) =>
        record.link_plataforma ? (
          <Tooltip title="Abrir plataforma">
            <Button
              type="link"
              size="small"
              icon={<LinkOutlined />}
              href={record.link_plataforma}
              target="_blank"
              aria-label="Abrir plataforma externa"
            />
          </Tooltip>
        ) : (
          '-'
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
              aria-label="Editar avaliação"
            />
          </Tooltip>
          <Tooltip title="Excluir">
            <Button
              type="text"
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(record)}
              aria-label="Excluir avaliação"
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  const currentColumns = activeTab === 'FORMAR' ? columnsFormar : columnsAvaliar;
  const currentPlataforma = PLATAFORMAS[activeTab];

  return (
    <div style={{ padding: '24px', background: '#f0f2f5', minHeight: 'calc(100vh - 64px)' }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
          <div>
            <Title level={3} style={{ margin: 0 }}>
              <CloudServerOutlined style={{ marginRight: 8 }} />
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
      </div>

      {/* Tabs for FORMAR / AVALIAR */}
      <Card style={{ marginBottom: 16 }}>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            {
              key: 'FORMAR',
              label: (
                <Space>
                  <BookOutlined style={{ color: '#1890ff' }} />
                  <span>FORMAR</span>
                  <Badge count={stats?.total_formar || 0} style={{ backgroundColor: '#1890ff' }} />
                </Space>
              ),
            },
            {
              key: 'AVALIAR',
              label: (
                <Space>
                  <BarChartOutlined style={{ color: '#52c41a' }} />
                  <span>AVALIAR</span>
                  <Badge count={stats?.total_avaliar || 0} style={{ backgroundColor: '#52c41a' }} />
                </Space>
              ),
            },
          ]}
        />

        {/* Stats Cards */}
        {stats && (
          <Row gutter={16} style={{ marginTop: 16 }}>
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
      <Card style={{ marginBottom: 16 }} bodyStyle={{ paddingBottom: 12 }}>
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} md={8} lg={5}>
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
              value={filters.projeto_geral}
              onChange={(val) => setFilters((prev) => ({ ...prev, projeto_geral: val }))}
              options={projetosGerais.map((p) => ({ label: p.nome, value: p.id }))}
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
            <div style={{ marginBottom: 4 }}>
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
          columns={currentColumns}
          dataSource={cadastros}
          rowKey="id"
          loading={loading}
          scroll={{ x: activeTab === 'FORMAR' ? 1200 : 1100 }}
          pagination={{
            ...pagination,
            showSizeChanger: true,
            showTotal: (total, range) => `Mostrando ${range[0]} a ${range[1]} de ${total} cadastros`,
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
            Legenda (clique nos ícones para alterar):
          </Text>
          <Space>
            <CheckCircleFilled style={{ color: '#52c41a' }} />
            <Text type="secondary">Concluído</Text>
          </Space>
          <Space>
            <ClockCircleFilled style={{ color: '#faad14' }} />
            <Text type="secondary">Em Andamento</Text>
          </Space>
          <Space>
            <ExclamationCircleFilled style={{ color: '#ff4d4f' }} />
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
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
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
        <Form form={form} layout="vertical" onFinish={handleSave}>
          <Form.Item name="plataforma" hidden>
            <Input />
          </Form.Item>

          {/* Identificação */}
          <Card size="small" title="Identificação" style={{ marginBottom: 16 }}>
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
            <Row gutter={16}>
              <Col xs={8}>
                <Form.Item name="quantidade_alunos" label="Alunos">
                  <InputNumber min={0} style={{ width: '100%' }} placeholder="0" />
                </Form.Item>
              </Col>
              <Col xs={8}>
                <Form.Item name="quantidade_professores" label="Professores">
                  <InputNumber min={0} style={{ width: '100%' }} placeholder="0" />
                </Form.Item>
              </Col>
              <Col xs={8}>
                <Form.Item name="quantidade_codigos" label="Códigos">
                  <InputNumber min={0} style={{ width: '100%' }} placeholder="Auto" />
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
                  <BookOutlined style={{ color: '#1890ff' }} />
                  <span>Workflow FORMAR</span>
                </Space>
              }
              style={{ marginBottom: 16 }}
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
                  <BarChartOutlined style={{ color: '#52c41a' }} />
                  <span>Workflow AVALIAR</span>
                </Space>
              }
              style={{ marginBottom: 16 }}
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
          <Card size="small" title="Links" style={{ marginBottom: 16 }}>
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
    </div>
  );
}
