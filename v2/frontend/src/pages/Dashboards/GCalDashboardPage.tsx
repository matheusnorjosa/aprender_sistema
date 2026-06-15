/**
 * Página de Dashboard Google Calendar
 *
 * Sprint 5 - Dashboard/Monitoring
 * - Cards de contagem (NONE/PENDING/PUBLISHED/ERROR)
 * - Filtros de período (date range) e status
 * - Tabela paginada de eventos
 * - Integração com /api/gcal/dashboard/metrics e /api/gcal/dashboard/events
 */

import { useState, useEffect, useMemo, useCallback } from 'react';
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
import { TIMING } from '../../constants';
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
    loadMetrics();
    loadEvents(1, pagination.pageSize);
    loadInsights();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dateRange]);

  useEffect(() => {
    loadEvents(1, pagination.pageSize);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter]);

  useEffect(() => {
    loadTopInsights();
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
      message.error('Erro ao carregar métricas do dashboard');
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
      message.error('Erro ao carregar lista de eventos');
    } finally {
      setTableLoading(false);
    }
  };

  const handleTableChange = useCallback((newPagination: TablePaginationConfig) => {
    loadEvents(newPagination.current || 1, newPagination.pageSize || 20);
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
      message.error('Erro ao carregar taxa de sucesso');
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
      message.error('Erro ao carregar insights');
    } finally {
      setInsightsLoading(false);
    }
  };

  const handleRefresh = () => {
    loadMetrics();
    loadEvents(pagination.current, pagination.pageSize);
    loadInsights();
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
      message.error('Erro ao carregar detalhes do evento');
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
        message.success(`Evento reenfileirado para publicação (Reapply)`);
        // Recarregar detalhes após 2 segundos
        setTimeout(() => loadEventDetail(selectedEventId), TIMING.GCAL_DETAIL_LOAD_DELAY_MS);
      } else if (data.errors && data.errors.length > 0) {
        message.error(`Erro: ${data.errors[0].detail}`);
      }
    } catch (error) {
      logger.error('Erro ao reapliar:', error);
      message.error((error as Error).message || 'Erro ao reapliar evento');
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
        message.success(`Evento reenfileirado para ressincronização (Resync)`);
        // Recarregar detalhes após 2 segundos
        setTimeout(() => loadEventDetail(selectedEventId), TIMING.GCAL_DETAIL_LOAD_DELAY_MS);
      } else if (data.errors && data.errors.length > 0) {
        message.error(`Erro: ${data.errors[0].detail}`);
      }
    } catch (error) {
      logger.error('Erro ao ressincronizar:', error);
      message.error((error as Error).message || 'Erro ao ressincronizar evento');
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
        datetime ? dayjs(datetime).format('DD/MM/YYYY HH:mm') : '-',
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
                        {dayjs(error.updated_at).format('DD/MM/YYYY HH:mm')}
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
                <Text strong>Top 5 {topMetric === 'municipios' ? 'Municípios' : 'Projetos'}</Text>
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
            <Tooltip title="Reapliar evento (forçar update sem resetar hash)">
              <Button icon={<EyeOutlined />} onClick={handleReapply}>
                Reapply
              </Button>
            </Tooltip>
            <Tooltip title="Ressincronizar evento (resetar hash + reprocessar)">
              <Button icon={<RedoOutlined />} onClick={handleResync} type="primary">
                Resync
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
                {eventDetail.inicio ? dayjs(eventDetail.inicio).format('DD/MM/YYYY HH:mm') : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="Fim">
                {eventDetail.fim ? dayjs(eventDetail.fim).format('DD/MM/YYYY HH:mm') : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="Usuário">{eventDetail.usuario_username || '-'}</Descriptions.Item>
              <Descriptions.Item label="Coordenador">{eventDetail.coordenador_username || '-'}</Descriptions.Item>
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
              <Descriptions.Item label="Event ID">{eventDetail.external_event_id || '-'}</Descriptions.Item>
              <Descriptions.Item label="Última Sincronização">
                {eventDetail.gcal_last_sync_at ? dayjs(eventDetail.gcal_last_sync_at).format('DD/MM/YYYY HH:mm') : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="Meet Link">
                {eventDetail.meet_link ? (
                  <a href={eventDetail.meet_link} target="_blank" rel="noopener noreferrer">
                    {eventDetail.meet_link}
                  </a>
                ) : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="Payload Hash">
                <Text ellipsis style={{ maxWidth: 500 }}>
                  {eventDetail.gcal_payload_hash || '-'}
                </Text>
              </Descriptions.Item>
              <Descriptions.Item label="Último Erro">
                {eventDetail.gcal_last_error ? (
                  <Text type="danger">{eventDetail.gcal_last_error}</Text>
                ) : (
                  <Text type="success">Nenhum erro</Text>
                )}
              </Descriptions.Item>
              <Descriptions.Item label="Atualizado em">
                {eventDetail.updated_at ? dayjs(eventDetail.updated_at).format('DD/MM/YYYY HH:mm') : '-'}
              </Descriptions.Item>
            </Descriptions>

            {/* Participações */}
            {eventDetail.participations && eventDetail.participations.length > 0 && (
              <>
                <Divider orientation="left">Participações</Divider>
                <Space direction="vertical" style={{ width: '100%' }}>
                  {eventDetail.participations.map((p) => (
                    <Card key={p.email} size="small">
                      <Space>
                        <UserOutlined />
                        <Text strong>{p.email}</Text>
                        <Tag>{p.role}</Tag>
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
                items={eventDetail.timeline.map((log) => ({
                  color: getTimelineColor(log.action),
                  children: (
                    <div>
                      <Text strong>{log.action}</Text>
                      <br />
                      <Text type="secondary">
                        {log.usuario_nome} - {dayjs(log.created_at).format('DD/MM/YYYY HH:mm:ss')}
                      </Text>
                      {log.details && Object.keys(log.details).length > 0 && (
                        <div className="mt-1">
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            {JSON.stringify(log.details, null, 2)}
                          </Text>
                        </div>
                      )}
                    </div>
                  ),
                }))}
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
