/**
 * Página de Dashboard Google Calendar
 *
 * Sprint 5 - Dashboard/Monitoring
 * - Cards de contagem (NONE/PENDING/PUBLISHED/ERROR)
 * - Filtros de período (date range) e status
 * - Tabela paginada de eventos
 * - Integração com /api/gcal/dashboard/metrics e /api/gcal/dashboard/events
 */

import { useState, useEffect, useMemo, useCallback, type JSX } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Table,
  Tag,
  Typography,
  Space,
  DatePicker,
  Select,
  message,
  Tooltip,
  Alert,
  Skeleton,
  Button,
  Dropdown,
  Drawer,
  Descriptions,
  Timeline,
  Divider,
  Spin,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import type { TablePaginationConfig } from 'antd/es/table';
import type { MenuProps } from 'antd';
import type { Dayjs } from 'dayjs';
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  CloseCircleOutlined,
  MinusCircleOutlined,
  SyncOutlined,
  ExclamationCircleOutlined,
  ReloadOutlined,
  DownloadOutlined,
  DownOutlined,
  EyeOutlined,
  RedoOutlined,
  UserOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import logger from '../../utils/logger';
import { formatFortaleza } from '../../utils/datetime';
import { TIMING } from '../../constants';
import { participantLabel } from '../../utils/participants';
import {
  getDashboardMetrics,
  listDashboardEvents,
  getDashboardSuccessRate,
  getDashboardTopInsights,
  getDashboardEventDetail,
  reapplyBatch,
  resyncBatch,
  buildDashboardEventsExportUrl,
  type GCalDashboardMetricsResponse,
  type GCalDashboardEventRecord,
  type GCalDashboardEventDetail,
  type GCalSuccessRateResponse,
  type GCalTopInsightsResponse,
  type GCalTopInsightItem,
} from '../../api/gcal';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;

/**
 * GCal status type
 */
type GCalStatus = 'NONE' | 'PENDING' | 'PUBLISHED' | 'ERROR';

type MetricsData = GCalDashboardMetricsResponse;
type EventRecord = GCalDashboardEventRecord;
type EventDetail = GCalDashboardEventDetail;
type SuccessRateData = GCalSuccessRateResponse;
type TopInsightItem = GCalTopInsightItem;
type TopInsightsData = GCalTopInsightsResponse;

/**
 * Pagination state interface
 */
interface PaginationState {
  current: number;
  pageSize: number;
  total: number;
}

// Status badge colors
const STATUS_COLORS: Record<GCalStatus, string> = {
  NONE: 'default',
  PENDING: 'processing',
  PUBLISHED: 'success',
  ERROR: 'error',
};

// Status icons
const STATUS_ICONS: Record<GCalStatus, JSX.Element> = {
  NONE: <MinusCircleOutlined />,
  PENDING: <ClockCircleOutlined />,
  PUBLISHED: <CheckCircleOutlined />,
  ERROR: <CloseCircleOutlined />,
};

// Status labels
const STATUS_LABELS: Record<GCalStatus, string> = {
  NONE: 'Não Publicado',
  PENDING: 'Pendente',
  PUBLISHED: 'Publicado',
  ERROR: 'Erro',
};

// Helper: Determinar cor da timeline baseado na action
function getTimelineColor(action: string): string {
  if (action.includes('ERROR')) return 'red';
  if (action.includes('PUBLISH') || action.includes('RESYNC')) return 'green';
  if (action.includes('REQUESTED') || action.includes('PENDING')) return 'blue';
  if (action.includes('CANCEL')) return 'orange';
  return 'gray';
}

// O que cada registro da linha do tempo quer dizer, em frase (B#18: o código da ação não vai à tela).
const ACAO_LABELS: Record<string, string> = {
  PUBLISH_GCAL_REQUESTED: 'Publicação pedida',
  PUBLISH_GCAL: 'Publicado no Google',
  PUBLISH_GCAL_ERROR: 'Erro ao publicar no Google',
  CANCEL_GCAL_REQUESTED: 'Remoção do Google pedida',
  CANCEL_GCAL: 'Removido do Google',
  RESYNC_GCAL_REQUESTED: 'Reenvio pedido',
  GOOGLE_CONNECT: 'Conta Google conectada',
  GOOGLE_DISCONNECT: 'Conta Google desconectada',
  GOOGLE_REFRESH_TOKEN: 'Acesso ao Google renovado',
};

