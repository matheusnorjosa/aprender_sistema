/**
 * Home Dashboard - AS v2
 *
 * Design: paginainicial/screen.png
 * - Cards organizados por nível de acesso (Administrator, Manager, General)
 * - KPI badges com contagens
 * - Links rápidos baseados em RBAC
 */

import { useState, useEffect } from 'react';
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

const { Title, Text } = Typography;

/**
 * Card de acesso rápido
 */
function AccessCard({ icon, title, description, link, badge, disabled = false }) {
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
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ fontSize: '32px', color: '#1890ff' }}>
            {icon}
          </div>
          {badge !== undefined && (
            <Badge count={badge} overflowCount={999} style={{ backgroundColor: '#52c41a' }} />
          )}
        </div>
        <div>
          <Title level={5} style={{ marginBottom: 4 }}>{title}</Title>
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

export default function HomePage() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    pendingApprovals: 0,
    myRequests: 0,
    upcomingEvents: 0,
  });

  useEffect(() => {
    const loadUserAndStats = async () => {
      try {
        const userData = await getMe();
        setUser(userData);

        // TODO: Carregar estatísticas reais da API
        // Por enquanto, valores mockados
        setStats({
          pendingApprovals: 5,
          myRequests: 3,
          upcomingEvents: 12,
        });
      } catch (error) {
        console.error('Erro ao carregar dados:', error);
      } finally {
        setLoading(false);
      }
    };

    loadUserAndStats();
  }, []);

  if (loading) {
    return (
      <div style={{ padding: '24px', textAlign: 'center' }}>
        <Spin size="large" tip="Carregando..." />
      </div>
    );
  }

  // Calcular permissões (RBAC com Setor + Função)
  const setores = user?.setores || [];
  const funcoes = user?.funcoes || [];

  // isAdmin = apenas superusers (acesso administrativo completo)
  const isAdmin = user?.is_superuser;
  // canApproveSuper = pode aprovar solicitações SUPER (Gerente + Superintendência)
  const canApproveSuper = user?.can_approve_super || false;
  // isManager = Gerente de qualquer setor (dashboards, métricas)
  const isGerente = user?.is_superuser || funcoes.includes('Gerente');
  const isManager = isGerente && (setores.includes('Gerência') || isAdmin);
  // isCoordenador = pode criar solicitações
  const isCoordenador = user?.is_superuser || funcoes.includes('Coordenador') || funcoes.includes('Apoio de Coordenação') || setores.includes('DAT');
  // canDAT = acesso ao Admin DAT
  const canDAT = user?.is_superuser || setores.includes('DAT');

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: 32 }}>
        <Title level={2}>Página Inicial</Title>
        <Text type="secondary">
          Atalhos e KPIs resumidos para suas tarefas diárias.
        </Text>
      </div>

      {/* Acesso Administrativo */}
      {isAdmin && (
        <>
          <Title level={4} style={{ marginTop: 24, marginBottom: 16 }}>
            Acesso Administrativo
          </Title>
          <Row gutter={[16, 16]}>
            {canDAT && (
              <Col xs={24} sm={12} md={8}>
                <AccessCard
                  icon={<UserOutlined />}
                  title="Gerenciamento de Usuários"
                  description="Gerenciar usuários, grupos e permissões."
                  link="/admin-dat/usuarios"
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

      {/* Aprovações (Gerente + Superintendência) */}
      {canApproveSuper && (
        <>
          <Title level={4} style={{ marginTop: 24, marginBottom: 16 }}>
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
          <Title level={4} style={{ marginTop: 24, marginBottom: 16 }}>
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
      <Title level={4} style={{ marginTop: 24, marginBottom: 16 }}>
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
      <Card style={{ marginTop: 32 }}>
        <Title level={4} style={{ marginBottom: 16 }}>
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
