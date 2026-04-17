/**
 * DAT Module - Gestão de Coordenadores
 *
 * Issue #303: Refactored - extracted constants, columns, and helpers to ./Coordenadores/
 *
 * Interface de gestão de coordenadores e suas áreas de atuação.
 * Alocação por área, projetos e municípios, visualização de carga de trabalho.
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
  Avatar,
  Tooltip,
  Divider,
  Row,
  Col,
  Statistic,
  Progress,
  DatePicker,
  Collapse,
  List,
  Switch,
} from 'antd';
import {
  ReloadOutlined,
  EditOutlined,
  PlusOutlined,
  DeleteOutlined,
  DownloadOutlined,
  FilterOutlined,
  ClearOutlined,
  TeamOutlined,
  AppstoreOutlined,
  TableOutlined,
  EnvironmentOutlined,
  ProjectOutlined,
  BarsOutlined,
  EyeOutlined,
  CheckCircleOutlined,
  PhoneOutlined,
  MailOutlined,
} from '@ant-design/icons';
import {
  listCoordenadoresDAT,
  createCoordenadorDAT,
  updateCoordenadorDAT,
  deleteCoordenadorDAT,
  getCoordenadorAlocacoes,
  getAreasOptions,
  getProjetosOptions,
  getMunicipiosOptions,
} from '../../api/datModule';
import dayjs from 'dayjs';
import logger from '../../utils/logger';
import {
  AREAS_DEFAULT,
  AREA_COLORS,
  DEFAULT_FILTERS,
  VIEW_MODES,
} from './Coordenadores/constants';
import { getColumns, type CoordenadorRecord } from './Coordenadores/columns';
import { getAreaColor, getInitials, groupByArea } from './Coordenadores/helpers';

const { Title, Text } = Typography;

// ============================================================
// TYPE DEFINITIONS
// ============================================================

interface CoordenadoresFilters {
  search: string;
  area: string | undefined;
  ativo: boolean | undefined;
}

interface CoordenadorFormValues {
  nome: string;
  area: string | null;
  cargo: string | null;
  ativo: boolean;
  [key: string]: any;
}

interface CoordenadoresStats {
  total: number;
  ativos: number;
  areas: number;
  media_projetos: string | number;
}

interface PaginationState {
  current: number;
  pageSize: number;
  total: number;
}

interface AreaOption {
  id: number;
  nome: string;
}

interface AlocacaoRecord {
  id: number;
  projeto_nome: string;
  projeto: string;
  municipio_nome: string;
  municipio: string;
  uf: string | null;
}

const { Panel } = Collapse;

export default function CoordenadoresPage(): JSX.Element {
  const [coordenadores, setCoordenadores] = useState<CoordenadorRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [pagination, setPagination] = useState<PaginationState>({ current: 1, pageSize: 15, total: 0 });
  const [stats, setStats] = useState<CoordenadoresStats | null>(null);
  const [viewMode, setViewMode] = useState<string>(VIEW_MODES.CARDS);

  // Filter states - using DEFAULT_FILTERS from constants
  const [filters, setFilters] = useState<CoordenadoresFilters>(DEFAULT_FILTERS as CoordenadoresFilters);

  // Options for dropdowns (projetos/municipios reserved for future use)
  const [areas, setAreas] = useState<(AreaOption | string)[]>([]);
  const [_projetos, setProjetos] = useState<any[]>([]);
  const [_municipios, setMunicipios] = useState<any[]>([]);

  // Modal states
  const [modalVisible, setModalVisible] = useState<boolean>(false);
  const [detailModalVisible, setDetailModalVisible] = useState<boolean>(false);
  const [editingCoordenador, setEditingCoordenador] = useState<CoordenadorRecord | null>(null);
  const [viewingCoordenador, setViewingCoordenador] = useState<CoordenadorRecord | null>(null);
  const [alocacoes, setAlocacoes] = useState<AlocacaoRecord[]>([]);
  const [loadingAlocacoes, setLoadingAlocacoes] = useState<boolean>(false);

  const [form] = Form.useForm<CoordenadorFormValues>();

  // Load options on mount
  useEffect(() => {
    const loadOptions = async () => {
      try {
        const [areasData, projData, munData] = await Promise.all([
          getAreasOptions().catch((): AreaOption[] => []),
          getProjetosOptions(),
          getMunicipiosOptions(),
        ]);

        // Use áreas da API ou padrão
        const areasList = ((areasData as any).results || areasData || []).length > 0
          ? (areasData as any).results || areasData
          : AREAS_DEFAULT.map((a, i) => ({ id: i + 1, nome: a }));

        setAreas(areasList);
        setProjetos((projData as any).results || projData || []);
        setMunicipios((munData as any).results || munData || []);
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
      const params: Record<string, string | number | boolean> = {
        page,
        page_size: pagination.pageSize,
        ordering: 'nome',
      };

      // Apply filters
      if (filters.search) params.search = filters.search;
      if (filters.area) params.area = filters.area;
      if (filters.ativo !== undefined) params.ativo = filters.ativo;

      const data = await listCoordenadoresDAT(params);

      const results = (data as any).results || data || [];
      setCoordenadores((results as any) as CoordenadorRecord[]);
      setPagination((prev) => ({
        ...prev,
        current: page,
        total: (data as any).count || (results as any[]).length,
      }));

      // Calculate stats
      const ativos = (results as any[]).filter((c) => c.ativo !== false).length;
      const areasUnicas = [...new Set((results as any[]).map((c) => c.area))].filter(Boolean).length;
      const totalProjetos = (results as any[]).reduce((sum, c) => sum + (c.total_projetos || 0), 0);
      const mediaProjetos = (results as any[]).length > 0 ? (totalProjetos / (results as any[]).length).toFixed(1) : 0;

      setStats({
        total: (data as any).count || (results as any[]).length,
        ativos,
        areas: areasUnicas,
        media_projetos: mediaProjetos,
      });
    } catch (error) {
      message.error(`Erro ao carregar dados: ${(error as Error).message}`);
    } finally {
      setLoading(false);
    }
  }, [filters, pagination.pageSize]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Clear all filters
  const handleClearFilters = () => {
    setFilters(DEFAULT_FILTERS);
  };

  // Load alocações for detail view
  const loadAlocacoes = async (coordenadorId: number) => {
    setLoadingAlocacoes(true);
    try {
      const data = await getCoordenadorAlocacoes(coordenadorId);
      setAlocacoes((data as any).results || data || []);
    } catch (error) {
      logger.error('Erro ao carregar alocações:', error);
      setAlocacoes([]);
    } finally {
      setLoadingAlocacoes(false);
    }
  };

  // CRUD handlers
  const handleCreate = () => {
    setEditingCoordenador(null);
    form.resetFields();
    form.setFieldsValue({ ativo: true });
    setModalVisible(true);
  };

  // Memoized handlers (§2 Epic #459)
  const handleEdit = useCallback((record: CoordenadorRecord) => {
    setEditingCoordenador(record);
    form.setFieldsValue({
      ...record,
      data_admissao: record.data_admissao ? dayjs(record.data_admissao) : null,
    });
    setModalVisible(true);
  }, [form]);

  const handleView = useCallback(async (record: CoordenadorRecord) => {
    setViewingCoordenador(record);
    setDetailModalVisible(true);
    await loadAlocacoes(record.id);
  }, []);

  const handleSave = async (values: CoordenadorFormValues) => {
    try {
      const payload = {
        ...values,
        data_admissao: values.data_admissao?.format('YYYY-MM-DD') || null,
      };

      if (editingCoordenador) {
        await updateCoordenadorDAT(editingCoordenador.id, payload);
        message.success('Coordenador atualizado com sucesso');
      } else {
        await createCoordenadorDAT(payload);
        message.success('Coordenador criado com sucesso');
      }
      setModalVisible(false);
      form.resetFields();
      fetchData(pagination.current);
    } catch (error) {
      message.error(`Erro: ${(error as Error).message}`);
    }
  };

  const handleDelete = useCallback((record: CoordenadorRecord) => {
    Modal.confirm({
      title: 'Confirmar exclusão',
      content: (
        <div>
          <p>Excluir coordenador <strong>"{record.nome}"</strong>?</p>
          {((record.total_municipios ?? 0) > 0 || (record.total_projetos ?? 0) > 0) && (
            <Text type="danger">
              Atenção: Este coordenador possui alocações ativas.
            </Text>
          )}
        </div>
      ),
      okText: 'Sim, excluir',
      okType: 'danger',
      cancelText: 'Cancelar',
      onOk: async () => {
        try {
          await deleteCoordenadorDAT(record.id);
          message.success('Coordenador excluído com sucesso');
          fetchData(pagination.current);
        } catch (error) {
          message.error(`Erro ao excluir: ${(error as Error).message}`);
        }
      },
    });
  }, [fetchData, pagination.current]);

  const handleToggleAtivo = useCallback(async (record: CoordenadorRecord) => {
    try {
      await updateCoordenadorDAT(record.id, { ativo: !record.ativo });
      message.success(`Coordenador ${record.ativo ? 'desativado' : 'ativado'}`);
      fetchData(pagination.current);
    } catch (error) {
      message.error(`Erro: ${(error as Error).message}`);
    }
  }, [fetchData, pagination.current]);

  // Issue #303: Helper functions extracted to ./Coordenadores/helpers.js
  // Group coordenadores by area using extracted helper - memoized (§2 Epic #459)
  const coordenadoresByArea = useMemo(
    () => groupByArea(coordenadores as any),
    [coordenadores]
  );

  // Issue #303: Column definitions extracted to ./Coordenadores/columns.jsx
  // Memoized to prevent re-renders (§2 Epic #459)
  const columns = useMemo(
    () => getColumns({
      onView: handleView,
      onEdit: handleEdit,
      onDelete: handleDelete,
      onToggleAtivo: handleToggleAtivo,
    }),
    [handleView, handleEdit, handleDelete, handleToggleAtivo]
  );

  // Card view renderer
  const renderCardView = () => (
    <Row gutter={[16, 16]}>
      {coordenadores.map((coord) => (
        <Col xs={24} sm={12} md={8} lg={6} key={coord.id}>
          <Card
            hoverable
            style={{
              opacity: coord.ativo === false ? 0.6 : 1,
              borderLeft: `4px solid ${coord.area && AREA_COLORS[coord.area] ? `var(--ant-${AREA_COLORS[coord.area]}-color)` : '#d9d9d9'}`,
            }}
            actions={[
              <Tooltip key="view" title="Ver detalhes">
                <EyeOutlined onClick={() => handleView(coord)} />
              </Tooltip>,
              <Tooltip key="edit" title="Editar">
                <EditOutlined onClick={() => handleEdit(coord)} />
              </Tooltip>,
              <Tooltip key="delete" title="Excluir">
                <DeleteOutlined onClick={() => handleDelete(coord)} />
              </Tooltip>,
            ]}
          >
            <Card.Meta
              avatar={
                <Avatar
                  src={coord.foto_url}
                  size={64}
                  style={{ backgroundColor: getAreaColor(coord.area) }}
                >
                  {getInitials(coord.nome)}
                </Avatar>
              }
              title={
                <div>
                  {coord.nome}
                  {coord.ativo === false && (
                    <Tag color="default" style={{ marginLeft: 8 }}>
                      Inativo
                    </Tag>
                  )}
                </div>
              }
              description={
                <div>
                  <Tag color={getAreaColor(coord.area)}>{coord.area || 'Sem área'}</Tag>
                  {coord.cargo && <Text type="secondary" style={{ fontSize: 12 }}> - {coord.cargo}</Text>}
                </div>
              }
            />
            <Divider style={{ margin: '12px 0' }} />
            <Space direction="vertical" size={2} style={{ width: '100%' }}>
              {coord.telefone && (
                <Text style={{ fontSize: 12 }}>
                  <PhoneOutlined style={{ marginRight: 4 }} />
                  {coord.telefone}
                </Text>
              )}
              {coord.email && (
                <Text style={{ fontSize: 12 }} ellipsis>
                  <MailOutlined style={{ marginRight: 4 }} />
                  {coord.email}
                </Text>
              )}
              <Divider style={{ margin: '8px 0' }} />
              <Row gutter={8}>
                <Col span={12}>
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    <EnvironmentOutlined /> {coord.total_municipios || 0} municípios
                  </Text>
                </Col>
                <Col span={12}>
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    <ProjectOutlined /> {coord.total_projetos || 0} projetos
                  </Text>
                </Col>
              </Row>
            </Space>
          </Card>
        </Col>
      ))}
    </Row>
  );

  // Area view renderer
  const renderAreaView = () => (
    <Collapse defaultActiveKey={Object.keys(coordenadoresByArea)}>
      {Object.entries(coordenadoresByArea).map(([area, coords]: [string, any[]]) => (
        <Panel
          key={area}
          header={
            <Space>
              <Tag color={getAreaColor(area)}>{area}</Tag>
              <Text strong>{coords.length}</Text>
              <Text type="secondary">coordenador{coords.length !== 1 ? 'es' : ''}</Text>
            </Space>
          }
        >
          <List
            grid={{ gutter: 16, xs: 1, sm: 2, md: 3, lg: 4 }}
            dataSource={coords}
            renderItem={(coord) => (
              <List.Item>
                <Card
                  size="small"
                  hoverable
                  onClick={() => handleView(coord)}
                  style={{ opacity: coord.ativo === false ? 0.6 : 1 }}
                >
                  <Space>
                    <Avatar
                      src={coord.foto_url}
                      style={{ backgroundColor: getAreaColor(area) }}
                    >
                      {getInitials(coord.nome)}
                    </Avatar>
                    <div>
                      <Text strong>{coord.nome}</Text>
                      <div>
                        <Text type="secondary" style={{ fontSize: 11 }}>
                          {coord.total_municipios || 0} mun. | {coord.total_projetos || 0} proj.
                        </Text>
                      </div>
                    </div>
                  </Space>
                </Card>
              </List.Item>
            )}
          />
        </Panel>
      ))}
    </Collapse>
  );

  return (
    <section className="p-6 bg-gray-100" style={{ minHeight: 'calc(100vh - 64px)' }} aria-labelledby="coordenadores-title">
      {/* Header */}
      <header className="mb-6">
        <div className="flex justify-between items-start mb-2">
          <div>
            <Title level={3} className="m-0" id="coordenadores-title">
              <TeamOutlined className="mr-2" />
              Gestão de Coordenadores
            </Title>
            <Text type="secondary">
              Cadastro e alocação de coordenadores por área e projeto
            </Text>
          </div>
          <Space>
            <Button.Group>
              <Tooltip title="Cards">
                <Button
                  type={viewMode === 'cards' ? 'primary' : 'default'}
                  icon={<AppstoreOutlined />}
                  onClick={() => setViewMode('cards')}
                  aria-label="Visualizar como cards"
                />
              </Tooltip>
              <Tooltip title="Lista">
                <Button
                  type={viewMode === 'table' ? 'primary' : 'default'}
                  icon={<TableOutlined />}
                  onClick={() => setViewMode('table')}
                  aria-label="Visualizar como lista"
                />
              </Tooltip>
              <Tooltip title="Por Área">
                <Button
                  type={viewMode === 'area' ? 'primary' : 'default'}
                  icon={<BarsOutlined />}
                  onClick={() => setViewMode('area')}
                  aria-label="Visualizar por área"
                />
              </Tooltip>
            </Button.Group>
            <Button icon={<DownloadOutlined />}>Exportar</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              Novo Coordenador
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
                title="Total Coordenadores"
                value={stats.total}
                prefix={<TeamOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="Ativos"
                value={stats.ativos}
                suffix={
                  <Text type="secondary" style={{ fontSize: 14 }}>
                    ({stats.total > 0 ? ((stats.ativos / stats.total) * 100).toFixed(0) : 0}%)
                  </Text>
                }
                valueStyle={{ color: '#52c41a' }}
                prefix={<CheckCircleOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="Áreas"
                value={stats.areas}
                valueStyle={{ color: '#1890ff' }}
                prefix={<BarsOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="Média de Projetos"
                value={stats.media_projetos}
                suffix="por coord."
                prefix={<ProjectOutlined />}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* Filters Card */}
      <nav aria-label="Filtros de busca">
      <Card style={{ marginBottom: 16 }} bodyStyle={{ paddingBottom: 12 }}>
        <Row gutter={[16, 16]} align="bottom">
          <Col xs={24} sm={12} md={8} lg={6}>
            <div className="mb-1">
              <Text type="secondary" style={{ fontSize: 12, textTransform: 'uppercase' }}>
                Buscar
              </Text>
            </div>
            <Input.Search
              placeholder="Nome, email..."
              allowClear
              value={filters.search}
              onChange={(e) => setFilters((prev) => ({ ...prev, search: e.target.value }))}
              onSearch={() => fetchData(1)}
            />
          </Col>
          <Col xs={12} sm={6} md={4} lg={4}>
            <div style={{ marginBottom: 4 }}>
              <Text type="secondary" style={{ fontSize: 12, textTransform: 'uppercase' }}>
                Área
              </Text>
            </div>
            <Select
              style={{ width: '100%' }}
              placeholder="Todas"
              allowClear
              showSearch
              value={filters.area}
              onChange={(val) => setFilters((prev) => ({ ...prev, area: val }))}
              options={areas.map((a) => ({
                label: typeof a === 'string' ? a : a.nome,
                value: typeof a === 'string' ? a : a.nome,
              }))}
            />
          </Col>
          <Col xs={12} sm={6} md={4} lg={4}>
            <div style={{ marginBottom: 4 }}>
              <Text type="secondary" style={{ fontSize: 12, textTransform: 'uppercase' }}>
                Status
              </Text>
            </div>
            <Select
              style={{ width: '100%' }}
              placeholder="Todos"
              allowClear
              value={filters.ativo}
              onChange={(val) => setFilters((prev) => ({ ...prev, ativo: val }))}
              options={[
                { label: 'Ativos', value: true },
                { label: 'Inativos', value: false },
              ]}
            />
          </Col>
          <Col flex="auto">
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
          </Col>
        </Row>
      </Card>
      </nav>

      {/* Content - Cards, Table or Area View */}
      <section aria-label="Lista de coordenadores">
      {viewMode === 'table' ? (
        <Card
          bodyStyle={{ padding: 0 }}
          title={
            <Space>
              <Text strong>Coordenadores:</Text>
              <Text type="danger" strong>{pagination.total}</Text>
              <Text>registros</Text>
            </Space>
          }
        >
          <Table
            columns={columns as any}
            dataSource={coordenadores}
            rowKey="id"
            loading={loading}
            scroll={{ x: 1200 }}
            pagination={{
              ...pagination,
              showSizeChanger: true,
              showTotal: (total, range) => `Mostrando ${range[0]} a ${range[1]} de ${total} coordenadores`,
              onChange: (page, pageSize) => {
                setPagination((prev) => ({ ...prev, current: page, pageSize }));
                fetchData(page);
              },
            }}
            size="middle"
          />
        </Card>
      ) : viewMode === 'area' ? (
        <Card title="Coordenadores por Área">
          {renderAreaView()}
        </Card>
      ) : (
        <Card
          title={
            <Space>
              <Text strong>Coordenadores:</Text>
              <Text type="danger" strong>{pagination.total}</Text>
              <Text>registros</Text>
            </Space>
          }
        >
          {loading ? (
            <div style={{ textAlign: 'center', padding: 40 }}>
              <Text type="secondary">Carregando...</Text>
            </div>
          ) : coordenadores.length > 0 ? (
            renderCardView()
          ) : (
            <div style={{ textAlign: 'center', padding: 40 }}>
              <Text type="secondary">Nenhum coordenador encontrado</Text>
            </div>
          )}
        </Card>
      )}
      </section>

      {/* Create/Edit Modal */}
      <Modal
        title={
          <div>
            <Title level={4} className="m-0">
              {editingCoordenador ? 'Editar Coordenador' : 'Novo Coordenador'}
            </Title>
            <Text type="secondary" style={{ fontSize: 13 }}>
              Dados do coordenador e informações de contato
            </Text>
          </div>
        }
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={
          <div className="flex justify-between">
            <div>
              {editingCoordenador && (
                <Button
                  danger
                  type="text"
                  icon={<DeleteOutlined />}
                  onClick={() => {
                    setModalVisible(false);
                    handleDelete(editingCoordenador);
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
        width={700}
        styles={{ body: { maxHeight: 'calc(100vh - 250px)', overflowY: 'auto' } }}
      >
        <Form form={form} layout="vertical" autoComplete="off" onFinish={handleSave}>
          {/* Dados Pessoais */}
          <Card size="small" title="Dados Pessoais" className="mb-4">
            <Row gutter={16}>
              <Col xs={24} sm={16}>
                <Form.Item
                  name="nome"
                  label="Nome Completo"
                  rules={[{ required: true, message: 'Informe o nome' }]}
                >
                  <Input placeholder="Nome completo do coordenador" />
                </Form.Item>
              </Col>
              <Col xs={24} sm={8}>
                <Form.Item name="ativo" label="Status" valuePropName="checked">
                  <Switch
                    checkedChildren="Ativo"
                    unCheckedChildren="Inativo"
                    defaultChecked
                  />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col xs={24} sm={12}>
                <Form.Item
                  name="area"
                  label="Área de Atuação"
                  rules={[{ required: true, message: 'Selecione a área' }]}
                >
                  <Select
                    placeholder="Selecione..."
                    showSearch
                    options={areas.map((a) => ({
                      label: typeof a === 'string' ? a : a.nome,
                      value: typeof a === 'string' ? a : a.nome,
                    }))}
                  />
                </Form.Item>
              </Col>
              <Col xs={24} sm={12}>
                <Form.Item name="cargo" label="Cargo">
                  <Input placeholder="Ex: Coordenador, Gerente..." />
                </Form.Item>
              </Col>
            </Row>
            <Form.Item name="data_admissao" label="Data de Admissão">
              <DatePicker style={{ width: '100%' }} format="DD/MM/YYYY" />
            </Form.Item>
          </Card>

          {/* Contato */}
          <Card size="small" title="Contato" className="mb-4">
            <Row gutter={16}>
              <Col xs={24} sm={12}>
                <Form.Item
                  name="email"
                  label="Email Principal"
                  rules={[
                    { type: 'email', message: 'Email inválido' },
                  ]}
                >
                  <Input placeholder="email@exemplo.com" prefix={<MailOutlined />} />
                </Form.Item>
              </Col>
              <Col xs={24} sm={12}>
                <Form.Item name="email_alternativo" label="Email Alternativo">
                  <Input placeholder="email@exemplo.com" prefix={<MailOutlined />} />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col xs={24} sm={12}>
                <Form.Item name="telefone" label="Telefone Principal">
                  <Input placeholder="(00) 00000-0000" prefix={<PhoneOutlined />} />
                </Form.Item>
              </Col>
              <Col xs={24} sm={12}>
                <Form.Item name="telefone_alternativo" label="Telefone Alternativo">
                  <Input placeholder="(00) 00000-0000" prefix={<PhoneOutlined />} />
                </Form.Item>
              </Col>
            </Row>
          </Card>

          {/* Observações */}
          <Form.Item name="observacoes" label="Observações">
            <Input.TextArea rows={3} placeholder="Observações sobre o coordenador..." />
          </Form.Item>
        </Form>
      </Modal>

      {/* Detail Modal */}
      <Modal
        title={null}
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={
          <Space>
            <Button onClick={() => setDetailModalVisible(false)}>Fechar</Button>
            <Button
              type="primary"
              icon={<EditOutlined />}
              onClick={() => {
                setDetailModalVisible(false);
                if (viewingCoordenador) {
                  handleEdit(viewingCoordenador);
                }
              }}
            >
              Editar
            </Button>
          </Space>
        }
        width={800}
      >
        {viewingCoordenador && (
          <div>
            {/* Header */}
            <div className="flex gap-4 mb-6">
              <Avatar
                src={viewingCoordenador.foto_url}
                size={80}
                style={{ backgroundColor: getAreaColor(viewingCoordenador.area) }}
              >
                {getInitials(viewingCoordenador.nome)}
              </Avatar>
              <div>
                <Title level={4} style={{ margin: 0 }}>
                  {viewingCoordenador.nome}
                </Title>
                <Space>
                  <Tag color={getAreaColor(viewingCoordenador.area)}>
                    {viewingCoordenador.area}
                  </Tag>
                  {viewingCoordenador.cargo && (
                    <Text type="secondary">{viewingCoordenador.cargo}</Text>
                  )}
                  {viewingCoordenador.ativo === false && (
                    <Tag color="default">Inativo</Tag>
                  )}
                </Space>
                <div style={{ marginTop: 8 }}>
                  {viewingCoordenador.telefone && (
                    <Text style={{ marginRight: 16 }}>
                      <PhoneOutlined /> {viewingCoordenador.telefone}
                    </Text>
                  )}
                  {viewingCoordenador.email && (
                    <Text>
                      <MailOutlined /> {viewingCoordenador.email}
                    </Text>
                  )}
                </div>
                {viewingCoordenador.data_admissao && (
                  <div style={{ marginTop: 4 }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      Desde: {dayjs(viewingCoordenador.data_admissao).format('DD/MM/YYYY')}
                    </Text>
                  </div>
                )}
              </div>
            </div>

            {/* Stats */}
            <Row gutter={16} className="mb-6">
              <Col span={8}>
                <Card size="small">
                  <Statistic
                    title="Projetos"
                    value={viewingCoordenador.total_projetos || 0}
                    prefix={<ProjectOutlined />}
                  />
                </Card>
              </Col>
              <Col span={8}>
                <Card size="small">
                  <Statistic
                    title="Municípios"
                    value={viewingCoordenador.total_municipios || 0}
                    prefix={<EnvironmentOutlined />}
                  />
                </Card>
              </Col>
              <Col span={8}>
                <Card size="small">
                  <Statistic
                    title="Formações"
                    value={viewingCoordenador.total_formacoes || 0}
                    prefix={<TeamOutlined />}
                  />
                </Card>
              </Col>
            </Row>

            {/* Carga de Trabalho */}
            <Card size="small" title="Carga de Trabalho" className="mb-4">
              <Space direction="vertical" style={{ width: '100%' }}>
                <div>
                  <Text type="secondary">Municípios: </Text>
                  <Progress
                    percent={((viewingCoordenador.total_municipios || 0) / 20) * 100}
                    format={() => `${viewingCoordenador.total_municipios || 0}/20`}
                    status={(viewingCoordenador.total_municipios || 0) >= 20 ? 'exception' : 'active'}
                  />
                </div>
                <div>
                  <Text type="secondary">Projetos: </Text>
                  <Progress
                    percent={((viewingCoordenador.total_projetos || 0) / 15) * 100}
                    format={() => `${viewingCoordenador.total_projetos || 0}/15`}
                    status={(viewingCoordenador.total_projetos || 0) >= 15 ? 'exception' : 'active'}
                  />
                </div>
              </Space>
            </Card>

            {/* Alocações */}
            <Card
              size="small"
              title="Alocações (Projetos/Municípios)"
              loading={loadingAlocacoes}
            >
              {alocacoes.length > 0 ? (
                <List
                  size="small"
                  dataSource={alocacoes}
                  renderItem={(item) => (
                    <List.Item>
                      <Space>
                        <Tag color="blue">{item.projeto_nome || item.projeto}</Tag>
                        <Text>{item.municipio_nome || item.municipio}</Text>
                        {item.uf && <Text type="secondary">- {item.uf}</Text>}
                      </Space>
                    </List.Item>
                  )}
                />
              ) : (
                <Text type="secondary">Nenhuma alocação encontrada</Text>
              )}
            </Card>

            {/* Observações */}
            {viewingCoordenador.observacoes && (
              <Card size="small" title="Observações" className="mt-4">
                <Text>{String(viewingCoordenador.observacoes)}</Text>
              </Card>
            )}
          </div>
        )}
      </Modal>
    </section>
  );
}
