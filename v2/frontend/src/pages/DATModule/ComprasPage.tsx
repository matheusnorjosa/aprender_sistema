/**
 * DAT Module - Gestão de Compras/Materiais
 *
 * Interface de gestão de compras e materiais didáticos.
 * Controle de estoque, distribuição e utilização por projeto/município.
 *
 * Baseado na análise da planilha de controle - aba COMPRAS
 * 1.798 registros, 502.771 itens, 307 produtos, 94 municípios
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
  Tooltip,
  Divider,
  Row,
  Col,
  Progress,
  Radio,
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
} from '@ant-design/icons';
import type { RadioChangeEvent } from 'antd/es/radio';
import {
  listCompras,
  createCompra,
  updateCompra,
  deleteCompra,
  getMunicipiosOptions,
  getProjetosOptions,
  getProdutosOptions,
  type GenericRecord,
} from '../../api/datModule';
import {
  importCompras,
  importAcoes,
  importEventos,
  importProdutos,
  type ImportResult as OpsImportResult,
} from '../../api/ops';
import type { PaginatedResponse } from '../../types';
import { useCrudOperations } from '../../hooks/useCrudOperations';
import ImportUploader from '../../components/ImportUploader';
import type { ValidationResult, ApplyResult } from '../../components/ImportUploader';
import dayjs from 'dayjs';
import { UF_OPTIONS } from '../../constants';

const { Title, Text } = Typography;

// ============================================================
// TYPE DEFINITIONS
// ============================================================

interface CompraRecord {
  id: number;
  projeto: number;
  projeto_nome: string;
  produto: number;
  produto_nome: string;
  codigo_produto: string | null;
  tipo_compra?: string | null;
  uf: string;
  municipio: number;
  municipio_nome: string;
  quantidade: number;
  quantidade_utilizada: number | null;
  [key: string]: any;
}

interface CompraFormValues {
  projeto: number;
  produto: number;
  tipo_compra?: string | null;
  uf: string;
  municipio: number;
  quantidade: number;
  [key: string]: any;
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

interface ProdutoOption {
  id: number;
  nome: string;
}

type ViewMode = 'lista' | 'importar';

function toValidationResult(result: OpsImportResult): ValidationResult {
  return {
    stats: {
      created: result.created,
      updated: result.updated,
      unchanged: result.skipped,
    },
    errors: result.errors.map((e) => `Linha ${e.row}: ${e.message}`),
  };
}

function toApplyResult(result: OpsImportResult): ApplyResult {
  return {
    stats: {
      created: result.created,
      updated: result.updated,
      unchanged: result.skipped,
    },
  };
}

// Status options
const STATUS_OPTIONS = [
  { label: 'Disponível', value: 'disponivel', color: 'green' },
  { label: 'Em Uso', value: 'em_uso', color: 'blue' },
  { label: 'Reservado', value: 'reservado', color: 'orange' },
  { label: 'Esgotado', value: 'esgotado', color: 'red' },
];

const TIPO_COMPRA_OPTIONS = [
  { label: 'Primeira compra', value: 'primeira', color: 'blue' },
  { label: 'Compra adicional 1', value: 'adicional_1', color: 'green' },
  { label: 'Compra adicional 2', value: 'adicional_2', color: 'orange' },
  { label: 'Compra adicional 3', value: 'adicional_3', color: 'magenta' },
];

// Ano de uso options (dinâmico: ano atual ± 1)
const currentYear = new Date().getFullYear();
const ANO_OPTIONS = [currentYear - 1, currentYear, currentYear + 1].map(
  (year) => ({ label: String(year), value: year })
);

export default function ComprasPage(): JSX.Element {
  const [viewMode, setViewMode] = useState<ViewMode>('lista');

  // Issue #302: Use useCrudOperations hook for standardized CRUD
  const crud = useCrudOperations({
    listFn: listCompras as unknown as (params: { page?: number; pageSize?: number; [key: string]: unknown }) => Promise<PaginatedResponse<GenericRecord>>,
    createFn: createCompra,
    updateFn: updateCompra,
    deleteFn: deleteCompra,
    entityName: 'Compra',
    pageSize: 15,
  });

  // Filter states
  const [filters, setFilters] = useState({
    search: '',
    uf: undefined,
    municipio: undefined,
    projeto: undefined,
    produto: undefined,
    status: undefined,
    ano_uso: undefined,
    tipo_compra: undefined,
  });

  // Options for dropdowns
  const [municipios, setMunicipios] = useState<MunicipioOption[]>([]);
  const [projetos, setProjetos] = useState<ProjetoOption[]>([]);
  const [produtos, setProdutos] = useState<ProdutoOption[]>([]);

  // Modal states
  const [modalVisible, setModalVisible] = useState<boolean>(false);
  const [editingCompra, setEditingCompra] = useState<CompraRecord | null>(null);

  const [form] = Form.useForm<CompraFormValues>();

  // Load options on mount
  useEffect(() => {
    const loadOptions = async () => {
      try {
        const [munData, projData, prodData] = await Promise.all([
          getMunicipiosOptions(),
          getProjetosOptions(),
          getProdutosOptions(),
        ]);
        setMunicipios((munData as any).results || munData || []);
        setProjetos((projData as any).results || projData || []);
        setProdutos((prodData as any).results || prodData || []);
      } catch (error) {
        message.error(`Erro ao carregar opções: ${(error as Error).message}`);
      }
    };
    loadOptions();
  }, []);

  // Fetch data with filters (uses crud hook internally)
  const fetchData = useCallback(async (page = 1) => {
    const params: any = {
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
    if (filters.tipo_compra) params.tipo_compra = filters.tipo_compra;

    await crud.fetchData(params);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters]);

  // Initial load only
  useEffect(() => {
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
      tipo_compra: undefined,
    });
  };

  // CRUD handlers
  const handleCreate = () => {
    setEditingCompra(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (record: CompraRecord) => {
    setEditingCompra(record);
    form.setFieldsValue({
      ...record,
      data_compra: record.data_compra ? dayjs(record.data_compra) : null,
      data_entrega: record.data_entrega ? dayjs(record.data_entrega) : null,
    });
    setModalVisible(true);
  };

  // Issue #302: Simplified handleSave using crud hook
  const handleSave = async (values: CompraFormValues) => {
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
  const handleDelete = (record: CompraRecord) => {
    crud.confirmDelete(record, {
      nameField: 'produto_nome',
      onSuccess: () => fetchData(crud.pagination.current),
    });
  };

  // Calculate disponível
  const calcularDisponivel = (quantidade: number, utilizado: number | null): number => {
    return (quantidade || 0) - (utilizado || 0);
  };

  // Status tag renderer
  const renderStatusTag = (status: string | null, disponivel: number, quantidade: number): JSX.Element => {
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

  const renderTipoCompraTag = (tipo: string | null | undefined): JSX.Element => {
    if (!tipo) return <Tag color="default">Não informado</Tag>;
    const config = TIPO_COMPRA_OPTIONS.find((t) => t.value === tipo);
    return <Tag color={config?.color || 'default'}>{config?.label || tipo}</Tag>;
  };

  // Table columns (memoized §16 Epic #459)
  const columns = useMemo(() => [
    {
      title: 'Projeto',
      dataIndex: 'projeto_nome',
      key: 'projeto',
      width: 120,
      fixed: 'left' as const,
      render: (nome: string) => <Tag color="blue">{nome}</Tag>,
    },
    {
      title: 'Produto',
      dataIndex: 'produto_nome',
      key: 'produto',
      width: 200,
      fixed: 'left' as const,
      render: (nome: string, record: CompraRecord) => (
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
      render: (uf: string) => <Tag>{uf}</Tag>,
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
      align: 'right' as const,
      render: (val: number | null) => (
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
      align: 'right' as const,
      render: (val: number | null) => val?.toLocaleString('pt-BR') || 0,
    },
    {
      title: 'Disponível',
      key: 'disponivel',
      width: 120,
      align: 'right' as const,
      render: (_: unknown, record: CompraRecord) => {
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
      align: 'center' as const,
      render: (ano: number | null) => ano ? <Tag>{ano}</Tag> : '-',
    },
    {
      title: 'Tipo Compra',
      dataIndex: 'tipo_compra',
      key: 'tipo_compra',
      width: 140,
      render: (tipo: string | null) => renderTipoCompraTag(tipo),
    },
    {
      title: 'Status',
      key: 'status',
      width: 120,
      render: (_: unknown, record: CompraRecord) => {
        const disponivel = calcularDisponivel(record.quantidade, record.quantidade_utilizada);
        return renderStatusTag(record.status_uso, disponivel, record.quantidade);
      },
    },
    {
      title: 'Ações',
      key: 'acoes',
      width: 100,
      fixed: 'right' as const,
      render: (_: unknown, record: CompraRecord) => (
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
  ], []);

  return (
    <section className="p-6 bg-gray-100" style={{ minHeight: 'calc(100vh - 64px)' }} aria-labelledby="compras-title">
      {/* Header */}
      <header className="mb-6">
        <div className="flex flex-wrap justify-between items-start gap-3 mb-2">
          <div>
            <Title level={3} className="m-0" id="compras-title">
              <ShoppingCartOutlined className="mr-2" />
              Gestão de Compras/Materiais
            </Title>
            <Text type="secondary">
              {viewMode === 'lista'
                ? 'Controle de estoque, distribuição e utilização de materiais didáticos'
                : 'Importe dados de compras e bases relacionadas (ações, eventos e produtos).'}
            </Text>
          </div>
          <Space wrap>
            <Radio.Group
              value={viewMode}
              onChange={(event: RadioChangeEvent) => setViewMode(event.target.value)}
              buttonStyle="solid"
            >
              <Radio.Button value="lista">Lista</Radio.Button>
              <Radio.Button value="importar">Importar</Radio.Button>
            </Radio.Group>
            {viewMode === 'lista' && (
              <>
                <Button icon={<DownloadOutlined />}>Exportar</Button>
                <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
                  Nova Compra
                </Button>
              </>
            )}
          </Space>
        </div>
      </header>

      {viewMode === 'lista' ? (
        <>
      {/* Filters Card */}
      <nav aria-label="Filtros de busca">
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
              onChange={(e) => setFilters((prev: any) => ({ ...prev, search: e.target.value }))}
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
              onChange={(val) => setFilters((prev: any) => ({ ...prev, projeto: val }))}
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
              onChange={(val) => setFilters((prev: any) => ({ ...prev, produto: val }))}
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
              onChange={(val) => setFilters((prev: any) => ({ ...prev, uf: val }))}
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
              onChange={(val) => setFilters((prev: any) => ({ ...prev, municipio: val }))}
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
              onChange={(val) => setFilters((prev: any) => ({ ...prev, ano_uso: val }))}
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
              onChange={(val) => setFilters((prev: any) => ({ ...prev, status: val }))}
              options={STATUS_OPTIONS}
            />
          </Col>
          <Col xs={24} sm={12} md={8} lg={4}>
            <div className="mb-1">
              <Text type="secondary" style={{ fontSize: 12, textTransform: 'uppercase' }}>
                Tipo Compra
              </Text>
            </div>
            <Select
              style={{ width: '100%' }}
              placeholder="Todos"
              allowClear
              value={filters.tipo_compra}
              onChange={(val) => setFilters((prev: any) => ({ ...prev, tipo_compra: val }))}
              options={TIPO_COMPRA_OPTIONS}
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
      </nav>

      {/* Table Card */}
      <section aria-label="Resultados da busca">
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
          columns={columns as any}
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
            const totalQtd = pageData.reduce((sum: number, r: any) => sum + (r.quantidade || 0), 0);
            const totalUtilizado = pageData.reduce((sum: number, r: any) => sum + (r.quantidade_utilizada || 0), 0);
            const totalDisponivel = totalQtd - totalUtilizado;

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
                  <Table.Summary.Cell index={7} colSpan={4} />
                </Table.Summary.Row>
              </Table.Summary>
            );
          }}
        />
      </Card>
      </section>

      {/* Legend */}
      <aside aria-label="Legenda de status">
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
      </aside>
        </>
      ) : (
        <section aria-label="Importação de dados de compras" className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <ImportUploader
            label="Importar COMPRAS"
            description="CSV/XLSX com colunas: codigo, produto, quant, municipio, uf, data, uso"
            onDryRun={async (file: File) => toValidationResult(await importCompras(file, true))}
            onApply={async (file: File) => {
              const result = await importCompras(file, false);
              await fetchData(1);
              return toApplyResult(result);
            }}
          />

          <ImportUploader
            label="Importar AÇÕES"
            description="CSV/XLSX de Ações de Controle (Município, Projeto, Coordenador, Datas, Observação)"
            onDryRun={async (file: File) => toValidationResult(await importAcoes(file, true))}
            onApply={async (file: File) => toApplyResult(await importAcoes(file, false))}
          />

          <ImportUploader
            label="Importar EVENTOS"
            description="CSV/XLSX: municipio, projeto, tipo_evento, data, hora_inicio, hora_fim, coordenador, formador1-5"
            onDryRun={async (file: File) => toValidationResult(await importEventos(file, true))}
            onApply={async (file: File) => toApplyResult(await importEventos(file, false))}
          />

          <ImportUploader
            label="Importar PRODUTOS"
            description="CSV/XLSX: codigo, nome, projeto (obrigatórios), descricao (opcional)"
            onDryRun={async (file: File) => toValidationResult(await importProdutos(file, true))}
            onApply={async (file: File) => toApplyResult(await importProdutos(file, false))}
          />
        </section>
      )}

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
        <Form form={form} layout="vertical" autoComplete="off" onFinish={handleSave}>
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
                <Form.Item
                  name="tipo_compra"
                  label="Tipo de Compra"
                  rules={[{ required: true, message: 'Selecione o tipo de compra' }]}
                >
                  <Select placeholder="Selecione..." options={TIPO_COMPRA_OPTIONS} />
                </Form.Item>
              </Col>
              <Col xs={12} sm={6}>
                <Form.Item name="data_entrega" label="Data Entrega">
                  <DatePicker style={{ width: '100%' }} format="DD/MM/YYYY" />
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
    </section>
  );
}
