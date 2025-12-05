/**
 * App Principal - AS v2 Frontend
 *
 * Roteamento para todas as páginas do sistema.
 * PR15: RBAC e menu dinâmico por perfil
 * Issue #207: Code-splitting com React.lazy() para reduzir bundle size
 */

import { useState, useEffect, lazy, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, Navigate } from 'react-router-dom';
import { ConfigProvider, Layout, Menu, Spin, Result, Typography, Button, message, Badge } from 'antd';
import logger from './utils/logger';
import {
  CalendarOutlined,
  CheckCircleOutlined,
  TableOutlined,
  ShoppingOutlined,
  DatabaseOutlined,
  FileTextOutlined,
  SafetyOutlined,
  CloudUploadOutlined,
  UserOutlined,
  BarChartOutlined,
  GlobalOutlined,
  HomeOutlined,
  LogoutOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import ptBR from 'antd/locale/pt_BR';
import { getMe } from './api/availability';
import { logout as apiLogout } from './api/auth';
import './App.css';

// ============================================================================
// Issue #207: Lazy loading de páginas para code-splitting
// ============================================================================
const DisponibilidadeBlocks = lazy(() => import('./pages/Disponibilidade'));
const MonthlyPage = lazy(() => import('./pages/Disponibilidade/MonthlyPage'));
const ControlePage = lazy(() => import('./pages/Controle/ControlePage'));
const EtlReportsPage = lazy(() => import('./pages/Controle/EtlReportsPage'));
const DATPage = lazy(() => import('./pages/DAT/DATPage'));
const NewSolicitacaoWizard = lazy(() => import('./pages/Solicitacoes/NewSolicitacaoWizard'));
const MySolicitacoesPage = lazy(() => import('./pages/Solicitacoes/MySolicitacoesPage'));
const ApprovalsPage = lazy(() => import('./pages/Aprovacoes/ApprovalsPage'));
const PreAgendaPage = lazy(() => import('./pages/PreAgenda/PreAgendaPage'));
const LoginPage = lazy(() => import('./pages/Auth/LoginPage'));
const HomePage = lazy(() => import('./pages/Home/HomePage'));
const DashboardsPage = lazy(() => import('./pages/Dashboards/DashboardsPage'));
const EquipeDashboardPage = lazy(() => import('./pages/Dashboards/EquipeDashboardPage'));
const GCalDashboardPage = lazy(() => import('./pages/Dashboards/GCalDashboardPage'));
const MapaBrasilPage = lazy(() => import('./pages/MapaBrasil/MapaBrasilPage'));
const AdminDATHomePage = lazy(() => import('./pages/AdminDAT/AdminDATHomePage'));
const UsuariosPage = lazy(() => import('./pages/AdminDAT/UsuariosPage'));
const MunicipiosPage = lazy(() => import('./pages/AdminDAT/MunicipiosPage'));
const ProjetosPage = lazy(() => import('./pages/AdminDAT/ProjetosPage'));
const GruposPage = lazy(() => import('./pages/AdminDAT/GruposPage'));
const ConfiguracoesPage = lazy(() => import('./pages/AdminDAT/ConfiguracoesPage'));
const DeslocamentosPage = lazy(() => import('./pages/Deslocamentos/DeslocamentosPage'));

const { Header, Content, Sider } = Layout;
const { SubMenu } = Menu;
const { Text } = Typography;

// Componente de loading para Suspense
function PageLoader() {
  return (
    <div style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      height: '100%',
      minHeight: '300px'
    }}>
      <Spin size="large" tip="Carregando página..." />
    </div>
  );
}

