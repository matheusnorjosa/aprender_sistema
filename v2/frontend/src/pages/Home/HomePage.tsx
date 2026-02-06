/**
 * Home Dashboard - AS v2
 *
 * Design: paginainicial/screen.png
 * - Cards organizados por nível de acesso (Administrator, Manager, General)
 * - KPI badges com contagens
 * - Links rápidos baseados em RBAC
 */

import { useState, useEffect, ReactNode, JSX } from 'react';
import { Link } from 'react-router-dom';
import { Row, Col, Card, Typography, Badge, Space, Spin, Statistic } from 'antd';
import {
  UserOutlined,
  BarChartOutlined,
  CheckCircleOutlined,
  TeamOutlined,
  DashboardOutlined,
  FileTextOutlined,
  ShoppingOutlined,
  SafetyOutlined,
} from '@ant-design/icons';
import { getMe } from '../../api/availability';
import { getHomeStats } from '../../api/stats';
import logger from '../../utils/logger';
import type { CurrentUser } from '../../types';

const { Title, Text } = Typography;

/** Stats type */
interface StatsType {
  pendingApprovals: number;
  myRequests: number;
  upcomingEvents: number;
}

/** Home stats API response */
interface HomeStatsResponse {
  pending_approvals?: number;
  my_requests?: number;
  upcoming_events?: number;
}

/** Access card props */
interface AccessCardProps {
  icon: ReactNode;
  title: string;
  description: string;
  link?: string;
  badge?: number;
  disabled?: boolean;
}

/**
 * Card de acesso rápido
 */
function AccessCard({ icon, title, description, link, badge, disabled = false }: AccessCardProps): JSX.Element {
  const cardContent = (
    <Card
      hoverable={!disabled}
      style={{
        height: '100%',
        opacity: disabled ? 0.5 : 1,
        cursor: disabled ? 'not-allowed' : 'pointer',
      }}
    >
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        <div className="flex justify-between items-center">
          <div style={{ fontSize: '32px', color: '#004B3D' }}>
            {icon}
          </div>
          {badge !== undefined && (
            <Badge count={badge} overflowCount={999} style={{ backgroundColor: '#52c41a' }} />
          )}
        </div>
        <div>
          <Title level={5} className="mb-1">{title}</Title>
          <Text type="secondary">{description}</Text>
        </div>
      </Space>
    </Card>
  );

  if (disabled || !link) {
    return cardContent;
  }

  return <Link to={link}>{cardContent}</Link>;
}

