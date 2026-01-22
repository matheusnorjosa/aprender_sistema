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
import { ensureCsrfToken } from '../../api/config';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;

// Status badge colors
const STATUS_COLORS = {
  NONE: 'default',
  PENDING: 'processing',
  PUBLISHED: 'success',
  ERROR: 'error',
};

// Status icons
const STATUS_ICONS = {
  NONE: <MinusCircleOutlined />,
  PENDING: <ClockCircleOutlined />,
  PUBLISHED: <CheckCircleOutlined />,
  ERROR: <CloseCircleOutlined />,
};

// Status labels
const STATUS_LABELS = {
  NONE: 'Não Publicado',
  PENDING: 'Pendente',
  PUBLISHED: 'Publicado',
  ERROR: 'Erro',
};

export default function GCalDashboardPage() {
  const [metrics, setMetrics] = useState(null);
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [tableLoading, setTableLoading] = useState(false);
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 20,
    total: 0,
  });

  // Filtros
  const [dateRange, setDateRange] = useState([
    dayjs().subtract(30, 'days'),
    dayjs().add(30, 'days'),
  ]);
  const [statusFilter, setStatusFilter] = useState(null);

  // Drawer (Issue #98)
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedEventId, setSelectedEventId] = useState(null);
  const [eventDetail, setEventDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // Insights (Issue #99)
  const [successRate, setSuccessRate] = useState(null);
  const [topInsights, setTopInsights] = useState(null);
  const [insightsLoading, setInsightsLoading] = useState(false);
  const [topMetric, setTopMetric] = useState('municipios');

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
      const params = new URLSearchParams();
      if (dateRange && dateRange[0] && dateRange[1]) {
        params.append('start', dateRange[0].format('YYYY-MM-DD'));
        params.append('end', dateRange[1].format('YYYY-MM-DD'));
      }

      const response = await fetch(`/api/gcal/dashboard/metrics/?${params}`, {
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error('Erro ao carregar métricas');
      }

      const data = await response.json();
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
      const params = new URLSearchParams();
      params.append('page', page);
      params.append('page_size', pageSize);

      if (dateRange && dateRange[0] && dateRange[1]) {
        params.append('start', dateRange[0].format('YYYY-MM-DD'));
        params.append('end', dateRange[1].format('YYYY-MM-DD'));
      }

      if (statusFilter) {
        params.append('status', statusFilter);
      }

      const response = await fetch(`/api/gcal/dashboard/events/?${params}`, {
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error('Erro ao carregar eventos');
      }

      const data = await response.json();
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

  const handleTableChange = useCallback((newPagination) => {
    loadEvents(newPagination.current, newPagination.pageSize);
  }, []);

  // Issue #99: Carregar insights (success rate + top insights)
  const loadInsights = async () => {
    await Promise.all([loadSuccessRate(), loadTopInsights()]);
  };

  const loadSuccessRate = async () => {
    setInsightsLoading(true);
    try {
      const params = new URLSearchParams();
      if (dateRange && dateRange[0] && dateRange[1]) {
        params.append('start', dateRange[0].format('YYYY-MM-DD'));
        params.append('end', dateRange[1].format('YYYY-MM-DD'));
      }

      const response = await fetch(`/api/gcal/dashboard/insights/success-rate/?${params}`, {
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error('Erro ao carregar success rate');
      }

      const data = await response.json();
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
      const params = new URLSearchParams();
      params.append('metric', topMetric);
      params.append('limit', 5);

      if (dateRange && dateRange[0] && dateRange[1]) {
        params.append('start', dateRange[0].format('YYYY-MM-DD'));
        params.append('end', dateRange[1].format('YYYY-MM-DD'));
      }

      const response = await fetch(`/api/gcal/dashboard/insights/top/?${params}`, {
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error('Erro ao carregar top insights');
      }

      const data = await response.json();
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

  const handleExport = (format) => {
    // Construir URL de export com os mesmos filtros ativos
    const params = new URLSearchParams();
    params.append('export_format', format);

    if (dateRange && dateRange[0] && dateRange[1]) {
      params.append('start', dateRange[0].format('YYYY-MM-DD'));
      params.append('end', dateRange[1].format('YYYY-MM-DD'));
    }

    if (statusFilter) {
      params.append('status', statusFilter);
    }

    // Abrir URL em nova aba (download automático via Content-Disposition)
    const exportUrl = `/api/gcal/dashboard/events/export/?${params}`;
    window.open(exportUrl, '_blank');
    message.success(`Exportação ${format.toUpperCase()} iniciada!`);
  };

  // Issue #98: Abrir Drawer com detalhes do evento
  const handleRowClick = async (record) => {
    setSelectedEventId(record.id);
    setDrawerOpen(true);
    await loadEventDetail(record.id);
  };

  // Issue #98: Buscar detalhes do evento
  const loadEventDetail = async (eventId) => {
    setDetailLoading(true);
    try {
      const response = await fetch(`/api/gcal/dashboard/events/${eventId}/detail/`, {
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error('Erro ao carregar detalhes do evento');
      }

      const data = await response.json();
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
      const csrfToken = await ensureCsrfToken();
      const response = await fetch('/api/gcal/dashboard/batch/reapply/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken,
        },
        credentials: 'include',
        body: JSON.stringify({
          ids: [selectedEventId],
          dry_run: false,
          apply_blocked: false,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Erro ao reapliar evento');
      }

      const data = await response.json();

      if (data.queued > 0) {
        message.success(`Evento reenfileirado para publicação (Reapply)`);
        // Recarregar detalhes após 2 segundos
        setTimeout(() => loadEventDetail(selectedEventId), TIMING.GCAL_DETAIL_LOAD_DELAY_MS);
      } else if (data.errors && data.errors.length > 0) {
        message.error(`Erro: ${data.errors[0].detail}`);
      }
    } catch (error) {
      logger.error('Erro ao reapliar:', error);
      message.error(error.message || 'Erro ao reapliar evento');
    }
  };

  // Issue #98: Resync (reutiliza endpoint batch com 1 ID)
  const handleResync = async () => {
    if (!selectedEventId) return;

    try {
      const csrfToken = await ensureCsrfToken();
      const response = await fetch('/api/gcal/dashboard/batch/resync/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken,
        },
        credentials: 'include',
        body: JSON.stringify({
          ids: [selectedEventId],
          dry_run: false,
          apply_blocked: false,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Erro ao ressincronizar evento');
      }

      const data = await response.json();

      if (data.queued > 0) {
        message.success(`Evento reenfileirado para ressincronização (Resync)`);
        // Recarregar detalhes após 2 segundos
        setTimeout(() => loadEventDetail(selectedEventId), TIMING.GCAL_DETAIL_LOAD_DELAY_MS);
      } else if (data.errors && data.errors.length > 0) {
        message.error(`Erro: ${data.errors[0].detail}`);
      }
    } catch (error) {
      logger.error('Erro ao ressincronizar:', error);
      message.error(error.message || 'Erro ao ressincronizar evento');
    }
  };

  // Menu items para dropdown de Export (memoized §16 Epic #459)
  const exportMenuItems = useMemo(() => [
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
  const columns = useMemo(() => [
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
      render: (text) => text || '-',
    },
    {
      title: 'Status GCal',
      dataIndex: 'gcal_status',
      key: 'gcal_status',
      width: 140,
      render: (status) => (
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
      render: (datetime) =>
        datetime ? dayjs(datetime).format('DD/MM/YYYY HH:mm') : '-',
    },
    {
      title: 'Erro',
      dataIndex: 'gcal_last_error',
      key: 'gcal_last_error',
      ellipsis: true,
      render: (error) =>
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
  const topInsightsColumns = useMemo(() => [
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
      render: (value) => <Text type="success">{value}</Text>,
    },
    {
      title: 'Erros',
      dataIndex: 'error',
      key: 'error',
      width: 80,
      align: 'center',
      render: (value) => <Text type="danger">{value}</Text>,
    },
    {
      title: 'Taxa (%)',
      dataIndex: 'rate',
      key: 'rate',
      width: 100,
      align: 'center',
      render: (rate) => {
        const percentage = (rate * 100).toFixed(1);
        const color = rate >= 0.8 ? '#52c41a' : rate >= 0.5 ? '#faad14' : '#f5222d';
        return <Text style={{ color, fontWeight: 'bold' }}>{percentage}%</Text>;
      },
    },
  ], []);

  return (
    <div className="p-6">
      <div className="mb-6 flex justify-between items-center">
        <div>
          <Title level={2}>Dashboard Google Calendar</Title>
          <Text type="secondary">
            Monitore métricas de publicação e sincronização de eventos
          </Text>
        </div>
      </div>

      {/* Filtros */}
      <Card
        className="mb-6"
        bodyStyle={{ padding: '16px' }}
      >
        <Space size="middle" wrap>
          <div>
            <Text strong style={{ marginRight: 8 }}>
              Período:
            </Text>
            <RangePicker
              value={dateRange}
              onChange={setDateRange}
              format="DD/MM/YYYY"
              allowClear={false}
            />
          </div>
          <div>
            <Text strong style={{ marginRight: 8 }}>
              Status:
            </Text>
            <Select
              style={{ width: 180 }}
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

      {/* Cards de Contagem */}
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

      {/* Insights - Success Rate + Top 5 (Issue #99) */}
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
                  style={{ width: 130 }}
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

      {/* Tabela de Eventos */}
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

      {/* Drawer de Detalhes do Evento (Issue #98) */}
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
                  {eventDetail.participations.map((p, idx) => (
                    <Card key={idx} size="small">
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
    </div>
  );
}

// Helper: Determinar cor da timeline baseado na action
function getTimelineColor(action) {
  if (action.includes('ERROR')) return 'red';
  if (action.includes('PUBLISH') || action.includes('RESYNC')) return 'green';
  if (action.includes('REQUESTED') || action.includes('PENDING')) return 'blue';
  if (action.includes('CANCEL')) return 'orange';
  return 'gray';
}