// Papel do participante em português (COORD_ACOMPANHA é o coordenador extra da caixa "Coordenador(es)").
const ROLE_LABELS: Record<string, string> = {
  FORMADOR: 'Formador',
  COORDENADOR: 'Coordenador',
  COORD_ACOMPANHA: 'Coordenador extra',
  CONVIDADO: 'Convidado',
};

// O aviso leva a mensagem do servidor (o fetchAPI a põe em error.message), não só o texto genérico.
function avisarErro(texto: string, error: unknown): void {
  const detalhe = error instanceof Error ? error.message : '';
  message.error(detalhe ? `${texto}: ${detalhe}` : texto);
}

// Cópia Google → sistema (GCAL_COPIA_GOOGLE): o que mudou, em português, e o choque (D3: copia e avisa).
const COPIA_GOOGLE = 'GCAL_COPIA_GOOGLE';

function intervalo(valor: unknown): string {
  const v = (valor ?? {}) as { inicio?: string; fim?: string };
  if (!v.inicio || !v.fim) return '?';
  return `${formatFortaleza(v.inicio, 'DD/MM HH:mm')}–${formatFortaleza(v.fim, 'HH:mm')}`;
}

function resumoDaCopia(details: Record<string, unknown>): { texto: string; choque: string | null } {
  if (details['campo'] === 'status') {
    return { texto: 'Cancelado no Google: o evento foi reprovado', choque: null };
  }
  const bruto = details['choque'];
  const choques = Array.isArray(bruto) ? (bruto as { usuario_id: number; codigo: string }[]) : [];
  const pessoas = new Set(choques.map((c) => c.usuario_id)).size;
  const codigos = [...new Set(choques.map((c) => c.codigo))].sort().join(', ');
  return {
    texto: `Horário: ${intervalo(details['antes'])} → ${intervalo(details['depois'])}`,
    choque: pessoas ? `Choque de agenda: ${pessoas} ${pessoas === 1 ? 'pessoa' : 'pessoas'} (${codigos})` : null,
  };
}