export default function HomePage(): JSX.Element {
  const [user, setUser] = useState<(CurrentUser & { can_approve_super?: boolean }) | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [stats, setStats] = useState<StatsType>({
    pendingApprovals: 0,
    myRequests: 0,
    upcomingEvents: 0,
  });

  useEffect(() => {
    const loadUserAndStats = async (): Promise<void> => {
      try {
        // Carregar dados do usuário e estatísticas em paralelo
        const [userData, statsData] = await Promise.all([
          getMe() as Promise<CurrentUser & { can_approve_super?: boolean }>,
          getHomeStats() as Promise<HomeStatsResponse>,
        ]);

        setUser(userData);
        setStats({
          pendingApprovals: statsData.pending_approvals ?? 0,
          myRequests: statsData.my_requests ?? 0,
          upcomingEvents: statsData.upcoming_events ?? 0,
        });
      } catch (error) {
        logger.error('Erro ao carregar dados:', error);
      } finally {
        setLoading(false);
      }
    };

    loadUserAndStats();
  }, []);

  if (loading) {
    return (
      <div className="p-6 text-center">
        <Spin size="large" tip="Carregando..." />
      </div>
    );
  }

  // Calcular permissões (RBAC com Setor + Função)
  const setores = user?.setores || [];
  const funcoes = user?.funcoes || [];

  // isAdmin = apenas superusers (acesso administrativo completo)
  const isAdmin = user?.is_superuser;
  // canApproveSuper = pode aprovar/reprovar solicitações (Superintendência/DAT)
  const canApproveSuper = user?.can_approve_super || false;
  // isManager = Gerente de qualquer setor (dashboards, métricas)
  const isGerente = user?.is_superuser || funcoes.includes('Gerente');
  const isManager = isGerente && (setores.includes('Gerência') || isAdmin);
  // isCoordenador = pode criar solicitações
  const isCoordenador = user?.is_superuser || funcoes.includes('Coordenador') || funcoes.includes('Apoio de Coordenação') || setores.includes('DAT');
  // canDAT = acesso ao Admin DAT
  const canDAT = user?.is_superuser || setores.includes('DAT');

  return (
    <div className="p-6">
      <div className="mb-8">
        <Title level={2}>Página Inicial</Title>
        <Text type="secondary">
          Atalhos e KPIs resumidos para suas tarefas diárias.
        </Text>
      </div>

      {/* Acesso Administrativo */}
      {isAdmin && (
        <>
          <Title level={4} className="mt-6 mb-4">
            Acesso Administrativo
          </Title>
          <Row gutter={[16, 16]}>
            {canDAT && (
              <Col xs={24} sm={12} md={8}>
                <AccessCard
                  icon={<UserOutlined />}
                  title="Gerenciamento de Usuários"
                  description="Gerenciar usuários, grupos e permissões."
                  link="/dat/admin/usuarios"
                />
              </Col>
            )}
            <Col xs={24} sm={12} md={8}>
              <AccessCard
                icon={<BarChartOutlined />}
                title="Análises"
                description="Visualizar relatórios detalhados e métricas do sistema."
                link="/dashboards"
              />
            </Col>
          </Row>
        </>
      )}

      {/* Aprovações (Superintendência/DAT) */}
      {canApproveSuper && (
        <>
          <Title level={4} className="mt-6 mb-4">
            Aprovações
          </Title>
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={12} md={8}>
              <AccessCard
                icon={<CheckCircleOutlined />}
                title="Solicitações de Aprovação"
                description="Revisar e aprovar solicitações pendentes."
                link="/aprovacoes"
                badge={stats.pendingApprovals}
              />
            </Col>
          </Row>
        </>
      )}

      {/* Acesso Gerencial (Gerência) */}
      {isManager && (
        <>
          <Title level={4} className="mt-6 mb-4">
            Acesso Gerencial
          </Title>
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={12} md={8}>
              <AccessCard
                icon={<TeamOutlined />}
                title="Desempenho da Equipe"
                description="Monitorar métricas e desempenho da equipe."
                link="/dashboards/equipe"
              />
            </Col>
          </Row>
        </>
      )}

      {/* Acesso Geral */}
      <Title level={4} className="mt-6 mb-4">
        Acesso Geral
      </Title>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} md={8}>
          <AccessCard
            icon={<DashboardOutlined />}
            title="Meu Painel"
            description="Seu painel pessoal com informações-chave."
            link="/disponibilidade"
          />
        </Col>
        {isCoordenador && (
          <>
            <Col xs={24} sm={12} md={8}>
              <AccessCard
                icon={<FileTextOutlined />}
                title="Enviar Solicitação"
                description="Criar uma nova solicitação de evento."
                link="/solicitacoes/nova"
              />
            </Col>
            <Col xs={24} sm={12} md={8}>
              <AccessCard
                icon={<ShoppingOutlined />}
                title="Minhas Solicitações"
                description="Ver suas solicitações e itens submetidos."
                link="/solicitacoes/minhas"
                badge={stats.myRequests}
              />
            </Col>
          </>
        )}
      </Row>

      {/* KPIs Summary */}
      <Card className="mt-8">
        <Title level={4} className="mb-4">
          Resumo Rápido
        </Title>
        <Row gutter={16}>
          <Col xs={24} sm={8}>
            <Statistic
              title="Eventos Futuros"
              value={stats.upcomingEvents}
              prefix={<SafetyOutlined />}
            />
          </Col>
          {isCoordenador && (
            <Col xs={24} sm={8}>
              <Statistic
                title="Minhas Solicitações"
                value={stats.myRequests}
                prefix={<FileTextOutlined />}
              />
            </Col>
          )}
          {canApproveSuper && (
            <Col xs={24} sm={8}>
              <Statistic
                title="Aprovações Pendentes"
                value={stats.pendingApprovals}
                prefix={<CheckCircleOutlined />}
                valueStyle={{ color: '#cf1322' }}
              />
            </Col>
          )}
        </Row>
      </Card>
    </div>
  );
}
