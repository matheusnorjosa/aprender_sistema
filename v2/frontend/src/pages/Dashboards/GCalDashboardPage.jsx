/**
 * Página de Dashboard Google Calendar
 *
 * Sprint 5 - Dashboard/Monitoring
 * - Cards de contagem (NONE/PENDING/PUBLISHED/ERROR)
 * - Filtros de período (date range) e status
 * - Tabela paginada de eventos
 * - Integração com /api/gcal/dashboard/metrics e /api/gcal/dashboard/events
 */

import { useState, useEffect } from 'react';
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
} from 'antd';
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  CloseCircleOutlined,
  MinusCircleOutlined,
  SyncOutlined,
  ExclamationCircleOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';

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

  useEffect(() => {
    loadMetrics();
    loadEvents(1, pagination.pageSize);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dateRange]);

  useEffect(() => {
    loadEvents(1, pagination.pageSize);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter]);

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
      console.error('Erro ao carregar métricas:', error);
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
      console.error('Erro ao carregar eventos:', error);
      message.error('Erro ao carregar lista de eventos');
    } finally {
      setTableLoading(false);
    }
  };

  const handleTableChange = (newPagination) => {
    loadEvents(newPagination.current, newPagination.pageSize);
  };

  const handleRefresh = () => {
    loadMetrics();
    loadEvents(pagination.current, pagination.pageSize);
  };

  const columns = [
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
  ];

  return (
    <div style={{ padding: '24px' }}>
      <div
        style={{
          marginBottom: 24,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <div>
          <Title level={2}>Dashboard Google Calendar</Title>
          <Text type="secondary">
            Monitore métricas de publicação e sincronização de eventos
          </Text>
        </div>
      </div>

      {/* Filtros */}
      <Card
        style={{ marginBottom: 24 }}
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
        </Space>
      </Card>

      {/* Cards de Contagem */}
      {loading ? (
        <Skeleton active paragraph={{ rows: 2 }} />
      ) : (
        <>
          <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
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
              style={{ marginBottom: 24 }}
            />
          )}
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
        />
      </Card>
    </div>
  );
}