// Componente 403 Forbidden
function Forbidden() {
  return <Result status="403" title="Sem permissão" subTitle="Você não tem permissão para acessar esta página." />;
}

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Issue #97: GCal Alerts (badge + toast)
  const [alerts, setAlerts] = useState({ errors: 0, pending: 0, published: 0, none: 0 });
  const [lastErrorsCount, setLastErrorsCount] = useState(0);
  const [cooldownUntil, setCooldownUntil] = useState(0);

  // Carregar dados do usuário
  const loadUser = async () => {
    try {
      const userData = await getMe();
      setUser(userData);
    } catch (error) {
      logger.error('Erro ao carregar usuário:', error);
      setUser(null); // Explicitamente null se falhar
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUser();
  }, []);

  // Issue #97: Polling de alertas GCal (badge + toast)
  useEffect(() => {
    // Só ativar polling para Controle/Super
    const canControle = user?.groups?.includes('Controle');
    const canSuper = user?.is_superuser || user?.is_superintendencia || user?.groups?.includes('Superintendência');

    if (!canControle && !canSuper) {
      return; // Não tem permissão, não fazer polling
    }

    const POLL_MS = 30000; // 30 segundos
    const COOLDOWN_MS = 120000; // 2 minutos de cooldown para toast

    const fetchAlerts = async () => {
      try {
        const response = await fetch('/api/gcal/dashboard/alerts/summary/', {
          credentials: 'include'
        });

        if (!response.ok) {
          if (response.status === 401 || response.status === 403) {
            logger.warn('[Alerts] Sem permissão para acessar alerts');
            return;
          }
          throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        setAlerts(data);

        // Toast quando errors aumentar (com cooldown)
        const now = Date.now();
        if (data.errors > lastErrorsCount && now > cooldownUntil) {
          message.warning(
            `Novos erros de publicação detectados (${lastErrorsCount} → ${data.errors})`,
            5 // duração 5s
          );
          setCooldownUntil(now + COOLDOWN_MS);
        }

        // Atualizar lastErrorsCount e persistir em localStorage
        if (data.errors !== lastErrorsCount) {
          setLastErrorsCount(data.errors);
          localStorage.setItem('gcalAlertsLastErrors', data.errors.toString());
        }
      } catch (error) {
        logger.error('[Alerts] Erro ao buscar alertas:', error);
      }
    };

    // Carregar lastErrorsCount do localStorage na inicialização
    const stored = localStorage.getItem('gcalAlertsLastErrors');
    if (stored) {
      setLastErrorsCount(parseInt(stored, 10) || 0);
    }

    // Fetch inicial
    fetchAlerts();

    // Polling a cada 30s
    const intervalId = setInterval(fetchAlerts, POLL_MS);

    // Cleanup: parar polling no unmount
    return () => clearInterval(intervalId);
  }, [user, lastErrorsCount, cooldownUntil]);

  if (loading) {
    return <Spin size="large" tip="Carregando..." fullscreen />;
  }

  // Se não autenticado, mostrar página de login
  if (!user) {
    return (
      <ConfigProvider locale={ptBR}>
        <Suspense fallback={<Spin size="large" tip="Carregando..." fullscreen />}>
          <LoginPage onLoginSuccess={loadUser} />
        </Suspense>
      </ConfigProvider>
    );
  }

  // Função de logout
  const handleLogout = async () => {
    try {
      await apiLogout();
      message.success('Logout realizado com sucesso');
      // Recarregar a página para voltar para tela de login
      window.location.reload();
    } catch (error) {
      message.error('Erro ao fazer logout');
      logger.error('Erro no logout:', error);
    }
  };

  // Calcular flags de permissão (RBAC correto)
  const canCoordenador = user?.is_superuser || user?.groups?.includes('Coordenador') || user?.groups?.includes('Apoio de Coordenação') || user?.groups?.includes('DAT');
  // canSuper = pode aprovar/reprovar (Superintendência) - NÃO dá acesso a dashboards
  const canSuper = user?.is_superuser || user?.is_superintendencia || user?.groups?.includes('Superintendência');
  const canControle = user?.is_superuser || user?.groups?.includes('Controle');
  const canDAT = user?.is_superuser || user?.groups?.includes('DAT');
  // isAdmin = apenas superusers (NÃO inclui Superintendência)
  const isAdmin = user?.is_superuser;
  // isManager = Gerência (dashboards, métricas) - NÃO inclui Superintendência
  const isManager = user?.groups?.includes('Gerência') || isAdmin;

  return (
    <ConfigProvider locale={ptBR}>
      <Router>
        <Layout style={{ minHeight: '100vh' }}>
          {/* Sider lateral fixo */}
          <Sider
            width={250}
            style={{
              overflow: 'auto',
              height: '100vh',
              position: 'fixed',
              left: 0,
              top: 0,
              bottom: 0,
            }}
          >
            {/* Logo/Título */}
            <div style={{
              height: '64px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white',
              fontSize: '22px',
              fontWeight: 'bold',
              borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
            }}>
              AS v2
            </div>

            {/* Menu vertical */}
            <Menu
              theme="dark"
              mode="inline"
              defaultSelectedKeys={['disponibilidade']}
              style={{ borderRight: 0 }}
            >
              <Menu.Item key="home" icon={<HomeOutlined />}>
                <Link to="/home">Página Inicial</Link>
              </Menu.Item>

              <Menu.Item key="grade-mensal" icon={<TableOutlined />}>
                <Link to="/disponibilidade">Grade Mensal</Link>
              </Menu.Item>

              {/* Dashboards (Admin/Gerência) */}
              {isManager && (
                <Menu.Item key="dashboards" icon={<BarChartOutlined />}>
                  <Link to="/dashboards">Dashboards</Link>
                </Menu.Item>
              )}

              {/* Dashboard Equipe (Controle/Gerência) - Issue #190 */}
              {(canControle || isManager) && (
                <Menu.Item key="dashboard-equipe" icon={<BarChartOutlined />}>
                  <Link to="/dashboards/equipe">Dashboard Equipe</Link>
                </Menu.Item>
              )}

              {/* GCal Dashboard (Controle only) */}
              {canControle && (
                <Menu.Item key="gcal-dashboard" icon={<SyncOutlined />}>
                  <Link to="/dashboard/gcal">
                    <Badge count={alerts.errors} offset={[10, 0]} size="small">
                      Dashboard GCal
                    </Badge>
                  </Link>
                </Menu.Item>
              )}

              {/* Mapa do Brasil (Admin/Gerência) */}
              {isManager && (
                <Menu.Item key="mapa-brasil" icon={<GlobalOutlined />}>
                  <Link to="/mapa-brasil">Mapa do Brasil</Link>
                </Menu.Item>
              )}

              {/* Bloqueios (NOT for Superintendência) */}
              {(canControle || canCoordenador || user?.groups?.includes('Formador')) && (
                <Menu.Item key="bloqueios" icon={<CalendarOutlined />}>
                  <Link to="/bloqueios">Bloqueios</Link>
                </Menu.Item>
              )}

              {/* Submenu Solicitações (Coordenador + DAT) */}
              {canCoordenador && (
                <SubMenu key="solicitacoes-submenu" icon={<FileTextOutlined />} title="Solicitações">
                  <Menu.Item key="minhas-solicitacoes">
                    <Link to="/solicitacoes/minhas">Minhas Solicitações</Link>
                  </Menu.Item>
                  <Menu.Item key="nova-solicitacao">
                    <Link to="/solicitacoes/nova">Nova Solicitação</Link>
                  </Menu.Item>
                </SubMenu>
              )}

              {/* Aprovações (Superintendência) */}
              {canSuper && (
                <Menu.Item key="aprovacoes" icon={<SafetyOutlined />}>
                  <Link to="/aprovacoes">Aprovações</Link>
                </Menu.Item>
              )}

              {/* Pré-agenda (Controle) */}
              {canControle && (
                <Menu.Item key="pre-agenda" icon={<CheckCircleOutlined />}>
                  <Link to="/pre-agenda">Pré-agenda</Link>
                </Menu.Item>
              )}

              {/* Ops Panels (Controle/Coordenador) */}
              {(canControle || canCoordenador) && (
                <SubMenu key="ops-submenu" icon={<ShoppingOutlined />} title="Ops">
                  {canControle && (
                    <>
                      <Menu.Item key="controle-ops">
                        <Link to="/controle">Controle</Link>
                      </Menu.Item>
                      <Menu.Item key="dat-ops">
                        <Link to="/dat">DAT</Link>
                      </Menu.Item>
                    </>
                  )}
                  <Menu.Item key="deslocamentos">
                    <Link to="/deslocamentos">Deslocamentos</Link>
                  </Menu.Item>
                </SubMenu>
              )}

              {/* Relatórios ETL (Controle only) */}
              {canControle && (
                <Menu.Item key="etl-reports" icon={<FileTextOutlined />}>
                  <Link to="/controle/etl-reports">Relatórios ETL</Link>
                </Menu.Item>
              )}

              {/* Admin DAT (DAT + Superusers) */}
              {canDAT && (
                <Menu.Item key="admin-dat" icon={<DatabaseOutlined />}>
                  <Link to="/admin-dat">Admin DAT</Link>
                </Menu.Item>
              )}
            </Menu>
          </Sider>

          {/* Layout com margem para compensar Sider fixo */}
          <Layout style={{ marginLeft: 250, minHeight: '100vh' }}>
            {/* Header com info do usuário */}
            <Header style={{
              background: '#fff',
              padding: '0 24px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'flex-end',
              borderBottom: '1px solid #f0f0f0',
              width: '100%',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px', whiteSpace: 'nowrap' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <UserOutlined />
                  <Text strong>{user?.name || user?.username || 'Usuário'}</Text>
                </div>
                <Button
                  type="primary"
                  danger
                  icon={<LogoutOutlined />}
                  onClick={handleLogout}
                >
                  Sair
                </Button>
              </div>
            </Header>

            {/* Conteúdo principal com Suspense para lazy loading */}
            <Content style={{ padding: '0', minHeight: 'calc(100vh - 64px)', background: '#f0f2f5' }}>
              <Suspense fallback={<PageLoader />}>
                <Routes>
                  <Route path="/" element={<HomePage />} />
                  <Route path="/home" element={<HomePage />} />

                  {/* Dashboards (Admin/Gerência) */}
                  <Route
                    path="/dashboards"
                    element={isManager ? <DashboardsPage /> : <Forbidden />}
                  />

                  {/* Dashboard Equipe (Controle/Gerência) - Issue #190 */}
                  <Route
                    path="/dashboards/equipe"
                    element={(canControle || isManager) ? <EquipeDashboardPage /> : <Forbidden />}
                  />

                  {/* GCal Dashboard (Controle/Super) */}
                  <Route
                    path="/dashboard/gcal"
                    element={(canControle || canSuper) ? <GCalDashboardPage /> : <Forbidden />}
                  />

                  {/* Mapa do Brasil (Admin/Gerência) */}
                  <Route
                    path="/mapa-brasil"
                    element={isManager ? <MapaBrasilPage /> : <Forbidden />}
                  />

                  <Route path="/disponibilidade" element={<MonthlyPage />} />
                  <Route path="/bloqueios" element={<DisponibilidadeBlocks />} />

                  {/* PR15: Novas rotas de solicitações */}
                  <Route
                    path="/solicitacoes/minhas"
                    element={canCoordenador ? <MySolicitacoesPage /> : <Forbidden />}
                  />
                  <Route
                    path="/solicitacoes/nova"
                    element={canCoordenador ? <NewSolicitacaoWizard /> : <Forbidden />}
                  />

                  {/* PR15: Rota de aprovações */}
                  <Route
                    path="/aprovacoes"
                    element={canSuper ? <ApprovalsPage /> : <Forbidden />}
                  />

                  {/* PR15: Rota de pré-agenda */}
                  <Route
                    path="/pre-agenda"
                    element={canControle ? <PreAgendaPage /> : <Forbidden />}
                  />

                  {/* Issue #188: Deslocamentos (Controle/Coordenador/DAT) */}
                  <Route
                    path="/deslocamentos"
                    element={(canControle || canCoordenador || canDAT) ? <DeslocamentosPage /> : <Forbidden />}
                  />

                  {/* Admin DAT (Fase 1 - Plano DAT/GCal) */}
                  <Route
                    path="/admin-dat"
                    element={canDAT ? <AdminDATHomePage /> : <Forbidden />}
                  />
                  <Route
                    path="/admin-dat/usuarios"
                    element={canDAT ? <UsuariosPage /> : <Forbidden />}
                  />
                  <Route
                    path="/admin-dat/municipios"
                    element={canDAT ? <MunicipiosPage /> : <Forbidden />}
                  />
                  <Route
                    path="/admin-dat/projetos"
                    element={canDAT ? <ProjetosPage /> : <Forbidden />}
                  />
                  <Route
                    path="/admin-dat/grupos"
                    element={canDAT ? <GruposPage /> : <Forbidden />}
                  />
                  <Route
                    path="/admin-dat/configuracoes"
                    element={canDAT ? <ConfiguracoesPage /> : <Forbidden />}
                  />

                  {/* Antigas rotas (manter compatibilidade) */}
                  <Route path="/controle" element={<ControlePage />} />
                  <Route
                    path="/controle/etl-reports"
                    element={canControle || canSuper ? <EtlReportsPage /> : <Forbidden />}
                  />
                  <Route path="/dat" element={<DATPage />} />
                </Routes>
              </Suspense>
            </Content>
          </Layout>
        </Layout>
      </Router>
    </ConfigProvider>
  );
}

export default App;
