/**
 * DAT Module - Gestão de Compras/Materiais
 *
 * Interface de gestão de compras e materiais didáticos.
 * Controle de estoque, distribuição e utilização por projeto/município.
 *
 * Baseado na análise da planilha de controle - aba COMPRAS
 * 1.798 registros, 502.771 itens, 307 produtos, 94 municípios
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
  ShoppingCartOutlined,
  InboxOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  DollarOutlined,
} from '@ant-design/icons';
import {
  listCompras,
  createCompra,
  updateCompra,
  deleteCompra,
  getComprasStats,
  getMunicipiosOptions,
  getProjetosOptions,
  getProdutosOptions,
} from '../../api/datModule';
import { useCrudOperations } from '../../hooks/useCrudOperations';
import dayjs from 'dayjs';

const { Title, Text } = Typography;

// Status options
const STATUS_OPTIONS = [
  { label: 'Disponível', value: 'disponivel', color: 'green' },
  { label: 'Em Uso', value: 'em_uso', color: 'blue' },
  { label: 'Reservado', value: 'reservado', color: 'orange' },
  { label: 'Esgotado', value: 'esgotado', color: 'red' },
];

// Ano de uso options
const ANO_OPTIONS = [
  { label: '2024', value: 2024 },
  { label: '2025', value: 2025 },
  { label: '2026', value: 2026 },
];

// UF options (Brazilian states)
const UF_OPTIONS = [
  'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
  'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN',
  'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO',
].map((uf) => ({ label: uf, value: uf }));

export default function ComprasPage() {
  // Issue #302: Use useCrudOperations hook for standardized CRUD
  const crud = useCrudOperations({
    listFn: listCompras,
    createFn: createCompra,
    updateFn: updateCompra,
    deleteFn: deleteCompra,
    entityName: 'Compra',
    pageSize: 15,
  });

  const [stats, setStats] = useState(null);

  // Filter states
  const [filters, setFilters] = useState({
    search: '',
    uf: undefined,
    municipio: undefined,
    projeto: undefined,
    produto: undefined,
    status: undefined,
    ano_uso: undefined,
  });

  // Options for dropdowns
  const [municipios, setMunicipios] = useState([]);
  const [projetos, setProjetos] = useState([]);
  const [produtos, setProdutos] = useState([]);

  // Modal states
  const [modalVisible, setModalVisible] = useState(false);
  const [editingCompra, setEditingCompra] = useState(null);

  const [form] = Form.useForm();

  // Load options on mount
  useEffect(() => {
    const loadOptions = async () => {
      try {
        const [munData, projData, prodData] = await Promise.all([
          getMunicipiosOptions(),
          getProjetosOptions(),
          getProdutosOptions(),
        ]);
        setMunicipios(munData.results || munData || []);
        setProjetos(projData.results || projData || []);
        setProdutos(prodData.results || prodData || []);
      } catch (error) {
        message.error(`Erro ao carregar opções: ${error.message}`);
      }
    };
    loadOptions();
  }, []);

  // Fetch data with filters (uses crud hook internally)
  const fetchData = useCallback(async (page = 1) => {
    const params = {
      page,
      ordering: '-updated_at',
    };

    // Apply filters
    if (filters.search) params.search = filters.search;
    if (filters.uf) params.uf = filters.uf;
    if (filters.municipio) params.municipio_id = filters.municipio;
    if (filters.projeto) params.projeto_id = filters.projeto;
    if (filters.produto) params.produto_id = filters.produto;
    if (filters.status) params.status = filters.status;
    if (filters.ano_uso) params.ano_uso = filters.ano_uso;

    // Fetch data and stats in parallel
    const [, statsData] = await Promise.all([
      crud.fetchData(params),
      getComprasStats(params).catch(() => null),
    ]);

    setStats(statsData);
  }, [filters, crud]);

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
      produto: undefined,
      status: undefined,
      ano_uso: undefined,
    });
  };

  // CRUD handlers
  const handleCreate = () => {
    setEditingCompra(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (record) => {
    setEditingCompra(record);
    form.setFieldsValue({
      ...record,
      data_compra: record.data_compra ? dayjs(record.data_compra) : null,
      data_entrega: record.data_entrega ? dayjs(record.data_entrega) : null,
    });
    setModalVisible(true);
  };

  // Issue #302: Simplified handleSave using crud hook
  const handleSave = async (values) => {
    const payload = {
      ...values,
      data_compra: values.data_compra ? values.data_compra.format('YYYY-MM-DD') : null,
      data_entrega: values.data_entrega ? values.data_entrega.format('YYYY-MM-DD') : null,
    };

    const result = await crud.handleSave(payload, editingCompra?.id);

    if (result.success) {
      setModalVisible(false);
      form.resetFields();
      fetchData(crud.pagination.current);
    }
  };

  // Issue #302: Simplified handleDelete using crud hook
  const handleDelete = (record) => {
    crud.confirmDelete(record, {
      nameField: 'produto_nome',
      onSuccess: () => fetchData(crud.pagination.current),
    });
  };

  // Calculate disponível
  const calcularDisponivel = (quantidade, utilizado) => {
    return (quantidade || 0) - (utilizado || 0);
  };

  // Status tag renderer
  const renderStatusTag = (status, disponivel, quantidade) => {
    if (!status) {
      // Auto-calculate based on disponível
      if (disponivel === 0) {
        return <Tag color="red">Esgotado</Tag>;
      } else if (disponivel < quantidade * 0.1) {
        return <Tag color="orange">Baixo Estoque</Tag>;
      } else {
        return <Tag color="green">Disponível</Tag>;
      }
    }

    const statusConfig = STATUS_OPTIONS.find((s) => s.value === status);
    return <Tag color={statusConfig?.color || 'default'}>{statusConfig?.label || status}</Tag>;
  };

  // Table columns
  const columns = [
    {
      title: 'Projeto',
      dataIndex: 'projeto_nome',
      key: 'projeto',
      width: 120,
      fixed: 'left',
      render: (nome) => <Tag color="blue">{nome}</Tag>,
    },
    {
      title: 'Produto',
      dataIndex: 'produto_nome',
      key: 'produto',
      width: 200,
      fixed: 'left',
      render: (nome, record) => (
        <div>
          <Text strong>{nome}</Text>
          {record.codigo_produto && (
            <div>
              <Text type="secondary" style={{ fontSize: 11 }}>
                Cód: {record.codigo_produto}
              </Text>
            </div>
          )}
        </div>
      ),
    },
    {
      title: 'UF',
      dataIndex: 'uf',
      key: 'uf',
      width: 60,
      render: (uf) => <Tag>{uf}</Tag>,
    },
    {
      title: 'Município',
      dataIndex: 'municipio_nome',
      key: 'municipio',
      width: 150,
      ellipsis: true,
    },
    {
      title: 'Quantidade',
      dataIndex: 'quantidade',
      key: 'quantidade',
      width: 100,
      align: 'right',
      render: (val) => (
        <Text strong style={{ color: '#1890ff' }}>
          {val?.toLocaleString('pt-BR') || 0}
        </Text>
      ),
    },
    {
      title: 'Utilizado',
      dataIndex: 'quantidade_utilizada',
      key: 'utilizado',
      width: 100,
      align: 'right',
      render: (val) => val?.toLocaleString('pt-BR') || 0,
    },
    {
      title: 'Disponível',
      key: 'disponivel',
      width: 120,
      align: 'right',
      render: (_, record) => {
        const disponivel = calcularDisponivel(record.quantidade, record.quantidade_utilizada);
        const percent = record.quantidade > 0 ? Math.round((disponivel / record.quantidade) * 100) : 0;

        return (
          <Space direction="vertical" size={0} align="end">
            <Text strong style={{ color: disponivel > 0 ? '#52c41a' : '#ff4d4f' }}>
              {disponivel.toLocaleString('pt-BR')}
            </Text>
            <Progress
              percent={percent}
              size="small"
              showInfo={false}
              strokeColor={percent > 20 ? '#52c41a' : percent > 10 ? '#faad14' : '#ff4d4f'}
              style={{ width: 60 }}
            />
          </Space>
        );
      },
    },
    {
      title: 'Ano Uso',
      dataIndex: 'ano_uso',
      key: 'ano_uso',
      width: 90,
      align: 'center',
      render: (ano) => ano ? <Tag>{ano}</Tag> : '-',
    },
    {
      title: 'Status',
      key: 'status',
      width: 120,
      render: (_, record) => {
        const disponivel = calcularDisponivel(record.quantidade, record.quantidade_utilizada);
        return renderStatusTag(record.status_uso, disponivel, record.quantidade);
      },
    },
    {
      title: 'Valor Unit.',
      dataIndex: 'valor_unitario',
      key: 'valor_unitario',
      width: 100,
      align: 'right',
      render: (val) =>
        val ? (
          <Text type="secondary">
            R$ {val.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
          </Text>
        ) : (
          '-'
        ),
    },
    {
      title: 'Valor Total',
      key: 'valor_total',
      width: 120,
      align: 'right',
      render: (_, record) => {
        const total = (record.quantidade || 0) * (record.valor_unitario || 0);
        return total > 0 ? (
          <Text strong>
            R$ {total.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
          </Text>
        ) : (
          '-'
        );
      },
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
              aria-label="Editar compra"
            />
          </Tooltip>
          <Tooltip title="Excluir">
            <Button
              type="text"
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(record)}
              aria-label="Excluir compra"
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <div className="p-6 bg-gray-100" style={{ minHeight: 'calc(100vh - 64px)' }}>
      {/* Header */}
      <div className="mb-6">
        <div className="flex justify-between items-start mb-2">
          <div>
            <Title level={3} className="m-0">
              <ShoppingCartOutlined className="mr-2" />
              Gestão de Compras/Materiais
            </Title>
            <Text type="secondary">
              Controle de estoque, distribuição e utilização de materiais didáticos
            </Text>
          </div>
          <Space>
            <Button icon={<DownloadOutlined />}>Exportar</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              Nova Compra
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
                title="Total de Itens"
                value={stats.total_itens || 0}
                prefix={<InboxOutlined />}
                formatter={(value) => value.toLocaleString('pt-BR')}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="Produtos Diferentes"
                value={stats.total_produtos || 0}
                valueStyle={{ color: '#1890ff' }}
                prefix={<ShoppingCartOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="Disponíveis"
                value={stats.total_disponivel || 0}
                valueStyle={{ color: '#52c41a' }}
                prefix={<CheckCircleOutlined />}
                formatter={(value) => value.toLocaleString('pt-BR')}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="Valor Total"
                value={stats.valor_total || 0}
                valueStyle={{ color: '#722ed1' }}
                prefix={<DollarOutlined />}
                precision={2}
                formatter={(value) => `R$ ${value.toLocaleString('pt-BR')}`}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* Filters Card */}
      <Card className="mb-4" bodyStyle={{ paddingBottom: 12 }}>
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} md={8} lg={4}>
            <div className="mb-1">
              <Text type="secondary" style={{ fontSize: 12, textTransform: 'uppercase' }}>
                Buscar
              </Text>
            </div>
            <Input.Search
              placeholder="Produto, código..."
              allowClear
              value={filters.search}
              onChange={(e) => setFilters((prev) => ({ ...prev, search: e.target.value }))}
              onSearch={() => fetchData(1)}
            />
          </Col>
          <Col xs={24} sm={12} md={8} lg={3}>
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
              onChange={(val) => setFilters((prev) => ({ ...prev, projeto: val }))}
              options={projetos.map((p) => ({ label: p.nome, value: p.id }))}
            />
          </Col>
          <Col xs={24} sm={12} md={8} lg={4}>
            <div className="mb-1">
              <Text type="secondary" style={{ fontSize: 12, textTransform: 'uppercase' }}>
                Produto
              </Text>
            </div>
            <Select
              style={{ width: '100%' }}
              placeholder="Todos"
              allowClear
              showSearch
              optionFilterProp="label"
              value={filters.produto}
              onChange={(val) => setFilters((prev) => ({ ...prev, produto: val }))}
              options={produtos.map((p) => ({ label: p.nome, value: p.id }))}
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
          <Col xs={24} sm={12} md={8} lg={4}>
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
          <Col xs={24} sm={12} md={8} lg={3}>
            <div className="mb-1">
              <Text type="secondary" style={{ fontSize: 12, textTransform: 'uppercase' }}>
                Ano Uso
              </Text>
            </div>
            <Select
              style={{ width: '100%' }}
              placeholder="Todos"
              allowClear
              value={filters.ano_uso}
              onChange={(val) => setFilters((prev) => ({ ...prev, ano_uso: val }))}
              options={ANO_OPTIONS}
            />
          </Col>
          <Col xs={24} sm={12} md={8} lg={3}>
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
              onChange={(val) => setFilters((prev) => ({ ...prev, status: val }))}
              options={STATUS_OPTIONS}
            />
          </Col>
        </Row>
        <Divider style={{ margin: '16px 0 12px' }} />
        <div className="flex justify-end gap-2">
          <Button icon={<ClearOutlined />} onClick={handleClearFilters}>
            Limpar
          </Button>
          <Button icon={<ReloadOutlined />} onClick={() => fetchData(1)} loading={crud.loading}>
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
            <Text type="danger" strong>{crud.pagination.total}</Text>
            <Text>registros</Text>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={crud.data}
          rowKey="id"
          loading={crud.loading}
          scroll={{ x: 1400 }}
          pagination={{
            ...crud.pagination,
            showSizeChanger: true,
            showTotal: (total, range) => `Mostrando ${range[0]} a ${range[1]} de ${total} registros`,
            onChange: (page, pageSize) => {
              crud.setPagination((prev) => ({ ...prev, current: page, pageSize }));
              fetchData(page);
            },
          }}
          size="middle"
          summary={(pageData) => {
            const totalQtd = pageData.reduce((sum, r) => sum + (r.quantidade || 0), 0);
            const totalUtilizado = pageData.reduce((sum, r) => sum + (r.quantidade_utilizada || 0), 0);
            const totalDisponivel = totalQtd - totalUtilizado;
            const totalValor = pageData.reduce(
              (sum, r) => sum + (r.quantidade || 0) * (r.valor_unitario || 0),
              0
            );

            return (
              <Table.Summary fixed>
                <Table.Summary.Row className="bg-gray-50 font-bold">
                  <Table.Summary.Cell index={0} colSpan={4}>
                    Total da Página
                  </Table.Summary.Cell>
                  <Table.Summary.Cell index={4} align="right">
                    {totalQtd.toLocaleString('pt-BR')}
                  </Table.Summary.Cell>
                  <Table.Summary.Cell index={5} align="right">
                    {totalUtilizado.toLocaleString('pt-BR')}
                  </Table.Summary.Cell>
                  <Table.Summary.Cell index={6} align="right">
                    <Text type={totalDisponivel > 0 ? 'success' : 'danger'}>
                      {totalDisponivel.toLocaleString('pt-BR')}
                    </Text>
                  </Table.Summary.Cell>
                  <Table.Summary.Cell index={7} colSpan={2} />
                  <Table.Summary.Cell index={9} align="right">
                    R$ {totalValor.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                  </Table.Summary.Cell>
                  <Table.Summary.Cell index={10} />
                </Table.Summary.Row>
              </Table.Summary>
            );
          }}
        />
      </Card>

      {/* Legend */}
      <Card className="mt-4" size="small">
        <Space size="large" wrap>
          <Text strong style={{ textTransform: 'uppercase', fontSize: 12 }}>
            Legenda:
          </Text>
          <Space>
            <Tag color="green">Disponível</Tag>
            <Text type="secondary">{'>'}20% disponível</Text>
          </Space>
          <Space>
            <Tag color="orange">Baixo Estoque</Tag>
            <Text type="secondary">{'<'}10% disponível</Text>
          </Space>
          <Space>
            <Tag color="red">Esgotado</Tag>
            <Text type="secondary">0 disponível</Text>
          </Space>
        </Space>
      </Card>

      {/* Create/Edit Modal */}
      <Modal
        title={
          <div>
            <Title level={4} className="m-0">
              {editingCompra ? 'Editar Compra' : 'Nova Compra'}
            </Title>
            <Text type="secondary" style={{ fontSize: 13 }}>
              Registro de materiais didáticos
            </Text>
          </div>
        }
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={
          <div className="flex justify-between">
            <div>
              {editingCompra && (
                <Button
                  danger
                  type="text"
                  icon={<DeleteOutlined />}
                  onClick={() => {
                    setModalVisible(false);
                    handleDelete(editingCompra);
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
        width={800}
        styles={{ body: { maxHeight: 'calc(100vh - 250px)', overflowY: 'auto' } }}
      >
        <Form form={form} layout="vertical" onFinish={handleSave}>
          {/* Identificação */}
          <Card size="small" title="Identificação do Material" className="mb-4">
            <Row gutter={16}>
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
              <Col xs={24} sm={12}>
                <Form.Item
                  name="produto"
                  label="Produto"
                  rules={[{ required: true, message: 'Selecione o produto' }]}
                >
                  <Select
                    placeholder="Selecione..."
                    showSearch
                    optionFilterProp="label"
                    options={produtos.map((p) => ({ label: p.nome, value: p.id }))}
                  />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col xs={24} sm={12}>
                <Form.Item name="codigo_produto" label="Código do Produto">
                  <Input placeholder="Ex: KIT-001" />
                </Form.Item>
              </Col>
              <Col xs={24} sm={12}>
                <Form.Item name="descricao_produto" label="Descrição">
                  <Input placeholder="Descrição adicional..." />
                </Form.Item>
              </Col>
            </Row>
          </Card>

          {/* Localização */}
          <Card size="small" title="Localização" className="mb-4">
            <Row gutter={16}>
              <Col xs={24} sm={8}>
                <Form.Item
                  name="uf"
                  label="UF"
                  rules={[{ required: true, message: 'Selecione a UF' }]}
                >
                  <Select
                    placeholder="Selecione..."
                    options={UF_OPTIONS}
                    showSearch
                  />
                </Form.Item>
              </Col>
              <Col xs={24} sm={16}>
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

          {/* Quantidades */}
          <Card size="small" title="Quantidades e Uso" className="mb-4">
            <Row gutter={16}>
              <Col xs={12} sm={6}>
                <Form.Item
                  name="quantidade"
                  label="Quantidade"
                  rules={[{ required: true, message: 'Informe a quantidade' }]}
                >
                  <InputNumber min={0} style={{ width: '100%' }} placeholder="0" />
                </Form.Item>
              </Col>
              <Col xs={12} sm={6}>
                <Form.Item name="quantidade_utilizada" label="Utilizada">
                  <InputNumber min={0} style={{ width: '100%' }} placeholder="0" />
                </Form.Item>
              </Col>
              <Col xs={12} sm={6}>
                <Form.Item name="ano_uso" label="Ano de Uso">
                  <Select placeholder="Selecione..." options={ANO_OPTIONS} allowClear />
                </Form.Item>
              </Col>
              <Col xs={12} sm={6}>
                <Form.Item name="status_uso" label="Status">
                  <Select placeholder="Automático..." options={STATUS_OPTIONS} allowClear />
                </Form.Item>
              </Col>
            </Row>
          </Card>

          {/* Dados da Compra */}
          <Card size="small" title="Dados da Compra" className="mb-4">
            <Row gutter={16}>
              <Col xs={12} sm={6}>
                <Form.Item name="data_compra" label="Data Compra">
                  <DatePicker style={{ width: '100%' }} format="DD/MM/YYYY" />
                </Form.Item>
              </Col>
              <Col xs={12} sm={6}>
                <Form.Item name="data_entrega" label="Data Entrega">
                  <DatePicker style={{ width: '100%' }} format="DD/MM/YYYY" />
                </Form.Item>
              </Col>
              <Col xs={12} sm={6}>
                <Form.Item name="valor_unitario" label="Valor Unitário">
                  <InputNumber
                    min={0}
                    precision={2}
                    style={{ width: '100%' }}
                    formatter={(value) => `R$ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, '.')}
                    parser={(value) => value.replace(/R\$\s?|\.(?=\d{3})/g, '').replace(',', '.')}
                  />
                </Form.Item>
              </Col>
              <Col xs={12} sm={6}>
                <Form.Item name="numero_nota_fiscal" label="Nota Fiscal">
                  <Input placeholder="NF-12345" />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col xs={24}>
                <Form.Item name="fornecedor" label="Fornecedor">
                  <Input placeholder="Nome do fornecedor..." />
                </Form.Item>
              </Col>
            </Row>
          </Card>

          {/* Observações */}
          <Form.Item name="observacoes" label="Observações">
            <Input.TextArea rows={3} placeholder="Observações sobre a compra..." />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
