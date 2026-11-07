/**
 * Pagina de Dashboards e Analytics
 *
 * Design: paginadashboards/screen.png
 * - KPI cards (Eventos Futuros, Aprovados, Total Participantes, Aprovacoes Pendentes)
 * - Grafico de barras: Eventos por Fluxo
 * - Grafico de pizza: Eventos por Setor
 *
 * Ref: Issue #311 - Substituir mock data por API real
 *
 * Sem rolagem horizontal (G30): o Top 5 é o ResponsiveTable (posição a partir de sm, progresso
 * de md; o que some vai para a linha expandida) e os botões do cabeçalho quebram linha.
 */

import { useState, useEffect, useCallback, type JSX } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Tag,
  Button,
  Typography,
  Space,
  Progress,
  Spin,
  Alert,
  Empty,
} from 'antd';
import ResponsiveTable, { VISIVEL_A_PARTIR, type ColunaResponsiva } from '../../components/ResponsiveTable';
import logger from '../../utils/logger';
import {
  getDashboardOverview,
  type DashboardOverviewResponse,
  type DashboardCoordenadorItem,
} from '../../api/dashboard';
import {
  CalendarOutlined,
  CheckCircleOutlined,
  TeamOutlined,
  ClockCircleOutlined,
  BarChartOutlined,
  PieChartOutlined,
  RiseOutlined,
  ReloadOutlined,
} from '@ant-design/icons';

const { Title, Text } = Typography;

// Cores para os graficos
const FLUXO_COLORS: Record<string, string> = {
  SUPER: '#1890ff',
  NAO_SUPER: '#52c41a',
};

// Rótulo do fluxo na tela (G20): o código (NAO_SUPER) não aparece cru.
const FLUXO_ROTULO: Record<string, string> = {
  SUPER: 'Superintendência',
  NAO_SUPER: 'Não Superintendência',
};

const GERENCIA_COLORS = ['#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1'];

