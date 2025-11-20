/**
 * Dashboard da Equipe - Métricas de Desempenho
 *
 * Issue #190: Dashboard React consumindo endpoints /api/metrics/team/*
 * - Seção 1: Produtividade (cards + filtro de período)
 * - Seção 2: Ranking de Formadores (bar chart + tabela com export)
 * - Seção 3: Qualidade (cards com thresholds visuais)
 *
 * RBAC: Controle + Gerência (validado em App.jsx)
 */

import { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Table,
  Button,
  Typography,
  Space,
  Progress,
  Divider,
  Select,
  Spin,
  Alert,
  Tag,
  message,
} from 'antd';
import {
  RiseOutlined,
  FallOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  TeamOutlined,
  DownloadOutlined,
  TrophyOutlined,
  SyncOutlined,
  BarChartOutlined,
  SafetyOutlined,
  WarningOutlined,
} from '@ant-design/icons';

const { Title, Text } = Typography;
const { Option } = Select;

export default function EquipeDashboardPage() {
  const [days, setDays] = useState(7);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [productivityData, setProductivityData] = useState(null);
  const [formadoresData, setFormadoresData] = useState(null);
  const [qualityData, setQualityData] = useState(null);

  const loadAllMetrics = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      // Fetch em paralelo para performance
      const [prodRes, formRes, qualRes] = await Promise.all([
        fetch(`/api/metrics/team/productivity/?days=${days}`, { credentials: 'include' }),
        fetch(`/api/metrics/team/formadores/?days=${days}`, { credentials: 'include' }),
        fetch(`/api/metrics/team/quality/?days=${days}`, { credentials: 'include' }),
      ]);

      // Validar respostas
      if (!prodRes.ok || !formRes.ok || !qualRes.ok) {
        const errorStatus = !prodRes.ok ? prodRes.status : !formRes.ok ? formRes.status : qualRes.status;
        throw new Error(`Erro HTTP ${errorStatus}`);
      }

      // Parse JSON
      const [prod, form, qual] = await Promise.all([
        prodRes.json(),
        formRes.json(),
        qualRes.json(),
      ]);

      setProductivityData(prod);
      setFormadoresData(form);
      setQualityData(qual);
    } catch (err) {
      console.error('Erro ao carregar métricas:', err);
      setError(err.message);
      message.error('Erro ao carregar métricas da equipe');
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => {
    loadAllMetrics();
  }, [loadAllMetrics]);

  const handleExportCSV = () => {
    if (!formadoresData || !formadoresData.formadores) {
      message.warning('Nenhum dado para exportar');
      return;
    }

    // CSV headers
    const headers = ['Nome', 'Eventos', 'Horas Trabalhadas', 'Municípios Atendidos'];
    const rows = formadoresData.formadores.map((f) => [
      f.nome,
      f.eventos,
      f.horas_trabalhadas,
      f.municipios_atendidos,
    ]);

    // Gerar CSV
    const csvContent = [
      headers.join(','),
      ...rows.map((row) => row.join(',')),
    ].join('\n');

    // Download
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `formadores_ranking_${days}d.csv`;
    link.click();

    message.success(`CSV exportado (${rows.length} formadores)`);
  };

  // Helper para threshold de cores
  const getThresholdColor = (value, goodThreshold, direction = 'lower') => {
    if (direction === 'lower') {
      // Valores BAIXOS são bons (ex: taxa de rejeição)
      return value <= goodThreshold ? 'green' : 'red';
    }
    // Valores ALTOS são bons (ex: taxa de aprovação)
    return value >= goodThreshold ? 'green' : 'red';
  };

  const getThresholdStatus = (value, goodThreshold, direction = 'lower') => {
    const color = getThresholdColor(value, goodThreshold, direction);
    return color === 'green' ? 'success' : 'exception';
  };

  if (error) {
    return (
      <div style={{ padding: '24px' }}>
        <Alert
          message="Erro ao carregar dashboard"
          description={error}
          type="error"
          showIcon
        />
      </div>
    );
  }

  return (
    <div style={{ padding: '24px' }}>
      {/* Header com filtro e export */}
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <Title level={2}>Dashboard da Equipe</Title>
          <Text type="secondary">
            Métricas de desempenho e produtividade
          </Text>
        </div>

        <Space>
          <Select
            value={days}
            onChange={setDays}
            style={{ width: 150 }}
            disabled={loading}
          >
            <Option value={7}>Últimos 7 dias</Option>
            <Option value={15}>Últimos 15 dias</Option>
            <Option value={30}>Últimos 30 dias</Option>
          </Select>

          <Button
            type="primary"
            icon={<DownloadOutlined />}
            onClick={handleExportCSV}
            disabled={loading || !formadoresData}
          >
            Exportar CSV
          </Button>

          <Button
            icon={<SyncOutlined spin={loading} />}
            onClick={loadAllMetrics}
            disabled={loading}
          >
            Atualizar
          </Button>
        </Space>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '60px 0' }}>
          <Spin size="large" tip="Carregando métricas..." />
        </div>
      ) : (
        <>
          {/* SEÇÃO 1: PRODUTIVIDADE */}
          <Title level={4} style={{ marginTop: 24, marginBottom: 16 }}>
            <BarChartOutlined /> Produtividade ({productivityData?.period || '7d'})
          </Title>

          <Row gutter={[16, 16]} style={{ marginBottom: 32 }}>
            <Col xs={24} sm={12} md={6}>
              <Card bordered={false} style={{ background: 'linear-gradient(135deg, #1890ff 0%, #096dd9 100%)' }}>
                <Statistic
                  title={<span style={{ color: 'white' }}>Eventos Criados</span>}
                  value={productivityData?.events_created || 0}
                  prefix={<RiseOutlined />}
                  valueStyle={{ color: 'white' }}
                />
              </Card>
            </Col>

            <Col xs={24} sm={12} md={6}>
              <Card bordered={false} style={{
                background: productivityData && productivityData.approval_rate >= 80
                  ? 'linear-gradient(135deg, #52c41a 0%, #237804 100%)'
                  : 'linear-gradient(135deg, #faad14 0%, #d46b08 100%)'
              }}>
                <Statistic
                  title={<span style={{ color: 'white' }}>Taxa de Aprovação</span>}
                  value={productivityData?.approval_rate || 0}
                  suffix="%"
                  prefix={productivityData && productivityData.approval_rate >= 80 ? <CheckCircleOutlined /> : <WarningOutlined />}
                  valueStyle={{ color: 'white' }}
                />
                <Text style={{ color: 'white', fontSize: '12px' }}>Meta: ≥ 80%</Text>
              </Card>
            </Col>

            <Col xs={24} sm={12} md={6}>
              <Card bordered={false} style={{ background: 'linear-gradient(135deg, #722ed1 0%, #531dab 100%)' }}>
                <Statistic
                  title={<span style={{ color: 'white' }}>Tempo Médio de Aprovação</span>}
                  value={productivityData?.avg_approval_time_hours || 0}
                  suffix="h"
                  prefix={<ClockCircleOutlined />}
                  valueStyle={{ color: 'white' }}
                  precision={1}
                />
              </Card>
            </Col>

            <Col xs={24} sm={12} md={6}>
              <Card bordered={false} style={{
                background: productivityData && productivityData.gcal_error_rate <= 5
                  ? 'linear-gradient(135deg, #52c41a 0%, #237804 100%)'
                  : 'linear-gradient(135deg, #f5222d 0%, #cf1322 100%)'
              }}>
                <Statistic
                  title={<span style={{ color: 'white' }}>Taxa de Erro GCal</span>}
                  value={productivityData?.gcal_error_rate || 0}
                  suffix="%"
                  prefix={productivityData && productivityData.gcal_error_rate <= 5 ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
                  valueStyle={{ color: 'white' }}
                  precision={1}
                />
                <Text style={{ color: 'white', fontSize: '12px' }}>Meta: ≤ 5%</Text>
              </Card>
            </Col>
          </Row>

          {/* SEÇÃO 2: RANKING DE FORMADORES */}
          <Title level={4} style={{ marginTop: 24, marginBottom: 16 }}>
            <TrophyOutlined /> Top 10 Formadores ({formadoresData?.period || '30d'})
          </Title>

          <Row gutter={[16, 16]} style={{ marginBottom: 32 }}>
            <Col xs={24} md={12}>
              <Card title="Ranking por Eventos" bordered={false}>
                <Space direction="vertical" style={{ width: '100%' }} size="middle">
                  {formadoresData?.formadores?.slice(0, 10).map((formador, index) => {
                    const maxEventos = formadoresData.formadores[0]?.eventos || 1;
                    const percent = (formador.eventos / maxEventos) * 100;

                    // Cores por posição
                    let barColor = '#1890ff';
                    if (index === 0) barColor = '#fadb14'; // Ouro
                    else if (index === 1) barColor = '#b7b7b7'; // Prata
                    else if (index === 2) barColor = '#d4734e'; // Bronze

                    return (
                      <div key={formador.id}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                          <Space>
                            <Tag color={index < 3 ? 'gold' : 'default'}>{index + 1}º</Tag>
                            <Text>{formador.nome}</Text>
                          </Space>
                          <Text strong>{formador.eventos} eventos</Text>
                        </div>
                        <Progress
                          percent={percent}
                          strokeColor={barColor}
                          showInfo={false}
                        />
                      </div>
                    );
                  })}
                </Space>
              </Card>
            </Col>

            <Col xs={24} md={12}>
              <Card title="Detalhamento" bordered={false}>
                <Table
                  dataSource={formadoresData?.formadores || []}
                  rowKey="id"
                  pagination={{ pageSize: 5, size: 'small' }}
                  size="small"
                  columns={[
                    {
                      title: '#',
                      key: 'rank',
                      width: 50,
                      align: 'center',
                      render: (_, __, index) => <Text type="secondary">{index + 1}</Text>,
                    },
                    {
                      title: 'Nome',
                      dataIndex: 'nome',
                      key: 'nome',
                      ellipsis: true,
                    },
                    {
                      title: 'Eventos',
                      dataIndex: 'eventos',
                      key: 'eventos',
                      width: 80,
                      align: 'right',
                      sorter: (a, b) => b.eventos - a.eventos,
                      render: (val) => <Text strong>{val}</Text>,
                    },
                    {
                      title: 'Horas',
                      dataIndex: 'horas_trabalhadas',
                      key: 'horas',
                      width: 80,
                      align: 'right',
                      sorter: (a, b) => b.horas_trabalhadas - a.horas_trabalhadas,
                      render: (val) => `${val}h`,
                    },
                    {
                      title: 'Municípios',
                      dataIndex: 'municipios_atendidos',
                      key: 'municipios',
                      width: 90,
                      align: 'right',
                      sorter: (a, b) => b.municipios_atendidos - a.municipios_atendidos,
                    },
                  ]}
                />
              </Card>
            </Col>
          </Row>

          {/* SEÇÃO 3: QUALIDADE */}
          <Title level={4} style={{ marginTop: 24, marginBottom: 16 }}>
            <SafetyOutlined /> Qualidade do Processo ({qualityData?.period || '30d'})
          </Title>

          <Row gutter={[16, 16]}>
            <Col xs={24} sm={12} md={6}>
              <Card bordered={false}>
                <Statistic
                  title="Taxa de Rejeição"
                  value={qualityData?.rejection_rate || 0}
                  suffix="%"
                  prefix={qualityData && qualityData.rejection_rate <= 10 ? <CheckCircleOutlined style={{ color: '#52c41a' }} /> : <CloseCircleOutlined style={{ color: '#f5222d' }} />}
                  valueStyle={{
                    color: qualityData && qualityData.rejection_rate <= 10 ? '#52c41a' : '#f5222d'
                  }}
                  precision={1}
                />
                <Progress
                  percent={qualityData?.rejection_rate || 0}
                  status={getThresholdStatus(qualityData?.rejection_rate || 0, 10, 'lower')}
                  size="small"
                  style={{ marginTop: 8 }}
                />
                <Text type="secondary" style={{ fontSize: '12px' }}>Meta: ≤ 10%</Text>
              </Card>
            </Col>

            <Col xs={24} sm={12} md={6}>
              <Card bordered={false}>
                <Statistic
                  title="Taxa de Conflitos"
                  value={qualityData?.conflict_rate || 0}
                  suffix="%"
                  prefix={qualityData && qualityData.conflict_rate <= 5 ? <CheckCircleOutlined style={{ color: '#52c41a' }} /> : <CloseCircleOutlined style={{ color: '#f5222d' }} />}
                  valueStyle={{
                    color: qualityData && qualityData.conflict_rate <= 5 ? '#52c41a' : '#f5222d'
                  }}
                  precision={1}
                />
                <Progress
                  percent={qualityData?.conflict_rate || 0}
                  status={getThresholdStatus(qualityData?.conflict_rate || 0, 5, 'lower')}
                  size="small"
                  style={{ marginTop: 8 }}
                />
                <Text type="secondary" style={{ fontSize: '12px' }}>Meta: ≤ 5%</Text>
              </Card>
            </Col>

            <Col xs={24} sm={12} md={6}>
              <Card bordered={false}>
                <Statistic
                  title="Taxa de Re-trabalho"
                  value={qualityData?.rework_rate || 0}
                  suffix="%"
                  prefix={qualityData && qualityData.rework_rate <= 15 ? <CheckCircleOutlined style={{ color: '#52c41a' }} /> : <CloseCircleOutlined style={{ color: '#f5222d' }} />}
                  valueStyle={{
                    color: qualityData && qualityData.rework_rate <= 15 ? '#52c41a' : '#f5222d'
                  }}
                  precision={1}
                />
                <Progress
                  percent={qualityData?.rework_rate || 0}
                  status={getThresholdStatus(qualityData?.rework_rate || 0, 15, 'lower')}
                  size="small"
                  style={{ marginTop: 8 }}
                />
                <Text type="secondary" style={{ fontSize: '12px' }}>Meta: ≤ 15%</Text>
              </Card>
            </Col>

            <Col xs={24} sm={12} md={6}>
              <Card bordered={false}>
                <Statistic
                  title="Tempo Médio de Publicação"
                  value={qualityData?.avg_publish_time_minutes || 0}
                  suffix="min"
                  prefix={<ClockCircleOutlined style={{ color: '#1890ff' }} />}
                  valueStyle={{ color: '#1890ff' }}
                  precision={1}
                />
                <Text type="secondary" style={{ fontSize: '12px', display: 'block', marginTop: 8 }}>
                  Tempo entre aprovação e publicação no GCal
                </Text>
              </Card>
            </Col>
          </Row>

          {/* Footer com timestamp */}
          <Divider />
          <Text type="secondary" style={{ fontSize: '12px' }}>
            Última atualização: {new Date().toLocaleString('pt-BR')}
          </Text>
        </>
      )}
    </div>
  );
}
