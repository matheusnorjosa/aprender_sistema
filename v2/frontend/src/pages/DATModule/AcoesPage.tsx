/**
 * DAT Module - Gestão de Ações
 *
 * Interface de gestão do ciclo de vida de projetos por município.
 * Fluxo: Carta → Contato → Reunião → Entrega
 *
 * Baseado na análise da planilha de controle - aba AÇÕES
 * 688 registros, 103 municípios, 88 projetos, 28 coordenadores
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useTableFilters, type TableFilterParams } from '../../hooks/useTableFilters';
import type { PaginatedResponse } from '../../types';
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
import { UF_OPTIONS } from '../../constants';

const { Title, Text } = Typography;

// ============================================================
// TYPE DEFINITIONS
// ============================================================

interface AcaoRecord {
  id: number;
  municipio: number;
  municipio_nome: string;
  municipio_uf: string;
  projeto: number;
  projeto_nome: string;
  coordenador: number | null;
  coordenador_nome: string | null;
  [key: string]: any;
}

interface AcaoFormValues {
  municipio: number;
  projeto: number;
  coordenador: number | null;
  [key: string]: any;
}

interface AcoesFilters {
  search: string;
  uf: string | undefined;
  municipio: number | undefined;
  projeto: number | undefined;
  coordenador: number | undefined;
  status_geral: string | undefined;
}

interface AcoesStats {
  total: number;
  cartas_enviadas: number;
  reunioes_realizadas: number;
  entregas_concluidas: number;
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


// Status options para cada etapa
const STATUS_OPTIONS = [
  { label: 'Pendente', value: 'pendente' },
  { label: 'Em Andamento', value: 'em_andamento' },
  { label: 'Concluído', value: 'concluido' },
  { label: 'N/A', value: 'na' },
];

const DEFAULT_FILTERS: AcoesFilters = {
  search: '',
  uf: undefined,
  municipio: undefined,
  projeto: undefined,
  coordenador: undefined,
  status_geral: undefined,
};

// Backend filterset (DATAcaoFilter) expõe `municipio`, `projeto`, `coordenador`
// (sem sufixo `_id`). Manter chaves alinhadas aqui — vide v2/backend/.../dat_module.py:195.
const buildAcoesParams = (f: AcoesFilters): TableFilterParams => ({
  ...(f.search && { search: f.search }),
  ...(f.uf && { uf: f.uf }),
  ...(f.municipio !== undefined && { municipio: f.municipio }),
  ...(f.projeto !== undefined && { projeto: f.projeto }),
  ...(f.coordenador !== undefined && { coordenador: f.coordenador }),
  ...(f.status_geral && { status_geral: f.status_geral }),
});

export default function AcoesPage(): JSX.Element {
  const {
    data: acoes,
    stats,
    loading,
    filters,
    setFilters,
    pagination,
    fetchData,
    handleClearFilters,
    handleTableChange,
    refresh,
  } = useTableFilters<AcoesFilters, AcaoRecord, AcoesStats>({
    defaultFilters: DEFAULT_FILTERS,
    listFn: listAcoes as unknown as (params: TableFilterParams) => Promise<PaginatedResponse<AcaoRecord>>,
    statsFn: getAcoesStats as unknown as (params: TableFilterParams) => Promise<AcoesStats>,
    buildParams: buildAcoesParams,
    defaultOrdering: '-updated_at',
    entityName: 'ações',
  });

  // Options for dropdowns
  const [municipios, setMunicipios] = useState<MunicipioOption[]>([]);
  const [projetos, setProjetos] = useState<ProjetoOption[]>([]);
  const [coordenadores, setCoordenadores] = useState<CoordenadorOption[]>([]);

  // Modal states
  const [modalVisible, setModalVisible] = useState<boolean>(false);
  const [editingAcao, setEditingAcao] = useState<AcaoRecord | null>(null);

  const [form] = Form.useForm<AcaoFormValues>();

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

  // CRUD handlers
  const handleCreate = () => {
    setEditingAcao(null);
    form.resetFields();
    setModalVisible(true);
  };

  // Memoized handlers (§3 Epic #459)
  const handleEdit = useCallback((record: AcaoRecord) => {
    setEditingAcao(record);
    form.setFieldsValue({
      ...record,
      data_carta: record.data_carta ? dayjs(record.data_carta) : null,
      data_contato: record.data_contato ? dayjs(record.data_contato) : null,
      data_reuniao: record.data_reuniao ? dayjs(record.data_reuniao) : null,
      data_entrega: record.data_entrega ? dayjs(record.data_entrega) : null,
    });
    setModalVisible(true);
  }, [form]);

  const handleSave = async (values: AcaoFormValues) => {
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
      void refresh();
    } catch (error) {
      message.error(`Erro: ${(error as Error).message}`);
    }
  };

  const handleDelete = useCallback((record: AcaoRecord) => {
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
          void refresh();
        } catch (error) {
          message.error(`Erro ao excluir: ${(error as Error).message}`);
        }
      },
    });
  }, [refresh]);

  // Status icon renderer - memoized (§3 Epic #459)
  const renderStatusIcon = useCallback((status: string | null) => {
    switch (status) {
      case 'concluido':
        return <CheckCircleFilled className="text-green-500 text-lg" />;
      case 'em_andamento':
        return <ClockCircleFilled className="text-blue-500 text-lg" />;
      case 'pendente':
        return <ExclamationCircleFilled className="text-yellow-500 text-lg" />;
      case 'na':
        return <MinusCircleFilled className="text-gray-400 text-lg" />;
      default:
        return <MinusCircleFilled className="text-gray-400 text-lg" />;
    }
  }, []);

  // Calculate progress based on status - memoized (§3 Epic #459)
  const calculateProgress = useCallback((record: AcaoRecord) => {
    const etapas = [
      record.status_carta,
      record.status_contato,
      record.status_reuniao,
      record.status_entrega,
    ];
    const concluidas = etapas.filter((s) => s === 'concluido').length;
    return Math.round((concluidas / 4) * 100);
  }, []);

  // Table columns - memoized to prevent re-renders (§3 Epic #459)
  const columns = useMemo(() => [
    {
      title: 'Município - UF',
      key: 'municipio_uf',
      width: 180,
      fixed: 'left' as const,
      render: (_: unknown, record: AcaoRecord) => (
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
      render: (nome: string) => <Tag color="blue">{nome}</Tag>,
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
      align: 'center' as const,
      render: (_: unknown, record: AcaoRecord) => (
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
      align: 'center' as const,
      render: (_: unknown, record: AcaoRecord) => (
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
      align: 'center' as const,
      render: (_: unknown, record: AcaoRecord) => (
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
      align: 'center' as const,
      render: (_: unknown, record: AcaoRecord) => (
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
      render: (_: unknown, record: AcaoRecord) => {
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
      render: (val: string | null) => (
        <Tooltip title={val}>
          <Text type="secondary">{val || '-'}</Text>
        </Tooltip>
      ),
    },
    {
      title: 'Ações',
      key: 'acoes',
      width: 100,
      fixed: 'right' as const,
      render: (_: unknown, record: AcaoRecord) => (
        <Space size="small">
          <Tooltip title="Editar">
            <Button
              type="text"
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
              aria-label="Editar ação"
            />
          </Tooltip>
          <Tooltip title="Excluir">
            <Button
              type="text"
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(record)}
              aria-label="Excluir ação"
            />
          </Tooltip>
        </Space>
      ),
    },
  ], [handleEdit, handleDelete, renderStatusIcon, calculateProgress]);

  return (
    <section className="p-6 bg-gray-100" style={{ minHeight: 'calc(100vh - 64px)' }} aria-labelledby="acoes-title">
      {/* Header */}
      <header className="mb-6">
        <div className="flex justify-between items-start mb-2">
          <div>
            <Title level={3} className="m-0" id="acoes-title">
              <RocketOutlined className="mr-2" />
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
      </header>

      {/* Stats Cards */}
      {stats && (
        <Row gutter={16} className="mb-4">
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
              <Tooltip title="Aguardando reprocessamento dos dados (parser de etapas Carta/Contato/Reunião/Entrega)">
                <Statistic
                  title="Cartas Enviadas"
                  value="—"
                  valueStyle={{ color: '#bfbfbf' }}
                  prefix={<MailOutlined />}
                />
              </Tooltip>
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Tooltip title="Aguardando reprocessamento dos dados (parser de etapas Carta/Contato/Reunião/Entrega)">
                <Statistic
                  title="Reuniões Realizadas"
                  value="—"
                  valueStyle={{ color: '#bfbfbf' }}
                  prefix={<TeamOutlined />}
                />
              </Tooltip>
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Tooltip title="Aguardando reprocessamento dos dados (parser de etapas Carta/Contato/Reunião/Entrega)">
                <Statistic
                  title="Entregas Concluídas"
                  value="—"
                  valueStyle={{ color: '#bfbfbf' }}
                  prefix={<CheckCircleFilled />}
                />
              </Tooltip>
            </Card>
          </Col>
        </Row>
      )}

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
              placeholder="Município, projeto..."
              allowClear
              value={filters.search}
              onChange={(e) => setFilters((prev) => ({ ...prev, search: e.target.value }))}
              onSearch={() => fetchData(1)}
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
            <div className="mb-1">
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
            <Text strong>Resultados:</Text>
            <Text type="danger" strong>{pagination.total}</Text>
            <Text>ações</Text>
          </Space>
        }
      >
        {/* Column Group Headers */}
        <div
          className="flex text-xs font-semibold uppercase bg-gray-50"
          style={{ borderBottom: '1px solid #f0f0f0' }}
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
          columns={columns as any}
          dataSource={acoes}
          rowKey="id"
          loading={loading}
          scroll={{ x: 1400 }}
          pagination={{
            ...pagination,
            showSizeChanger: true,
            showTotal: (total, range) => `Mostrando ${range[0]} a ${range[1]} de ${total} ações`,
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
            Legenda:
          </Text>
          <Space>
            <CheckCircleFilled className="text-green-500" />
            <Text type="secondary">Concluído</Text>
          </Space>
          <Space>
            <ClockCircleFilled className="text-blue-500" />
            <Text type="secondary">Em Andamento</Text>
          </Space>
          <Space>
            <ExclamationCircleFilled className="text-yellow-500" />
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
          <div className="flex justify-between">
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
        <Form form={form} layout="vertical" autoComplete="off" onFinish={handleSave}>
          {/* Dados Básicos */}
          <Card size="small" title="Identificação" className="mb-4">
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
          <Card size="small" title="Fluxo de Acompanhamento" className="mb-4">
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
    </section>
  );
}
