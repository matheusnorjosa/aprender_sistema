/**
 * DAT Module - Registros de Turmas
 *
 * Interface de gestão de registros DAT com filtros avançados,
 * tabela com cabeçalhos agrupados e legenda de status.
 * Ref: v2/docs/SPEC_DAT_REGISTROS.md
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
  Checkbox,
  Tooltip,
  Divider,
  Row,
  Col,
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
  DatabaseOutlined,
  BookOutlined,
  BarChartOutlined,
} from '@ant-design/icons';
import {
  listDATRegistros,
  createDATRegistro,
  updateDATRegistro,
  deleteDATRegistro,
  exportDATRegistros,
  getProjetosGeraisOptions,
  getMunicipiosOptions,
  getProjetosOptions,
} from '../../api/datModule';
import dayjs from 'dayjs';

const { Title, Text } = Typography;

// Status options
const STATUS_OPTIONS = [
  { label: 'Pendente', value: 'pendente' },
  { label: 'Em Andamento', value: 'em_andamento' },
  { label: 'Concluído', value: 'concluido' },
];

// UF options (Brazilian states)
const UF_OPTIONS = [
  'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
  'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN',
  'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO',
].map((uf) => ({ label: uf, value: uf }));

// Região mapping
const REGIAO_UFS = {
  Norte: ['AC', 'AP', 'AM', 'PA', 'RO', 'RR', 'TO'],
  Nordeste: ['AL', 'BA', 'CE', 'MA', 'PB', 'PE', 'PI', 'RN', 'SE'],
  'Centro-Oeste': ['DF', 'GO', 'MT', 'MS'],
  Sudeste: ['ES', 'MG', 'RJ', 'SP'],
  Sul: ['PR', 'RS', 'SC'],
};

const REGIAO_OPTIONS = [
  { label: 'Todas', value: '' },
  { label: 'Norte', value: 'Norte' },
  { label: 'Nordeste', value: 'Nordeste' },
  { label: 'Centro-Oeste', value: 'Centro-Oeste' },
  { label: 'Sudeste', value: 'Sudeste' },
  { label: 'Sul', value: 'Sul' },
];

export default function DATRegistrosPage() {
  const [registros, setRegistros] = useState([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 15, total: 0 });

  // Filter states
  const [filters, setFilters] = useState({
    regiao: '',
    uf: undefined,
    municipio: undefined,
    projeto_geral: undefined,
    usa_avaliar: undefined,
    status_formar: undefined,
  });

  // Options for dropdowns
  const [projetosGerais, setProjetosGerais] = useState([]);
  const [municipios, setMunicipios] = useState([]);
  const [projetos, setProjetos] = useState([]);
  const [filteredUFs, setFilteredUFs] = useState(UF_OPTIONS);

  // Modal states
  const [modalVisible, setModalVisible] = useState(false);
  const [editingRegistro, setEditingRegistro] = useState(null);

  const [form] = Form.useForm();

  // Load options on mount
  useEffect(() => {
    const loadOptions = async () => {
      try {
        const [pgData, munData, projData] = await Promise.all([
          getProjetosGeraisOptions(),
          getMunicipiosOptions(),
          getProjetosOptions(),
        ]);
        setProjetosGerais(pgData.results || pgData || []);
        setMunicipios(munData.results || munData || []);
        setProjetos(projData.results || projData || []);
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
        ordering: '-created_at',
      };

      // Apply filters
      if (filters.uf) params.uf = filters.uf;
      if (filters.municipio) params.municipio = filters.municipio;
      if (filters.projeto_geral) params.projeto_geral = filters.projeto_geral;
      if (filters.usa_avaliar !== undefined) params.usa_avaliar = filters.usa_avaliar;
      if (filters.status_formar) params.status_formar = filters.status_formar;

      const data = await listDATRegistros(params);
      setRegistros(data.results || data || []);
      setPagination((prev) => ({
        ...prev,
        current: page,
        total: data.count || (data.results || data || []).length,
      }));
    } catch (error) {
      message.error(`Erro ao carregar dados: ${error.message}`);
    } finally {
      setLoading(false);
    }
  }, [filters, pagination.pageSize]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Handle region filter change
  const handleRegiaoChange = (regiao) => {
    setFilters((prev) => ({ ...prev, regiao, uf: undefined }));
    if (regiao && REGIAO_UFS[regiao]) {
      setFilteredUFs(UF_OPTIONS.filter((uf) => REGIAO_UFS[regiao].includes(uf.value)));
    } else {
      setFilteredUFs(UF_OPTIONS);
    }
  };

  // Clear all filters
  const handleClearFilters = () => {
    setFilters({
      regiao: '',
      uf: undefined,
      municipio: undefined,
      projeto_geral: undefined,
      usa_avaliar: undefined,
      status_formar: undefined,
    });
    setFilteredUFs(UF_OPTIONS);
  };

  // Apply filters
  const handleApplyFilters = () => {
    fetchData(1);
  };

  // Export to CSV
  const handleExport = async () => {
    try {
      const blob = await exportDATRegistros(filters);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'dat_registros.csv';
      a.click();
      window.URL.revokeObjectURL(url);
      message.success('Exportação realizada com sucesso');
    } catch (error) {
      message.error(`Erro ao exportar: ${error.message}`);
    }
  };

  // CRUD handlers
  const handleCreate = () => {
    setEditingRegistro(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (record) => {
    setEditingRegistro(record);
    form.setFieldsValue({
      ...record,
      reuniao_dat: record.reuniao_dat ? dayjs(record.reuniao_dat) : null,
    });
    setModalVisible(true);
  };

  const handleSave = async (values) => {
    try {
      const payload = {
        ...values,
        reuniao_dat: values.reuniao_dat ? values.reuniao_dat.format('YYYY-MM-DD') : null,
      };

      if (editingRegistro) {
        await updateDATRegistro(editingRegistro.id, payload);
        message.success('Registro atualizado com sucesso');
      } else {
        await createDATRegistro(payload);
        message.success('Registro criado com sucesso');
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
      content: `Excluir registro de "${record.municipio_nome}"? Esta ação requer permissão de Superintendência.`,
      okText: 'Sim, excluir',
      okType: 'danger',
      cancelText: 'Cancelar',
      onOk: async () => {
        try {
          await deleteDATRegistro(record.id);
          message.success('Registro excluído com sucesso');
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
        return <ClockCircleFilled style={{ color: '#faad14', fontSize: 18 }} />;
      case 'pendente':
        return <ExclamationCircleFilled style={{ color: '#ff4d4f', fontSize: 18 }} />;
      default:
        return <MinusCircleFilled style={{ color: '#999', fontSize: 18 }} />;
    }
  };

  // Table columns with grouped headers
  const columns = [
    // Dados Básicos
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
      title: 'Projeto Geral',
      dataIndex: 'projeto_geral_nome',
      key: 'projeto_geral',
      width: 150,
    },
    {
      title: 'Projeto',
      dataIndex: 'projeto_nome',
      key: 'projeto',
      width: 150,
    },
    {
      title: 'Alunos',
      dataIndex: 'aluno_qtde',
      key: 'aluno_qtde',
      width: 80,
      align: 'right',
      render: (val) => val?.toLocaleString('pt-BR') || '-',
    },
    {
      title: 'Profs.',
      dataIndex: 'professor_qtde',
      key: 'professor_qtde',
      width: 80,
      align: 'right',
      render: (val) => val?.toLocaleString('pt-BR') || '-',
    },
    // Detalhes FORMAR
    {
      title: 'Reunião DAT',
      dataIndex: 'reuniao_dat',
      key: 'reuniao_dat',
      width: 110,
      render: (val) => (val ? dayjs(val).format('DD/MM/YYYY') : '-'),
    },
    {
      title: 'ID Turma',
      dataIndex: 'turma_formar_id',
      key: 'turma_formar_id',
      width: 100,
      render: (val) =>
        val ? (
          <Text code style={{ color: '#1890ff' }}>
            {val}
          </Text>
        ) : (
          '-'
        ),
    },
    {
      title: 'Códs',
      dataIndex: 'nr_codigos',
      key: 'nr_codigos',
      width: 70,
      align: 'center',
      render: (val) =>
        val ? (
          <Tag>{val}</Tag>
        ) : (
          '-'
        ),
    },
    {
      title: 'Chaves',
      dataIndex: 'chaves_inscricao_status',
      key: 'chaves',
      width: 100,
      render: (status) => {
        const colors = {
          concluido: 'green',
          em_andamento: 'gold',
          pendente: 'default',
        };
        const labels = {
          concluido: 'Geradas',
          em_andamento: 'Pend.',
          pendente: 'Pend.',
        };
        return <Tag color={colors[status]}>{labels[status] || status}</Tag>;
      },
    },
    {
      title: 'Envio',
      dataIndex: 'envio_codigos_status',
      key: 'envio',
      width: 70,
      align: 'center',
      render: (status) => (
        <Tooltip title={STATUS_OPTIONS.find((s) => s.value === status)?.label || status}>
          {renderStatusIcon(status)}
        </Tooltip>
      ),
    },
    {
      title: 'Obs. FORMAR',
      dataIndex: 'obs_formar',
      key: 'obs_formar',
      width: 150,
      ellipsis: { showTitle: false },
      render: (val) => (
        <Tooltip title={val}>
          <Text type="secondary">{val || '-'}</Text>
        </Tooltip>
      ),
    },
    // Detalhes AVALIAR
    {
      title: 'Usa AVALIAR',
      dataIndex: 'usa_avaliar',
      key: 'usa_avaliar',
      width: 100,
      align: 'center',
      render: (val) =>
        val ? (
          <Tag color="green">SIM</Tag>
        ) : (
          <Tag color="default">NÃO</Tag>
        ),
    },
    {
      title: 'Recebidos',
      dataIndex: 'alunos_recebidos_status',
      key: 'recebidos',
      width: 90,
      align: 'center',
      render: (status) => renderStatusIcon(status),
    },
    {
      title: 'Validados',
      dataIndex: 'alunos_validados_status',
      key: 'validados',
      width: 90,
      align: 'center',
      render: (status) => renderStatusIcon(status),
    },
    {
      title: 'Importados',
      dataIndex: 'alunos_importados_status',
      key: 'importados',
      width: 90,
      align: 'center',
      render: (status) => renderStatusIcon(status),
    },
    {
      title: 'Obs. AVALIAR',
      dataIndex: 'obs_avaliar',
      key: 'obs_avaliar',
      width: 150,
      ellipsis: { showTitle: false },
      render: (val) => (
        <Tooltip title={val}>
          <Text type="secondary">{val || '-'}</Text>
        </Tooltip>
      ),
    },
    // Ações
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
              aria-label="Editar registro"
            />
          </Tooltip>
          <Tooltip title="Excluir">
            <Button
              type="text"
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(record)}
              aria-label="Excluir registro"
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
              Listagem de Registros DAT
            </Title>
            <Text type="secondary">
              Gerenciamento e acompanhamento de dados de turmas por município e projeto.
            </Text>
          </div>
          <Space>
            <Button icon={<DownloadOutlined />} onClick={handleExport}>
              Exportar
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              Novo Registro
            </Button>
          </Space>
        </div>
      </div>

      {/* Filters Card */}
      <Card style={{ marginBottom: 16 }} bodyStyle={{ paddingBottom: 12 }}>
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} md={8} lg={4}>
            <div style={{ marginBottom: 4 }}>
              <Text type="secondary" style={{ fontSize: 12, textTransform: 'uppercase' }}>
                Região
              </Text>
            </div>
            <Select
              style={{ width: '100%' }}
              placeholder="Todas"
              allowClear
              value={filters.regiao || undefined}
              onChange={handleRegiaoChange}
              options={REGIAO_OPTIONS}
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
              options={filteredUFs}
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
                Projeto Geral
              </Text>
            </div>
            <Select
              style={{ width: '100%' }}
              placeholder="Todos"
              allowClear
              value={filters.projeto_geral}
              onChange={(val) => setFilters((prev) => ({ ...prev, projeto_geral: val }))}
              options={projetosGerais.map((pg) => ({ label: pg.nome, value: pg.id }))}
            />
          </Col>
          <Col xs={24} sm={12} md={8} lg={4}>
            <div style={{ marginBottom: 4 }}>
              <Text type="secondary" style={{ fontSize: 12, textTransform: 'uppercase' }}>
                Usa AVALIAR
              </Text>
            </div>
            <Select
              style={{ width: '100%' }}
              placeholder="Todos"
              allowClear
              value={filters.usa_avaliar}
              onChange={(val) => setFilters((prev) => ({ ...prev, usa_avaliar: val }))}
              options={[
                { label: 'Sim', value: 'true' },
                { label: 'Não', value: 'false' },
              ]}
            />
          </Col>
          <Col xs={24} sm={12} md={8} lg={4}>
            <div style={{ marginBottom: 4 }}>
              <Text type="secondary" style={{ fontSize: 12, textTransform: 'uppercase' }}>
                Status Geral
              </Text>
            </div>
            <Select
              style={{ width: '100%' }}
              placeholder="Todos"
              allowClear
              value={filters.status_formar}
              onChange={(val) => setFilters((prev) => ({ ...prev, status_formar: val }))}
              options={[
                { label: 'Completo', value: 'completo' },
                { label: 'Pendente', value: 'pendente' },
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
          <Button type="primary" icon={<FilterOutlined />} onClick={handleApplyFilters}>
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
            <Text>registros</Text>
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
              flex: '0 0 640px',
              padding: '8px 16px',
              borderRight: '1px solid #f0f0f0',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            <DatabaseOutlined /> Dados Básicos
          </div>
          <div
            style={{
              flex: '0 0 580px',
              padding: '8px 16px',
              borderRight: '1px solid #f0f0f0',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              color: '#1890ff',
            }}
          >
            <BookOutlined /> Detalhes FORMAR
          </div>
          <div
            style={{
              flex: 1,
              padding: '8px 16px',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              color: '#52c41a',
            }}
          >
            <BarChartOutlined /> Detalhes AVALIAR
          </div>
        </div>

        <Table
          columns={columns}
          dataSource={registros}
          rowKey="id"
          loading={loading}
          scroll={{ x: 1800 }}
          pagination={{
            ...pagination,
            showSizeChanger: true,
            showTotal: (total, range) => `Mostrando ${range[0]} a ${range[1]} de ${total} registros`,
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
            Legenda de Ícones:
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
            <Text type="secondary">Não Aplicável</Text>
          </Space>
          <Divider type="vertical" />
          <Space>
            <Tag color="green">Chaves Geradas</Tag>
          </Space>
          <Space>
            <Tag color="gold">Chaves Pendentes</Tag>
          </Space>
        </Space>
      </Card>

      {/* Create/Edit Modal */}
      <Modal
        title={
          <div>
            <Title level={4} style={{ margin: 0 }}>
              {editingRegistro ? 'Editar Registro DAT' : 'Novo Registro DAT'}
            </Title>
            <Text type="secondary" style={{ fontSize: 13 }}>
              Gerenciamento de dados de acompanhamento de turmas FORMAR e AVALIAR
            </Text>
          </div>
        }
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <div>
              {editingRegistro && (
                <Button danger type="text" icon={<DeleteOutlined />} onClick={() => { setModalVisible(false); handleDelete(editingRegistro); }}>
                  Excluir Registro
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
        width={1100}
        styles={{ body: { maxHeight: 'calc(100vh - 250px)', overflowY: 'auto' } }}
      >
        <Form form={form} layout="vertical" onFinish={handleSave}>
          {/* Dados Básicos */}
          <Card
            size="small"
            title={
              <Space>
                <DatabaseOutlined style={{ color: '#1890ff' }} />
                <span>Dados Básicos</span>
              </Space>
            }
            style={{ marginBottom: 16 }}
          >
            <Row gutter={16}>
              <Col xs={24} sm={12} md={8}>
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
              <Col xs={24} sm={12} md={8}>
                <Form.Item
                  name="projeto_geral"
                  label="Projeto Geral"
                  rules={[{ required: true, message: 'Selecione o projeto geral' }]}
                >
                  <Select
                    placeholder="Selecione..."
                    options={projetosGerais.map((pg) => ({ label: pg.nome, value: pg.id }))}
                  />
                </Form.Item>
              </Col>
              <Col xs={24} sm={12} md={8}>
                <Form.Item
                  name="projeto"
                  label="Projeto"
                  rules={[{ required: true, message: 'Selecione o projeto' }]}
                >
                  <Select
                    placeholder="Filtrado pelo geral..."
                    showSearch
                    optionFilterProp="label"
                    options={projetos.map((p) => ({ label: `${p.nome} (${p.codigo})`, value: p.id }))}
                  />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col xs={12} sm={6}>
                <Form.Item
                  name="aluno_qtde"
                  label="Qtde Alunos"
                  rules={[{ required: true, message: 'Obrigatório' }]}
                >
                  <InputNumber min={0} style={{ width: '100%' }} placeholder="0" />
                </Form.Item>
              </Col>
              <Col xs={12} sm={6}>
                <Form.Item name="professor_qtde" label="Qtde Professores">
                  <InputNumber min={0} style={{ width: '100%' }} placeholder="0" />
                </Form.Item>
              </Col>
            </Row>
          </Card>

          {/* Two Column Layout: FORMAR and AVALIAR */}
          <Row gutter={16}>
            {/* Plataforma FORMAR */}
            <Col xs={24} lg={12}>
              <Card
                size="small"
                title={
                  <Space>
                    <BookOutlined style={{ color: '#1890ff' }} />
                    <span>Plataforma FORMAR</span>
                    <Tag color="blue">Integração</Tag>
                  </Space>
                }
                style={{ marginBottom: 16, height: '100%' }}
              >
                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item name="reuniao_dat" label="Data Reunião DAT">
                      <DatePicker style={{ width: '100%' }} format="DD/MM/YYYY" />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item name="turma_formar_status" label="Status Turma">
                      <Select placeholder="Selecione..." options={STATUS_OPTIONS} allowClear />
                    </Form.Item>
                  </Col>
                </Row>

                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item name="turma_formar_id" label="ID Turma FORMAR">
                      <Input placeholder="Ex: 48291" />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item name="nr_codigos" label="Nº Códigos">
                      <InputNumber min={0} style={{ width: '100%' }} placeholder="0" />
                    </Form.Item>
                  </Col>
                </Row>

                <Divider style={{ margin: '12px 0' }} dashed />

                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Form.Item name="chaves_inscricao_status" noStyle>
                      <Select
                        placeholder="Status"
                        options={STATUS_OPTIONS}
                        style={{ width: 140 }}
                        allowClear
                      />
                    </Form.Item>
                    <Text>Chaves de Inscrição</Text>
                    <Form.Item name="chaves_inscricao_data" noStyle>
                      <DatePicker format="DD/MM/YYYY" placeholder="Data" style={{ width: 130 }} />
                    </Form.Item>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Form.Item name="instrucoes_status" noStyle>
                      <Select
                        placeholder="Status"
                        options={STATUS_OPTIONS}
                        style={{ width: 140 }}
                        allowClear
                      />
                    </Form.Item>
                    <Text>Instruções</Text>
                    <Form.Item name="instrucoes_data" noStyle>
                      <DatePicker format="DD/MM/YYYY" placeholder="Data" style={{ width: 130 }} />
                    </Form.Item>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Form.Item name="envio_codigos_status" noStyle>
                      <Select
                        placeholder="Status"
                        options={STATUS_OPTIONS}
                        style={{ width: 140 }}
                        allowClear
                      />
                    </Form.Item>
                    <Text>Envio de Códigos</Text>
                    <Form.Item name="envio_codigos_data" noStyle>
                      <DatePicker format="DD/MM/YYYY" placeholder="Data" style={{ width: 130 }} />
                    </Form.Item>
                  </div>
                </div>

                <Divider style={{ margin: '12px 0' }} dashed />

                <Form.Item name="obs_formar" label="Observações FORMAR" style={{ marginBottom: 0 }}>
                  <Input.TextArea rows={3} placeholder="Observações sobre a integração com FORMAR..." />
                </Form.Item>
              </Card>
            </Col>

            {/* Plataforma AVALIAR */}
            <Col xs={24} lg={12}>
              <Card
                size="small"
                title={
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
                    <Space>
                      <BarChartOutlined style={{ color: '#52c41a' }} />
                      <span>Plataforma AVALIAR</span>
                    </Space>
                    <Form.Item name="usa_avaliar" valuePropName="checked" noStyle>
                      <Checkbox>Usa AVALIAR</Checkbox>
                    </Form.Item>
                  </div>
                }
                style={{ marginBottom: 16, height: '100%' }}
              >
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  {/* Alunos Recebidos */}
                  <Card size="small" style={{ background: '#fafafa' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Space>
                        <Form.Item name="alunos_recebidos_status" noStyle>
                          <Select
                            placeholder="Status"
                            options={STATUS_OPTIONS}
                            style={{ width: 140 }}
                            allowClear
                          />
                        </Form.Item>
                        <Text strong>Alunos Recebidos</Text>
                      </Space>
                      <Form.Item name="alunos_recebidos_data" noStyle>
                        <DatePicker format="DD/MM/YYYY" placeholder="Data" style={{ width: 130 }} />
                      </Form.Item>
                    </div>
                  </Card>

                  {/* Alunos Validados */}
                  <Card size="small" style={{ background: '#fafafa' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Space>
                        <Form.Item name="alunos_validados_status" noStyle>
                          <Select
                            placeholder="Status"
                            options={STATUS_OPTIONS}
                            style={{ width: 140 }}
                            allowClear
                          />
                        </Form.Item>
                        <Text strong>Alunos Validados</Text>
                      </Space>
                      <Form.Item name="alunos_validados_data" noStyle>
                        <DatePicker format="DD/MM/YYYY" placeholder="Data" style={{ width: 130 }} />
                      </Form.Item>
                    </div>
                  </Card>

                  {/* Alunos Importados */}
                  <Card size="small" style={{ background: '#fafafa' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Space>
                        <Form.Item name="alunos_importados_status" noStyle>
                          <Select
                            placeholder="Status"
                            options={STATUS_OPTIONS}
                            style={{ width: 140 }}
                            allowClear
                          />
                        </Form.Item>
                        <Text strong>Alunos Importados</Text>
                      </Space>
                      <Form.Item name="alunos_importados_data" noStyle>
                        <DatePicker format="DD/MM/YYYY" placeholder="Data" style={{ width: 130 }} />
                      </Form.Item>
                    </div>
                  </Card>
                </div>

                <Divider style={{ margin: '12px 0' }} dashed />

                <Form.Item name="obs_avaliar" label="Observações AVALIAR" style={{ marginBottom: 0 }}>
                  <Input.TextArea rows={3} placeholder="Detalhes sobre a importação no AVALIAR..." />
                </Form.Item>
              </Card>
            </Col>
          </Row>
        </Form>
      </Modal>
    </div>
  );
}
