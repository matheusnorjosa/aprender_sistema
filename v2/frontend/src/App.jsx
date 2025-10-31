/**
 * App Principal - AS v2 Frontend
 *
 * Roteamento para todas as páginas do sistema.
 * PR15: RBAC e menu dinâmico por perfil
 */

import { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, Navigate } from 'react-router-dom';
import { ConfigProvider, Layout, Menu, Spin, Result, Typography, Button, message } from 'antd';
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
} from '@ant-design/icons';
import ptBR from 'antd/locale/pt_BR';
import DisponibilidadeBlocks from './pages/Disponibilidade';
import MonthlyPage from './pages/Disponibilidade/MonthlyPage';
import Solicitacoes from './pages/Solicitacoes';
import ControlePage from './pages/Controle/ControlePage';
import EtlReportsPage from './pages/Controle/EtlReportsPage';
import DATPage from './pages/DAT/DATPage';
import NewSolicitacaoWizard from './pages/Solicitacoes/NewSolicitacaoWizard';
import MySolicitacoesPage from './pages/Solicitacoes/MySolicitacoesPage';
import ApprovalsPage from './pages/Aprovacoes/ApprovalsPage';
import PreAgendaPage from './pages/PreAgenda/PreAgendaPage';
import LoginPage from './pages/Auth/LoginPage';
import HomePage from './pages/Home/HomePage';
import DashboardsPage from './pages/Dashboards/DashboardsPage';
import MapaBrasilPage from './pages/MapaBrasil/MapaBrasilPage';
import AdminDATHomePage from './pages/AdminDAT/AdminDATHomePage';
import UsuariosPage from './pages/AdminDAT/UsuariosPage';
import MunicipiosPage from './pages/AdminDAT/MunicipiosPage';
import ProjetosPage from './pages/AdminDAT/ProjetosPage';
import GruposPage from './pages/AdminDAT/GruposPage';
import { getMe } from './api/availability';
import './App.css';

const { Header, Content, Sider } = Layout;
const { SubMenu } = Menu;
const { Text } = Typography;

// Componente 403 Forbidden
function Forbidden() {
  return <Result status="403" title="Sem permissão" subTitle="Você não tem permissão para acessar esta página." />;
}

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Carregar dados do usuário
  const loadUser = async () => {
    try {
      const userData = await getMe();
      setUser(userData);
    } catch (error) {
      console.error('Erro ao carregar usuário:', error);
      setUser(null); // Explicitamente null se falhar
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUser();
  }, []);

  if (loading) {
    return <Spin size="large" tip="Carregando..." fullscreen />;
  }

  // Se não autenticado, mostrar página de login
  if (!user) {
    return (
      <ConfigProvider locale={ptBR}>
        <LoginPage onLoginSuccess={loadUser} />
      </ConfigProvider>
    );
  }

  // Função de logout
  const handleLogout = async () => {
    try {
      await fetch('/api/auth/logout/', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      message.success('Logout realizado com sucesso');
      // Recarregar a página para voltar para tela de login
      window.location.reload();
    } catch (error) {
      message.error('Erro ao fazer logout');
      console.error('Erro no logout:', error);
    }
  };

  // Calcular flags de permissão
  const canCoordenador = user?.is_superuser || user?.groups?.includes('Coordenador') || user?.groups?.includes('DAT');
  const canSuper = user?.is_superuser || user?.is_superintendencia || user?.groups?.includes('Superintendência');
  const canControle = user?.is_superuser || user?.groups?.includes('Controle');
  const canDAT = user?.is_superuser || user?.groups?.includes('DAT');
  const isAdmin = user?.is_superuser || user?.groups?.includes('Superintendência');
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

              {/* Mapa do Brasil (Admin/Gerência) */}
              {isManager && (
                <Menu.Item key="mapa-brasil" icon={<GlobalOutlined />}>
                  <Link to="/mapa-brasil">Mapa do Brasil</Link>
                </Menu.Item>
              )}

              <Menu.Item key="bloqueios" icon={<CalendarOutlined />}>
                <Link to="/bloqueios">Bloqueios</Link>
              </Menu.Item>

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

              {/* Ops Panels (Controle) */}
              {canControle && (
                <SubMenu key="ops-submenu" icon={<ShoppingOutlined />} title="Ops">
                  <Menu.Item key="controle-ops">
                    <Link to="/controle">Controle</Link>
                  </Menu.Item>
                  <Menu.Item key="dat-ops">
                    <Link to="/dat">DAT</Link>
                  </Menu.Item>
                </SubMenu>
              )}

              {/* Relatórios ETL (Controle + Superintendência) */}
              {(canControle || canSuper) && (
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

              {/* Fallback: Antigas páginas */}
              <Menu.Item key="solicitacoes-old" icon={<CheckCircleOutlined />}>
                <Link to="/solicitacoes">Solicitações (Old)</Link>
              </Menu.Item>
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

            {/* Conteúdo principal */}
            <Content style={{ padding: '0', minHeight: 'calc(100vh - 64px)', background: '#f0f2f5' }}>
              <Routes>
                <Route path="/" element={<HomePage />} />
                <Route path="/home" element={<HomePage />} />

                {/* Dashboards (Admin/Gerência) */}
                <Route
                  path="/dashboards"
                  element={isManager ? <DashboardsPage /> : <Forbidden />}
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

                {/* Antigas rotas (manter compatibilidade) */}
                <Route path="/solicitacoes" element={<Solicitacoes />} />
                <Route path="/controle" element={<ControlePage />} />
                <Route
                  path="/controle/etl-reports"
                  element={canControle || canSuper ? <EtlReportsPage /> : <Forbidden />}
                />
                <Route path="/dat" element={<DATPage />} />
              </Routes>
            </Content>
          </Layout>
        </Layout>
      </Router>
    </ConfigProvider>
  );
}

export default App;
