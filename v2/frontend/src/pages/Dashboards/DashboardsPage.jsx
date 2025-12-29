/**
 * Página de Dashboards e Analytics
 *
 * Design: paginadashboards/screen.png
 * - KPI cards (Eventos Futuros, Aprovados, Total Participantes, Aprovações Pendentes)
 * - Gráfico de barras: Eventos por Fluxo
 * - Gráfico de pizza: Eventos por Setor
 * - Botão de export CSV
 */

import { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Table,
  Tag,
  Button,
  Typography,
  Space,
  Progress,
  Divider,
} from 'antd';
import logger from '../../utils/logger';
import {
  CalendarOutlined,
  CheckCircleOutlined,
  TeamOutlined,
  ClockCircleOutlined,
  BarChartOutlined,
  PieChartOutlined,
  DownloadOutlined,
  RiseOutlined,
  FallOutlined,
} from '@ant-design/icons';

const { Title, Text } = Typography;

// Mock data - Substituir por chamadas API reais
const mockStats = {
  eventosFuturos: 45,
  eventosAprovados: 128,
  totalParticipantes: 342,
  aprovaçõesPendentes: 12,
};

const mockEventosPorFluxo = [
  { fluxo: 'SUPER', quantidade: 78, cor: '#1890ff' },
  { fluxo: 'NAO_SUPER', quantidade: 50, cor: '#52c41a' },
];

const mockEventosPorSetor = [
  { setor: 'Educação Infantil', quantidade: 45, porcentagem: 35.2 },
  { setor: 'Fundamental I', quantidade: 38, porcentagem: 29.7 },
  { setor: 'Fundamental II', quantidade: 30, porcentagem: 23.4 },
  { setor: 'EJA', quantidade: 15, porcentagem: 11.7 },
];

const mockTopCoordenadores = [
  { nome: 'João Silva', eventos: 23 },
  { nome: 'Maria Santos', eventos: 19 },
  { nome: 'Pedro Costa', eventos: 15 },
  { nome: 'Ana Oliveira', eventos: 12 },
  { nome: 'Carlos Souza', eventos: 10 },
];

export default function DashboardsPage() {
  const [stats, setStats] = useState(mockStats);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      // TODO: Chamar API real de estatísticas
      // const data = await fetchDashboardStats();
      setTimeout(() => {
        setStats(mockStats);
      }, 300);
    } catch (error) {
      logger.error('Erro ao carregar estatísticas:', error);
    }
  };

  const handleExportCSV = () => {
    // TODO: Implementar export real
  };

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <Title level={2}>Dashboards e Análises</Title>
          <Text type="secondary">
            Visualize métricas detalhadas e relatórios do sistema
          </Text>
        </div>
        <Button
          type="primary"
          icon={<DownloadOutlined />}
          onClick={handleExportCSV}
        >
          Exportar para CSV
        </Button>
      </div>

      {/* KPI Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={6}>
          <Card bordered={false} style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
            <Statistic
              title={<span style={{ color: 'white' }}>Eventos Futuros</span>}
              value={stats.eventosFuturos}
              prefix={<CalendarOutlined />}
              valueStyle={{ color: 'white' }}
              suffix={<RiseOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card bordered={false} style={{ background: 'linear-gradient(135deg, #52c41a 0%, #237804 100%)' }}>
            <Statistic
              title={<span style={{ color: 'white' }}>Aprovados</span>}
              value={stats.eventosAprovados}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: 'white' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card bordered={false} style={{ background: 'linear-gradient(135deg, #1890ff 0%, #096dd9 100%)' }}>
            <Statistic
              title={<span style={{ color: 'white' }}>Total Participantes</span>}
              value={stats.totalParticipantes}
              prefix={<TeamOutlined />}
              valueStyle={{ color: 'white' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card bordered={false} style={{ background: 'linear-gradient(135deg, #fa8c16 0%, #d46b08 100%)' }}>
            <Statistic
              title={<span style={{ color: 'white' }}>Aprovações Pendentes</span>}
              value={stats.aprovaçõesPendentes}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: 'white' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Gráficos */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        {/* Eventos por Fluxo */}
        <Col xs={24} md={12}>
          <Card
            title={<Space><BarChartOutlined /> Eventos por Fluxo</Space>}
            bordered={false}
          >
            <Space direction="vertical" style={{ width: '100%' }} size="large">
              {mockEventosPorFluxo.map((item) => (
                <div key={item.fluxo}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                    <Tag color={item.cor}>{item.fluxo}</Tag>
                    <Text strong>{item.quantidade} eventos</Text>
                  </div>
                  <Progress
                    percent={(item.quantidade / 128) * 100}
                    strokeColor={item.cor}
                    showInfo={false}
                  />
                </div>
              ))}
            </Space>
          </Card>
        </Col>

        {/* Eventos por Setor */}
        <Col xs={24} md={12}>
          <Card
            title={<Space><PieChartOutlined /> Eventos por Setor</Space>}
            bordered={false}
          >
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              {mockEventosPorSetor.map((item, idx) => {
                const colors = ['#1890ff', '#52c41a', '#faad14', '#f5222d'];
                return (
                  <div key={item.setor}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <Text>{item.setor}</Text>
                      <Text strong>{item.porcentagem}%</Text>
                    </div>
                    <Progress
                      percent={item.porcentagem}
                      strokeColor={colors[idx % colors.length]}
                      size="small"
                    />
                  </div>
                );
              })}
            </Space>
          </Card>
        </Col>
      </Row>

      {/* Top Coordenadores */}
      <Row gutter={[16, 16]}>
        <Col xs={24}>
          <Card
            title="Top 5 Coordenadores (por número de eventos)"
            bordered={false}
          >
            <Table
              dataSource={mockTopCoordenadores}
              rowKey="nome"
              pagination={false}
              columns={[
                {
                  title: 'Posição',
                  key: 'posicao',
                  width: 100,
                  render: (_, __, index) => (
                    <Tag color={index < 3 ? 'gold' : 'default'}>
                      {index + 1}º
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
                  align: 'right',
                  render: (eventos) => <Text strong>{eventos}</Text>,
                },
                {
                  title: 'Progresso',
                  key: 'progresso',
                  render: (_, record) => (
                    <Progress
                      percent={(record.eventos / 23) * 100}
                      showInfo={false}
                      strokeColor="#52c41a"
                    />
                  ),
                },
              ]}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