export default function GCalDashboardPage(): JSX.Element {
  const [metrics, setMetrics] = useState<MetricsData | null>(null);
  const [events, setEvents] = useState<EventRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [tableLoading, setTableLoading] = useState<boolean>(false);
  const [pagination, setPagination] = useState<PaginationState>({
    current: 1,
    pageSize: 20,
    total: 0,
  });

  // Filtros
  const [dateRange, setDateRange] = useState<[Dayjs, Dayjs]>([
    dayjs().subtract(30, 'days'),
    dayjs().add(30, 'days'),
  ]);
  const [statusFilter, setStatusFilter] = useState<GCalStatus | null>(null);

  // Drawer (Issue #98)
  const [drawerOpen, setDrawerOpen] = useState<boolean>(false);
  const [selectedEventId, setSelectedEventId] = useState<number | null>(null);
  const [eventDetail, setEventDetail] = useState<EventDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState<boolean>(false);

  // Insights (Issue #99)
  const [successRate, setSuccessRate] = useState<SuccessRateData | null>(null);
  const [topInsights, setTopInsights] = useState<TopInsightsData | null>(null);
  const [insightsLoading, setInsightsLoading] = useState<boolean>(false);
  const [topMetric, setTopMetric] = useState<string>('municipios');

  useEffect(() => {
    void loadMetrics();
    void loadEvents(1, pagination.pageSize);
    void loadInsights();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dateRange]);

  useEffect(() => {
    void loadEvents(1, pagination.pageSize);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter]);

  useEffect(() => {
    void loadTopInsights();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [topMetric, dateRange]);

  const loadMetrics = async () => {
    setLoading(true);
    try {
      const data = await getDashboardMetrics({
        start: dateRange[0].format('YYYY-MM-DD'),
        end: dateRange[1].format('YYYY-MM-DD'),
      });
      setMetrics(data);
    } catch (error) {
      logger.error('Erro ao carregar métricas:', error);
      avisarErro('Erro ao carregar métricas do painel', error);
    } finally {
      setLoading(false);
    }
  };

  const loadEvents = async (page = 1, pageSize = 20) => {
    setTableLoading(true);
    try {
      const data = await listDashboardEvents({
        page,
        page_size: pageSize,
        start: dateRange[0].format('YYYY-MM-DD'),
        end: dateRange[1].format('YYYY-MM-DD'),
        status: statusFilter || undefined,
      });
      setEvents(data.results || []);
      setPagination({
        current: page,
        pageSize: pageSize,
        total: data.count || 0,
      });
    } catch (error) {
      logger.error('Erro ao carregar eventos:', error);
      avisarErro('Erro ao carregar a lista de eventos', error);
    } finally {
      setTableLoading(false);
    }
  };

  const handleTableChange = useCallback((newPagination: TablePaginationConfig) => {
    void loadEvents(newPagination.current || 1, newPagination.pageSize || 20);
  }, []);

  // Issue #99: Carregar insights (success rate + top insights)
  const loadInsights = async () => {
    await Promise.all([loadSuccessRate(), loadTopInsights()]);
  };

  const loadSuccessRate = async () => {
    setInsightsLoading(true);
    try {
      const data = await getDashboardSuccessRate({
        start: dateRange[0].format('YYYY-MM-DD'),
        end: dateRange[1].format('YYYY-MM-DD'),
      });
      setSuccessRate(data);
    } catch (error) {
      logger.error('Erro ao carregar success rate:', error);
      avisarErro('Erro ao carregar a taxa de sucesso', error);
    } finally {
      setInsightsLoading(false);
    }
  };

  const loadTopInsights = async () => {
    setInsightsLoading(true);
    try {
      const data = await getDashboardTopInsights({
        metric: topMetric,
        limit: 5,
        start: dateRange[0].format('YYYY-MM-DD'),
        end: dateRange[1].format('YYYY-MM-DD'),
      });
      setTopInsights(data);
    } catch (error) {
      logger.error('Erro ao carregar top insights:', error);
      avisarErro('Erro ao carregar os municípios e projetos com mais eventos', error);
    } finally {
      setInsightsLoading(false);
    }
  };

  const handleRefresh = () => {
    void loadMetrics();
    void loadEvents(pagination.current, pagination.pageSize);
    void loadInsights();
  };

  const handleExport = (format: string) => {
    const exportUrl = buildDashboardEventsExportUrl({
      export_format: format === 'json' ? 'json' : 'csv',
      start: dateRange[0].format('YYYY-MM-DD'),
      end: dateRange[1].format('YYYY-MM-DD'),
      status: statusFilter || undefined,
    });
    window.open(exportUrl, '_blank');
    message.success(`Exportação ${format.toUpperCase()} iniciada!`);
  };

  // Issue #98: Abrir Drawer com detalhes do evento
  const handleRowClick = async (record: EventRecord) => {
    setSelectedEventId(record.id);
    setDrawerOpen(true);
    await loadEventDetail(record.id);
  };

  // Issue #98: Buscar detalhes do evento
  const loadEventDetail = async (eventId: number) => {
    setDetailLoading(true);
    try {
      const data = await getDashboardEventDetail(eventId);
      setEventDetail(data);
    } catch (error) {
      logger.error('Erro ao carregar detalhes:', error);
      avisarErro('Erro ao carregar os detalhes do evento', error);
    } finally {
      setDetailLoading(false);
    }
  };

  // Issue #98: Fechar Drawer
  const handleDrawerClose = () => {
    setDrawerOpen(false);
    setEventDetail(null);
    setSelectedEventId(null);
  };

  // Issue #98: Reapply (reutiliza endpoint batch com 1 ID)
  const handleReapply = async () => {
    if (!selectedEventId) return;

    try {
      const data = await reapplyBatch({
        ids: [selectedEventId],
        dry_run: false,
        apply_blocked: false,
      });

      if (data.queued > 0) {
        message.success('Atualização pedida: o evento vai ser enviado de novo ao Google');
        // Recarregar detalhes após 2 segundos
        setTimeout(() => { void loadEventDetail(selectedEventId); }, TIMING.GCAL_DETAIL_LOAD_DELAY_MS);
      } else if (data.errors && data.errors.length > 0) {
        message.error(`Erro: ${data.errors[0]?.detail}`);
      }
    } catch (error) {
      logger.error('Erro ao reapliar:', error);
      message.error((error as Error).message || 'Erro ao atualizar o evento no Google');
    }
  };

  // Issue #98: Resync (reutiliza endpoint batch com 1 ID)
  const handleResync = async () => {
    if (!selectedEventId) return;

    try {
      const data = await resyncBatch({
        ids: [selectedEventId],
        dry_run: false,
        apply_blocked: false,
      });

      if (data.queued > 0) {
        message.success('Reenvio pedido: o evento vai ser publicado de novo no Google');
        // Recarregar detalhes após 2 segundos
        setTimeout(() => { void loadEventDetail(selectedEventId); }, TIMING.GCAL_DETAIL_LOAD_DELAY_MS);
      } else if (data.errors && data.errors.length > 0) {
        message.error(`Erro: ${data.errors[0]?.detail}`);
      }
    } catch (error) {
      logger.error('Erro ao ressincronizar:', error);
      message.error((error as Error).message || 'Erro ao reenviar o evento ao Google');
    }
  };

  // Menu items para dropdown de Export (memoized §16 Epic #459)
  const exportMenuItems: MenuProps['items'] = useMemo(() => [
    {
      key: 'csv',
      label: 'Exportar CSV',
      icon: <DownloadOutlined />,
      onClick: () => handleExport('csv'),
    },
    {
      key: 'json',
      label: 'Exportar JSON',
      icon: <DownloadOutlined />,
      onClick: () => handleExport('json'),
    },
  ], [dateRange, statusFilter]);

  // Columns memoized (§16 Epic #459)
  const columns: ColumnsType<EventRecord> = useMemo(() => [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: 'Resumo',
      dataIndex: 'summary',
      key: 'summary',
      ellipsis: true,
      render: (text: string) => text || '-',
    },
    {
      title: 'Status GCal',
      dataIndex: 'gcal_status',
      key: 'gcal_status',
      width: 140,
      render: (status: GCalStatus) => (
        <Tag color={STATUS_COLORS[status]} icon={STATUS_ICONS[status]}>
          {STATUS_LABELS[status]}
        </Tag>
      ),
    },
    {
      title: 'Última Sincronização',
      dataIndex: 'gcal_last_sync_at',
      key: 'gcal_last_sync_at',
      width: 180,
      render: (datetime: string | null) =>
        datetime ? formatFortaleza(datetime) : '-',
    },
    {
      title: 'Erro',
      dataIndex: 'gcal_last_error',
      key: 'gcal_last_error',
      ellipsis: true,
      render: (error: string | null) =>
        error ? (
          <Tooltip title={error}>
            <Text type="danger" ellipsis style={{ maxWidth: 200 }}>
              {error}
            </Text>
          </Tooltip>
        ) : (
          '-'
        ),
    },
  ], []);

  // Issue #99: Colunas para Top Insights (memoized §16 Epic #459)
  const topInsightsColumns: ColumnsType<TopInsightItem> = useMemo(() => [
    {
      title: 'Nome',
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
    },
    {
      title: 'Total',
      dataIndex: 'count',
      key: 'count',
      width: 80,
      align: 'center',
    },
    {
      title: 'Publicados',
      dataIndex: 'published',
      key: 'published',
      width: 100,
      align: 'center',
      render: (value: number) => <Text type="success">{value}</Text>,
    },
    {
      title: 'Erros',
      dataIndex: 'error',
      key: 'error',
      width: 80,
      align: 'center',
      render: (value: number) => <Text type="danger">{value}</Text>,
    },
    {
      title: 'Taxa (%)',
      dataIndex: 'rate',
      key: 'rate',
      width: 100,
      align: 'center',
      render: (rate: number) => {
        const percentage = (rate * 100).toFixed(1);
        const color = rate >= 0.8 ? '#52c41a' : rate >= 0.5 ? '#faad14' : '#f5222d';
        return <Text style={{ color, fontWeight: 'bold' }}>{percentage}%</Text>;
      },
    },
  ], []);

  return (
    <section className="p-6" aria-labelledby="gcal-dashboard-title">
      <header className="mb-6 flex justify-between items-center">
        <div>
          <Title level={2} id="gcal-dashboard-title">Dashboard Google Calendar</Title>
          <Text type="secondary">
            Monitore métricas de publicação e sincronização de eventos
          </Text>
        </div>
      </header>

      {/* Filtros */}
      <nav aria-label="Filtros de busca">
      <Card
        className="mb-6"
        styles={{ body: { padding: '16px' } }}
      >
        <Space size="middle" wrap>
          <div>
            <Text strong style={{ marginRight: 8 }}>
              Período:
            </Text>
            <RangePicker
              value={dateRange}
              onChange={(dates) => dates && setDateRange(dates as [Dayjs, Dayjs])}
              format="DD/MM/YYYY"
              allowClear={false}
            />
          </div>
          <div>
            <Text strong style={{ marginRight: 8 }}>
              Status:
            </Text>
            <Select
              style={{ width: '100%', maxWidth: 180 }}
              placeholder="Todos os status"
              allowClear
              value={statusFilter}
              onChange={setStatusFilter}
              options={[
                { value: 'NONE', label: 'Não Publicado' },
                { value: 'PENDING', label: 'Pendente' },
                { value: 'PUBLISHED', label: 'Publicado' },
                { value: 'ERROR', label: 'Erro' },
              ]}
            />
          </div>
          <Tooltip title="Recarregar dados">
            <ReloadOutlined
              onClick={handleRefresh}
              style={{ fontSize: 18, cursor: 'pointer', color: '#1890ff' }}
              spin={loading || tableLoading}
            />
          </Tooltip>
          <Dropdown menu={{ items: exportMenuItems }} placement="bottomRight">
            <Button icon={<DownloadOutlined />}>
              Exportar <DownOutlined />
            </Button>
          </Dropdown>
        </Space>
      </Card>
      </nav>

      {/* Cards de Contagem */}
      <section aria-label="Contagem por status">
      {loading ? (
        <Skeleton active paragraph={{ rows: 2 }} />
      ) : (
        <>
          <Row gutter={[16, 16]} className="mb-6">
            <Col xs={24} sm={12} md={6}>
              <Card bordered={false} style={{ background: 'linear-gradient(135deg, #8e9eab 0%, #505965 100%)' }}>
                <Statistic
                  title={<span style={{ color: 'white' }}>Não Publicado</span>}
                  value={metrics?.counts?.NONE || 0}
                  prefix={<MinusCircleOutlined />}
                  valueStyle={{ color: 'white' }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Card bordered={false} style={{ background: 'linear-gradient(135deg, #1890ff 0%, #096dd9 100%)' }}>
                <Statistic
                  title={<span style={{ color: 'white' }}>Pendente</span>}
                  value={metrics?.counts?.PENDING || 0}
                  prefix={<SyncOutlined spin />}
                  valueStyle={{ color: 'white' }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Card bordered={false} style={{ background: 'linear-gradient(135deg, #52c41a 0%, #237804 100%)' }}>
                <Statistic
                  title={<span style={{ color: 'white' }}>Publicado</span>}
                  value={metrics?.counts?.PUBLISHED || 0}
                  prefix={<CheckCircleOutlined />}
                  valueStyle={{ color: 'white' }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Card bordered={false} style={{ background: 'linear-gradient(135deg, #f5222d 0%, #a8071a 100%)' }}>
                <Statistic
                  title={<span style={{ color: 'white' }}>Erro</span>}
                  value={metrics?.counts?.ERROR || 0}
                  prefix={<ExclamationCircleOutlined />}
                  valueStyle={{ color: 'white' }}
                />
              </Card>
            </Col>
          </Row>

          {/* Erros Recentes */}
          {metrics?.recent_errors && metrics.recent_errors.length > 0 && (
            <Alert
              message="Erros Recentes"
              description={
                <Space direction="vertical" style={{ width: '100%' }} size="small">
                  {metrics.recent_errors.map((error) => (
                    <div key={error.id}>
                      <Text strong>#{error.id}</Text> - {error.summary}:{' '}
                      <Text type="danger">{error.gcal_last_error}</Text>
                      <br />
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {formatFortaleza(error.updated_at)}
                      </Text>
                    </div>
                  ))}
                </Space>
              }
              type="error"
              showIcon
              icon={<CloseCircleOutlined />}
              className="mb-6"
            />
          )}
        </>
      )}
      </section>

      {/* Insights - Success Rate + Top 5 (Issue #99) */}
      <section aria-label="Insights e taxa de sucesso">
      {insightsLoading ? (
        <Skeleton active paragraph={{ rows: 3 }} className="mb-6" />
      ) : (
        <>
          <Row gutter={[16, 16]} className="mb-6">
            {/* Success Rate Cards */}
            <Col xs={24} md={8}>
              <Card bordered={false}>
                <Statistic
                  title="Taxa de Sucesso"
                  value={successRate?.rate ? (successRate.rate * 100).toFixed(1) : 0}
                  suffix="%"
                  valueStyle={{
                    color: (successRate?.rate || 0) >= 0.8 ? '#52c41a' : '#f5222d',
                    fontSize: 32,
                    fontWeight: 'bold',
                  }}
                />
                <Space size="small" className="mt-4">
                  <Text type="secondary">Publicados:</Text>
                  <Text strong style={{ color: '#52c41a' }}>{successRate?.published || 0}</Text>
                </Space>
                <br />
                <Space size="small">
                  <Text type="secondary">Erros:</Text>
                  <Text strong style={{ color: '#f5222d' }}>{successRate?.error || 0}</Text>
                </Space>
              </Card>
            </Col>
            <Col xs={24} md={8}>
              <Card bordered={false}>
                <Statistic
                  title="Publicados"
                  value={successRate?.published || 0}
                  valueStyle={{ color: '#52c41a' }}
                  prefix={<CheckCircleOutlined />}
                />
              </Card>
            </Col>
            <Col xs={24} md={8}>
              <Card bordered={false}>
                <Statistic
                  title="Erros"
                  value={successRate?.error || 0}
                  valueStyle={{ color: '#f5222d' }}
                  prefix={<CloseCircleOutlined />}
                />
              </Card>
            </Col>
          </Row>

          {/* Top 5 Insights */}
          <Card
            title={
              <Space>
                <Text strong>Os 5 {topMetric === 'municipios' ? 'municípios' : 'projetos'} com mais eventos</Text>
                <Select
                  size="small"
                  value={topMetric}
                  onChange={setTopMetric}
                  style={{ width: '100%', maxWidth: 130 }}
                  options={[
                    { value: 'municipios', label: 'Municípios' },
                    { value: 'projetos', label: 'Projetos' },
                  ]}
                />
              </Space>
            }
            bordered={false}
            className="mb-6"
          >
            <Table
              scroll={{ x: "max-content" }}
              dataSource={topInsights?.items || []}
              columns={topInsightsColumns}
              rowKey="name"
              pagination={false}
              size="small"
              loading={insightsLoading}
            />
          </Card>
        </>
      )}
      </section>

      {/* Tabela de Eventos */}
      <section aria-label="Lista de eventos">
      <Card title="Eventos" bordered={false}>
        <Table
          dataSource={events}
          columns={columns}
          rowKey="id"
          loading={tableLoading}
          pagination={pagination}
          onChange={handleTableChange}
          scroll={{ x: 800 }}
          onRow={(record) => ({
            onClick: () => handleRowClick(record),
            style: { cursor: 'pointer' },
          })}
        />
      </Card>
      </section>

      {/* Drawer de Detalhes do Evento (Issue #98) */}
      <aside aria-label="Detalhes do evento">
      <Drawer
        title={`Detalhes do Evento #${selectedEventId}`}
        placement="right"
        width={720}
        onClose={handleDrawerClose}
        open={drawerOpen}
        extra={
          <Space>
            <Tooltip title="Manda o evento de novo ao Google, como está no sistema">
              <Button icon={<EyeOutlined />} onClick={handleReapply}>
                Atualizar no Google
              </Button>
            </Tooltip>
            <Tooltip title="Refaz a publicação do evento no Google desde o começo">
              <Button icon={<RedoOutlined />} onClick={handleResync} type="primary">
                Reenviar
              </Button>
            </Tooltip>
          </Space>
        }
      >
        {detailLoading ? (
          <Spin size="large" style={{ display: 'block', textAlign: 'center', marginTop: 100 }} />
        ) : eventDetail ? (
          <>
            {/* Resumo do Evento */}
            <Descriptions title="Resumo" bordered column={1} size="small">
              <Descriptions.Item label="ID">{eventDetail.id}</Descriptions.Item>
              <Descriptions.Item label="Município">{eventDetail.municipio_nome || '-'}</Descriptions.Item>
              <Descriptions.Item label="Projeto">{eventDetail.projeto_nome || '-'}</Descriptions.Item>
              <Descriptions.Item label="Tipo de Evento">{eventDetail.tipo_evento_nome || '-'}</Descriptions.Item>
              <Descriptions.Item label="Início">
                {eventDetail.inicio ? formatFortaleza(eventDetail.inicio) : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="Fim">
                {eventDetail.fim ? formatFortaleza(eventDetail.fim) : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="Usuário">{eventDetail.usuario_nome || '-'}</Descriptions.Item>
              <Descriptions.Item label="Coordenador">{eventDetail.coordenador_nome || '-'}</Descriptions.Item>
              <Descriptions.Item label="Fluxo">
                <Tag color={eventDetail.fluxo === 'SUPER' ? 'blue' : 'green'}>
                  {eventDetail.fluxo}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Status GCal">
                <Tag color={STATUS_COLORS[eventDetail.gcal_status]} icon={STATUS_ICONS[eventDetail.gcal_status]}>
                  {STATUS_LABELS[eventDetail.gcal_status]}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Código no Google">{eventDetail.external_event_id || '-'}</Descriptions.Item>
              <Descriptions.Item label="Última Sincronização">
                {eventDetail.gcal_last_sync_at ? formatFortaleza(eventDetail.gcal_last_sync_at) : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="Meet Link">
                {eventDetail.meet_link ? (
                  <a href={eventDetail.meet_link} target="_blank" rel="noopener noreferrer">
                    {eventDetail.meet_link}
                  </a>
                ) : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="Último Erro">
                {eventDetail.gcal_last_error ? (
                  <Text type="danger">{eventDetail.gcal_last_error}</Text>
                ) : (
                  <Text type="success">Nenhum erro</Text>
                )}
              </Descriptions.Item>
              <Descriptions.Item label="Atualizado em">
                {eventDetail.updated_at ? formatFortaleza(eventDetail.updated_at) : '-'}
              </Descriptions.Item>
            </Descriptions>

            {/* Participações */}
            {eventDetail.participations && eventDetail.participations.length > 0 && (
              <>
                <Divider orientation="left">Participações</Divider>
                <Space direction="vertical" style={{ width: '100%' }}>
                  {eventDetail.participations.map((p, index) => (
                    <Card key={p.usuario?.id ?? p.guest_email ?? index} size="small">
                      <Space>
                        <UserOutlined />
                        {/* S5: o e-mail vem null quando é o de reserva ou leva CPF; o rótulo é o nome. */}
                        <Text strong>{participantLabel(p)}</Text>
                        <Tag>{ROLE_LABELS[p.role] ?? p.role}</Tag>
                        {p.ch_horas && <Text type="secondary">{p.ch_horas}h</Text>}
                      </Space>
                      {p.observacao && (
                        <div className="mt-2">
                          <Text type="secondary">{p.observacao}</Text>
                        </div>
                      )}
                    </Card>
                  ))}
                </Space>
              </>
            )}

            {/* Timeline de Auditoria */}
            <Divider orientation="left">Timeline de Auditoria</Divider>
            {eventDetail.timeline && eventDetail.timeline.length > 0 ? (
              <Timeline
                items={eventDetail.timeline.map((log) => {
                  if (log.action === COPIA_GOOGLE) {
                    const { texto, choque } = resumoDaCopia(log.details ?? {});
                    return {
                      color: choque ? 'red' : 'blue',
                      children: (
                        <div>
                          <Text strong>Mudança feita no Google</Text>
                          <br />
                          <Text>{texto}</Text>
                          {choque && <Alert className="mt-1" type="warning" showIcon message={choque} />}
                          <br />
                          <Text type="secondary">{formatFortaleza(log.created_at, 'DD/MM/YYYY HH:mm:ss')}</Text>
                        </div>
                      ),
                    };
                  }
                  return {
                    color: getTimelineColor(log.action),
                    children: (
                      <div>
                        <Text strong>{ACAO_LABELS[log.action] ?? 'Registro do Google'}</Text>
                        <br />
                        <Text type="secondary">
                          {log.usuario_nome} - {formatFortaleza(log.created_at, 'DD/MM/YYYY HH:mm:ss')}
                        </Text>
                      </div>
                    ),
                  };
                })}
              />
            ) : (
              <Alert message="Nenhum log de auditoria encontrado" type="info" />
            )}
          </>
        ) : (
          <Alert message="Nenhum dado disponível" type="warning" />
        )}
      </Drawer>
      </aside>
    </section>
  );
}