export default function DashboardsPage(): JSX.Element {
  const [data, setData] = useState<DashboardOverviewResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const result = await getDashboardOverview();
      setData(result);
    } catch (err) {
      logger.error('Erro ao carregar dashboard:', err);
      setError((err as Error).message || 'Erro ao carregar dados do dashboard');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  // Loading state
  if (loading) {
    return (
      <div className="p-6 flex justify-center items-center min-h-96">
        <Spin size="large" tip="Carregando dashboard..." />
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="p-6">
        <Alert
          message="Erro ao carregar dashboard"
          description={error}
          type="error"
          showIcon
          action={
            <Button size="small" onClick={loadData} icon={<ReloadOutlined />}>
              Tentar novamente
            </Button>
          }
        />
      </div>
    );
  }

  // No data state
  if (!data) {
    return (
      <div className="p-6">
        <Empty description="Nenhum dado disponível" />
      </div>
    );
  }

  const { kpis, por_fluxo, por_gerencia, top_coordenadores } = data;

  // Calcular max para Progress bars
  const maxFluxo = Math.max(...por_fluxo.map((f) => f.quantidade), 1);
  const maxCoord = top_coordenadores[0]?.eventos ?? 1;

  // Columns for top coordenadores table
  const columns: ColunaResponsiva<DashboardCoordenadorItem>[] = [
    {
      title: 'Posicao',
      key: 'posicao',
      responsive: VISIVEL_A_PARTIR.sm,
      width: 88,
      render: (_, __, index) => (
        <Tag color={index < 3 ? 'gold' : 'default'}>
          {index + 1}o
        </Tag>
      ),
    },
    {
      title: 'Coordenador',
      dataIndex: 'nome',
      key: 'nome',
    },
    {
      title: 'Eventos',
      dataIndex: 'eventos',
      key: 'eventos',
      width: 80,
      align: 'right',
      render: (eventos: number) => <Text strong>{eventos}</Text>,
    },
    {
      title: 'Progresso',
      key: 'progresso',
      responsive: VISIVEL_A_PARTIR.md,
      render: (_, record) => (
        <Progress
          percent={(record.eventos / maxCoord) * 100}
          showInfo={false}
          strokeColor="#52c41a"
        />
      ),
    },
  ];

  return (
    <section className="p-6" aria-labelledby="dashboards-title">
      <header className="mb-6 flex flex-wrap justify-between items-center gap-3">
        <div>
          <Title level={2} id="dashboards-title">Dashboards e Análises</Title>
          <Text type="secondary">
            Visualize métricas detalhadas e relatórios do sistema
          </Text>
        </div>
        <Space wrap>
          <Button icon={<ReloadOutlined />} onClick={loadData}>
            Atualizar
          </Button>
        </Space>
      </header>

      {/* KPI Cards */}
      <section aria-label="Indicadores principais">
      <Row gutter={[16, 16]} className="mb-6">
        <Col xs={24} sm={12} md={6}>
          <Card
            bordered={false}
            style={{
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            }}
          >
            <Statistic
              title={<span style={{ color: 'white' }}>Eventos Futuros</span>}
              value={kpis.eventos_futuros}
              prefix={<CalendarOutlined />}
              valueStyle={{ color: 'white' }}
              suffix={<RiseOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card
            bordered={false}
            style={{
              background: 'linear-gradient(135deg, #52c41a 0%, #237804 100%)',
            }}
          >
            <Statistic
              title={<span style={{ color: 'white' }}>Aprovados</span>}
              value={kpis.eventos_aprovados}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: 'white' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card
            bordered={false}
            style={{
              background: 'linear-gradient(135deg, #1890ff 0%, #096dd9 100%)',
            }}
          >
            <Statistic
              title={<span style={{ color: 'white' }}>Total Formadores</span>}
              value={kpis.total_formadores}
              prefix={<TeamOutlined />}
              valueStyle={{ color: 'white' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card
            bordered={false}
            style={{
              background: 'linear-gradient(135deg, #fa8c16 0%, #d46b08 100%)',
            }}
          >
            <Statistic
              title={
                <span style={{ color: 'white' }}>Aprovações Pendentes</span>
              }
              value={kpis.aprovacoes_pendentes}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: 'white' }}
            />
          </Card>
        </Col>
      </Row>
      </section>

      {/* Graficos */}
      <section aria-label="Gráficos de análise">
      <Row gutter={[16, 16]} className="mb-6">
        {/* Eventos por Fluxo */}
        <Col xs={24} md={12}>
          <Card
            title={
              <Space>
                <BarChartOutlined /> Eventos por Fluxo (últimos 30 dias)
              </Space>
            }
            bordered={false}
          >
            {por_fluxo.length === 0 ? (
              <Empty description="Nenhum evento no período" />
            ) : (
              <Space direction="vertical" style={{ width: '100%' }} size="large">
                {por_fluxo.map((item) => (
                  <div key={item.fluxo}>
                    <div className="flex justify-between mb-2">
                      <Tag color={FLUXO_COLORS[item.fluxo] || '#666'}>
                        {FLUXO_ROTULO[item.fluxo] ?? item.fluxo}
                      </Tag>
                      <Text strong>{item.quantidade} eventos</Text>
                    </div>
                    <Progress
                      percent={(item.quantidade / maxFluxo) * 100}
                      strokeColor={FLUXO_COLORS[item.fluxo] || '#666'}
                      showInfo={false}
                    />
                  </div>
                ))}
              </Space>
            )}
          </Card>
        </Col>

        {/* Eventos por Gerencia */}
        <Col xs={24} md={12}>
          <Card
            title={
              <Space>
                <PieChartOutlined /> Eventos por Gerência (últimos 30 dias)
              </Space>
            }
            bordered={false}
          >
            {por_gerencia.length === 0 ? (
              <Empty description="Nenhum evento no período" />
            ) : (
              <Space
                direction="vertical"
                style={{ width: '100%' }}
                size="middle"
              >
                {por_gerencia.map((item, idx) => (
                  <div key={item.gerencia}>
                    <div className="flex justify-between mb-1">
                      <Text>{item.gerencia}</Text>
                      <Text strong>{item.porcentagem}%</Text>
                    </div>
                    <Progress
                      percent={item.porcentagem}
                      {...(GERENCIA_COLORS[idx % GERENCIA_COLORS.length] !==
                        undefined && {
                        strokeColor:
                          GERENCIA_COLORS[idx % GERENCIA_COLORS.length],
                      })}
                      size="small"
                    />
                  </div>
                ))}
              </Space>
            )}
          </Card>
        </Col>
      </Row>
      </section>

      {/* Top Coordenadores */}
      <section aria-label="Ranking de coordenadores">
      <Row gutter={[16, 16]}>
        <Col xs={24}>
          <Card
            title="Top 5 Coordenadores (por numero de eventos - ultimos 30 dias)"
            bordered={false}
          >
            {top_coordenadores.length === 0 ? (
              <Empty description="Nenhum coordenador no periodo" />
            ) : (
              <ResponsiveTable<DashboardCoordenadorItem>
                dataSource={top_coordenadores}
                rowKey="nome"
                pagination={false}
                columns={columns}
                nomeDaLinha={(coordenador) => coordenador.nome}
              />
            )}
          </Card>
        </Col>
      </Row>
      </section>
    </section>
  );
}
