/**
 * Dashboard de Compras - DAT
 *
 * Métricas de municípios atendidos, volumes por coleção/produto e ranking de compras.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Col,
  Empty,
  Progress,
  Row,
  Select,
  Space,
  Spin,
  Table,
  Tag,
  Typography,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  AppstoreOutlined,
  BookOutlined,
  CheckCircleOutlined,
  DollarOutlined,
  EnvironmentOutlined,
  InboxOutlined,
  ReloadOutlined,
  ShoppingCartOutlined,
} from '@ant-design/icons';
import {
  getComprasDashboard,
  getProdutosOptions,
  getProjetosOptions,
  type ComprasDashboardData,
} from '../../api/datModule';
import { UF_OPTIONS } from '../../constants';
import './ComprasDashboardPage.css';

const { Title, Text } = Typography;

interface OptionItem {
  id: number;
  nome: string;
}

interface BarListProps {
  data: Array<Record<string, string | number>>;
  labelKey: string;
  valueKey: string;
  percentKey?: string;
  color: string;
  colorScale?: (percent: number, value: number, label: string) => string;
  valueFormatter?: (value: number) => string;
  emptyLabel: string;
}

const toNumber = (value: unknown): number => {
  if (typeof value === 'number') return value;
  if (typeof value === 'string' && value.trim() !== '') return Number(value);
  return 0;
};

const formatNumber = (value: unknown): string =>
  toNumber(value).toLocaleString('pt-BR');

const formatCurrency = (value: unknown): string =>
  `R$ ${toNumber(value).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`;

function BarList({
  data,
  labelKey,
  valueKey,
  percentKey,
  color,
  colorScale,
  valueFormatter = formatNumber,
  emptyLabel,
}: BarListProps): JSX.Element {
  if (!data || data.length === 0) {
    return <Empty description={emptyLabel} />;
  }

  const maxValue = Math.max(...data.map((item) => toNumber(item[valueKey])), 1);

  return (
    <div className="bar-list">
      {data.map((item) => {
        const value = toNumber(item[valueKey]);
        const percent = Math.max(2, Math.round((value / maxValue) * 100));
        const label = String(item[labelKey] ?? 'Sem nome');
        const percentValue = percentKey ? toNumber(item[percentKey]) : null;

        const fillColor = colorScale ? colorScale(percent, value, label) : color;

        return (
          <div className="bar-row" key={`${label}-${value}`}>
            <div className="bar-label">{label}</div>
            <div className="bar-track">
              <div className="bar-fill" style={{ width: `${percent}%`, background: fillColor }} />
            </div>
            <div className="bar-value">
              {valueFormatter(value)}
              {percentValue !== null && percentValue > 0 ? ` (${percentValue}%)` : ''}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function MiniBars({
  data,
  labelKey,
  valueKey,
}: {
  data: Array<Record<string, string | number>>;
  labelKey: string;
  valueKey: string;
}): JSX.Element {
  if (!data || data.length === 0) {
    return <Empty description="Sem dados para o período" />;
  }

  const maxValue = Math.max(...data.map((item) => toNumber(item[valueKey])), 1);

  return (
    <div className="mini-bars">
      {data.map((item) => {
        const value = toNumber(item[valueKey]);
        const height = Math.max(8, Math.round((value / maxValue) * 160));
        const label = String(item[labelKey] ?? '');

        return (
          <div className="mini-bar" key={`${label}-${value}`}>
            <div className="mini-bar-fill" style={{ height }} />
            <div className="mini-bar-label">{label}</div>
          </div>
        );
      })}
    </div>
  );
}

const percentColorScale = (percent: number): string => {
  if (percent < 20) return '#e03131';
  if (percent < 40) return '#f08c00';
  if (percent < 60) return '#f2c94c';
  if (percent < 80) return '#74c0fc';
  return '#2f9e44';
};

function PercentLegend(): JSX.Element {
  const labels = ['0-20%', '20-40%', '40-60%', '60-80%', '80-100%'];
  const colors = ['#e03131', '#f08c00', '#f2c94c', '#74c0fc', '#2f9e44'];
  return (
    <div className="percent-legend">
      <Text type="secondary" className="percent-legend-label">Percentual</Text>
      <div className="percent-legend-bar">
        {colors.map((color, idx) => (
          <div key={color} className="percent-legend-segment" style={{ background: color }}>
            <span>{labels[idx]}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function ComprasDashboardPage(): JSX.Element {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<ComprasDashboardData | null>(null);

  const [projetos, setProjetos] = useState<OptionItem[]>([]);
  const [produtos, setProdutos] = useState<OptionItem[]>([]);

  const [filters, setFilters] = useState({
    uf: undefined as string | undefined,
    ano_uso: undefined as number | undefined,
    projeto: undefined as number | undefined,
    produto: undefined as number | undefined,
    tipo_compra: undefined as string | undefined,
  });

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const params: Record<string, string | number> = {};
      if (filters.uf) params.uf = filters.uf;
      if (filters.ano_uso) params.ano_uso = filters.ano_uso;
      if (filters.projeto) params.projeto_id = filters.projeto;
      if (filters.produto) params.produto_id = filters.produto;
      if (filters.tipo_compra) params.tipo_compra = filters.tipo_compra;

      const response = await getComprasDashboard(params);
      setData(response);
    } catch (err) {
      setError((err as Error).message || 'Erro ao carregar dashboard');
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  useEffect(() => {
    const loadOptions = async () => {
      try {
        const [projData, prodData] = await Promise.all([
          getProjetosOptions(),
          getProdutosOptions(),
        ]);
        setProjetos((projData as any).results || projData || []);
        setProdutos((prodData as any).results || prodData || []);
      } catch (_error) {
        // Sem opções não bloqueia dashboard
      }
    };
    loadOptions();
  }, []);

  const anoOptions = useMemo(() => {
    const currentYear = new Date().getFullYear();
    return Array.from({ length: 6 }, (_, i) => currentYear - i).map((year) => ({
      label: String(year),
      value: year,
    }));
  }, []);

  const tipoCompraOptions = [
    { label: 'Primeira compra', value: 'primeira' },
    { label: 'Compra adicional 1', value: 'adicional_1' },
    { label: 'Compra adicional 2', value: 'adicional_2' },
    { label: 'Compra adicional 3', value: 'adicional_3' },
  ];

  const topMunicipiosColumns: ColumnsType<Record<string, string | number>> = [
    {
      title: 'Município',
      dataIndex: 'municipio',
      key: 'municipio',
      render: (value: string, record) => (
        <Space>
          <Tag color="blue">{String(record.uf || '-')}</Tag>
          <Text strong>{value}</Text>
        </Space>
      ),
    },
    {
      title: 'Itens',
      dataIndex: 'quantidade',
      key: 'quantidade',
      align: 'right',
      render: (value: number) => formatNumber(value),
    },
    {
      title: 'Entregues',
      dataIndex: 'entregues',
      key: 'entregues',
      align: 'right',
      render: (value: number) => formatNumber(value),
    },
    {
      title: 'Compras',
      dataIndex: 'compras',
      key: 'compras',
      align: 'right',
      render: (value: number) => formatNumber(value),
    },
    {
      title: 'Comparativo',
      key: 'comparativo',
      render: (_: unknown, record) => {
        const maxQuantidade = Math.max(
          ...(data?.top_municipios || []).map((item) => toNumber(item.quantidade)),
          1
        );
        const percent = Math.round((toNumber(record.quantidade) / maxQuantidade) * 100);

        return (
          <Progress
            percent={percent}
            showInfo={false}
            strokeColor="#20c997"
            size="small"
          />
        );
      },
    },
  ];

  if (loading) {
    return (
      <div className="p-6 flex justify-center items-center min-h-96">
        <Spin size="large" tip="Carregando dashboard..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <Alert
          message="Erro ao carregar dashboard"
          description={error}
          type="error"
          showIcon
          action={(
            <Button size="small" onClick={loadDashboard} icon={<ReloadOutlined />}>
              Tentar novamente
            </Button>
          )}
        />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="p-6">
        <Empty description="Nenhum dado disponível" />
      </div>
    );
  }

  return (
    <section className="compras-dashboard p-6" aria-labelledby="compras-dashboard-title">
      <header className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <Title level={2} id="compras-dashboard-title" className="dashboard-title">
            Dashboard de Compras
          </Title>
          <Text type="secondary">
            Municípios atendidos, volumes de livros e ranking de compras.
          </Text>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={loadDashboard}>
            Atualizar
          </Button>
        </Space>
      </header>

      <Card className="chart-card mb-6" bordered={false}>
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} md={6}>
            <Select
              style={{ width: '100%' }}
              placeholder="UF"
              allowClear
              value={filters.uf}
              onChange={(value) => setFilters((prev) => ({ ...prev, uf: value }))}
              options={UF_OPTIONS}
              showSearch
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Select
              style={{ width: '100%' }}
              placeholder="Ano de Uso"
              allowClear
              value={filters.ano_uso}
              onChange={(value) => setFilters((prev) => ({ ...prev, ano_uso: value }))}
              options={anoOptions}
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Select
              style={{ width: '100%' }}
              placeholder="Projeto"
              allowClear
              showSearch
              optionFilterProp="label"
              value={filters.projeto}
              onChange={(value) => setFilters((prev) => ({ ...prev, projeto: value }))}
              options={projetos.map((item) => ({ label: item.nome, value: item.id }))}
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Select
              style={{ width: '100%' }}
              placeholder="Produto"
              allowClear
              showSearch
              optionFilterProp="label"
              value={filters.produto}
              onChange={(value) => setFilters((prev) => ({ ...prev, produto: value }))}
              options={produtos.map((item) => ({ label: item.nome, value: item.id }))}
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Select
              style={{ width: '100%' }}
              placeholder="Tipo de Compra"
              allowClear
              value={filters.tipo_compra}
              onChange={(value) => setFilters((prev) => ({ ...prev, tipo_compra: value }))}
              options={tipoCompraOptions}
            />
          </Col>
        </Row>
      </Card>

      <Row gutter={[16, 16]} className="mb-6">
        <Col xs={24} sm={12} md={8} lg={4}>
          <Card className="kpi-card kpi-1" bordered={false}>
            <div className="flex items-center justify-between">
              <div>
                <div className="kpi-title">Municípios atendidos</div>
                <div className="kpi-value">{formatNumber(data.kpis.municipios_atendidos)}</div>
                {data.kpis.total_municipios_referencia ? (
                  <div className="kpi-subtitle">
                    de {formatNumber(data.kpis.total_municipios_referencia)} ({data.kpis.cobertura_percentual}%)
                  </div>
                ) : null}
              </div>
              <EnvironmentOutlined className="kpi-icon" />
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8} lg={4}>
          <Card className="kpi-card kpi-2" bordered={false}>
            <div className="flex items-center justify-between">
              <div>
                <div className="kpi-title">Livros comprados</div>
                <div className="kpi-value">{formatNumber(data.kpis.total_itens)}</div>
              </div>
              <BookOutlined className="kpi-icon" />
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8} lg={4}>
          <Card className="kpi-card kpi-3" bordered={false}>
            <div className="flex items-center justify-between">
              <div>
                <div className="kpi-title">Entregues / Vendidos</div>
                <div className="kpi-value">{formatNumber(data.kpis.total_entregue)}</div>
              </div>
              <CheckCircleOutlined className="kpi-icon" />
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8} lg={4}>
          <Card className="kpi-card kpi-4" bordered={false}>
            <div className="flex items-center justify-between">
              <div>
                <div className="kpi-title">Disponível</div>
                <div className="kpi-value">{formatNumber(data.kpis.total_disponivel)}</div>
              </div>
              <InboxOutlined className="kpi-icon" />
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8} lg={4}>
          <Card className="kpi-card kpi-5" bordered={false}>
            <div className="flex items-center justify-between">
              <div>
                <div className="kpi-title">Coleções ativas</div>
                <div className="kpi-value">{formatNumber(data.kpis.colecoes_diferentes)}</div>
              </div>
              <AppstoreOutlined className="kpi-icon" />
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8} lg={4}>
          <Card className="kpi-card kpi-6" bordered={false}>
            <div className="flex items-center justify-between">
              <div>
                <div className="kpi-title">Valor total</div>
                <div className="kpi-value">{formatCurrency(data.kpis.valor_total)}</div>
              </div>
              <DollarOutlined className="kpi-icon" />
            </div>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} className="mb-6">
        <Col xs={24} lg={12}>
          <Card className="chart-card" bordered={false} title={(
            <Space>
              <ShoppingCartOutlined />
              <span className="chart-title">Quantidade por Coleção</span>
            </Space>
          )}>
            <BarList
              data={data.por_colecao}
              labelKey="colecao"
              valueKey="quantidade"
              percentKey="percentual"
              color="linear-gradient(90deg, #339af0, #20c997)"
              emptyLabel="Sem dados de coleção"
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card className="chart-card" bordered={false} title={(
            <Space>
              <BookOutlined />
              <span className="chart-title">Top Produtos (o que compram mais)</span>
            </Space>
          )}>
            <BarList
              data={data.top_produtos}
              labelKey="produto"
              valueKey="quantidade"
              percentKey="percentual"
              color="linear-gradient(90deg, #ff6b6b, #f06595)"
              emptyLabel="Sem dados de produtos"
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} className="mb-6">
        <Col xs={24} lg={14}>
          <Card className="chart-card" bordered={false} title={(
            <Space>
              <EnvironmentOutlined />
              <span className="chart-title">Quem compra mais (Municípios)</span>
            </Space>
          )}>
            <Table
              dataSource={data.top_municipios}
              columns={topMunicipiosColumns}
              rowKey={(record) => `${record.municipio}-${record.uf}`}
              pagination={false}
            />
          </Card>
        </Col>
        <Col xs={24} lg={10}>
          <Card className="chart-card" bordered={false} title={(
            <Space>
              <AppstoreOutlined />
              <span className="chart-title">Compras por Ano de Uso</span>
            </Space>
          )}>
            <MiniBars data={data.por_ano} labelKey="ano_uso" valueKey="quantidade" />
            <div className="legend-line mt-4">
              <span className="legend-dot" />
              <span>Distribuição anual do volume comprado</span>
            </div>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card className="chart-card" bordered={false} title={(
            <Space>
              <EnvironmentOutlined />
              <span className="chart-title">Quem compra mais vezes</span>
            </Space>
          )}>
            <BarList
              data={data.top_frequencia}
              labelKey="municipio"
              valueKey="compras"
              color="linear-gradient(90deg, #20c997, #12b886)"
              colorScale={percentColorScale}
              emptyLabel="Sem dados de frequência"
              valueFormatter={(value) => `${formatNumber(value)} compras`}
            />
            <PercentLegend />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card className="chart-card" bordered={false} title={(
            <Space>
              <AppstoreOutlined />
              <span className="chart-title">Tipo de Compra</span>
            </Space>
          )}>
            <BarList
              data={data.por_tipo_compra}
              labelKey="tipo_compra"
              valueKey="quantidade"
              color="linear-gradient(90deg, #ffa94d, #ff922b)"
              emptyLabel="Sem dados de tipo de compra"
            />
          </Card>
        </Col>
      </Row>
    </section>
  );
}
