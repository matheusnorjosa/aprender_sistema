/**
 * Painel de Controle — hub da seção Controle (#1984).
 *
 * Substitui a antiga lista de compras (que era redundante com /controle/compras e
 * lia o modelo legado core.Compra): agora é uma landing com KPIs de contagem REAIS
 * (sem valor financeiro) + atalhos de navegação para as sub-páginas.
 */

import { useEffect, useState, type JSX } from 'react';
import { Link } from 'react-router';
import { Alert, Card, Col, Row, Spin, Statistic, Typography } from 'antd';
import {
  CalendarOutlined,
  ProjectOutlined,
  ScheduleOutlined,
  ShoppingCartOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import {
  getAcoesStats,
  getComprasStats,
  getPlanoFormacoesStats,
  listCoordenadoresDAT,
} from '../../api/datModule';
import DatImportsCentralizedBanner from '../../components/DatImportsCentralizedBanner';

const { Title, Text } = Typography;

const toNum = (v: unknown): number => (typeof v === 'number' ? v : Number(v) || 0);

interface Kpis {
  acoes: number;
  compras: number;
  planos: number;
  coordenadores: number;
}

const NAV_TILES = [
  { to: '/controle/acoes', label: 'Ações', icon: <ProjectOutlined /> },
  { to: '/controle/compras', label: 'Compras', icon: <ShoppingCartOutlined /> },
  { to: '/controle/coordenadores', label: 'Coordenadores', icon: <TeamOutlined /> },
  { to: '/controle/plano-formacoes', label: 'Plano Anual', icon: <CalendarOutlined /> },
  { to: '/controle/pre-agenda', label: 'Pré-agenda', icon: <ScheduleOutlined /> },
] as const;

export default function ControlePage(): JSX.Element {
  const [kpis, setKpis] = useState<Kpis | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const load = async (): Promise<void> => {
      setLoading(true);
      setError(null);
      try {
        const [acoes, compras, planos, coord] = await Promise.all([
          getAcoesStats(),
          getComprasStats(),
          getPlanoFormacoesStats(),
          listCoordenadoresDAT({ page: 1 }),
        ]);
        if (!active) return;
        setKpis({
          acoes: toNum(acoes['total']),
          compras: toNum(compras['total']),
          planos: toNum(planos['total_planos']),
          coordenadores: toNum(coord.count),
        });
      } catch (err) {
        if (active) setError((err as Error).message || 'Erro ao carregar indicadores');
      } finally {
        if (active) setLoading(false);
      }
    };
    void load();
    return () => {
      active = false;
    };
  }, []);

  const cards: Array<{ title: string; value: number; icon: JSX.Element }> = [
    { title: 'Ações', value: kpis?.acoes ?? 0, icon: <ProjectOutlined /> },
    { title: 'Compras', value: kpis?.compras ?? 0, icon: <ShoppingCartOutlined /> },
    { title: 'Planos de formação', value: kpis?.planos ?? 0, icon: <CalendarOutlined /> },
    { title: 'Coordenadores', value: kpis?.coordenadores ?? 0, icon: <TeamOutlined /> },
  ];

  return (
    <main className="p-6" aria-labelledby="controle-title">
      <header className="mb-6">
        <Title level={3} id="controle-title" className="!mb-1">Painel de Controle</Title>
        <Text type="secondary">
          Visão geral da seção Controle — ações, compras, planos de formação e coordenadores.
        </Text>
      </header>

      <DatImportsCentralizedBanner className="mb-6" />

      {error && (
        <Alert
          type="error"
          showIcon
          className="mb-4"
          message="Erro ao carregar indicadores"
          description={error}
        />
      )}

      <Spin spinning={loading}>
        <Row gutter={[16, 16]} className="mb-8">
          {cards.map((c) => (
            <Col xs={12} md={6} key={c.title}>
              <Card variant="borderless">
                <Statistic title={c.title} value={c.value} prefix={c.icon} groupSeparator="." />
              </Card>
            </Col>
          ))}
        </Row>
      </Spin>

      <Title level={5} className="!mb-3">Atalhos</Title>
      <Row gutter={[16, 16]}>
        {NAV_TILES.map((t) => (
          <Col xs={12} sm={8} md={6} lg={4} key={t.to}>
            <Link to={t.to}>
              <Card hoverable variant="borderless" className="text-center">
                <div className="text-2xl mb-2" aria-hidden="true">{t.icon}</div>
                <Text strong>{t.label}</Text>
              </Card>
            </Link>
          </Col>
        ))}
      </Row>
    </main>
  );
}
