/**
 * App Principal - AS v2 Frontend
 *
 * Roteamento para todas as páginas do sistema.
 * PR15: RBAC e menu dinâmico por perfil
 * Issue #207: Code-splitting com React.lazy() para reduzir bundle size
 */

import { useState, useEffect, useRef, useCallback, lazy, Suspense, useMemo } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import { ConfigProvider, Layout, Menu, Spin, Result, Typography, Button, message, Badge } from 'antd';
import logger from './utils/logger';
import {
  CalendarOutlined,
  CheckCircleOutlined,
  TableOutlined,
  FileTextOutlined,
  SafetyOutlined,
  UserOutlined,
  BarChartOutlined,
  HomeOutlined,
  LogoutOutlined,
  SolutionOutlined,
} from '@ant-design/icons';
import { ThemeProvider, useTheme, useBrandColors } from './contexts/ThemeContext';
import ptBR from 'antd/locale/pt_BR';
import { getMe } from './api/availability';
import { logout as apiLogout } from './api/auth';
import { LAYOUT, TIMING } from './constants';
import { preloadSearchData } from './services/preloadSearchData';
import OfflineBanner from './components/OfflineBanner';
import type { CurrentUser } from './types';
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
const EditSolicitacaoPage = lazy(() => import('./pages/Solicitacoes/EditSolicitacaoPage'));
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
// DAT Module - Acompanhamento de Turmas (SPEC_DAT_REGISTROS.md)
const DATRegistrosPage = lazy(() => import('./pages/DATModule/DATRegistrosPage'));
// DAT Module - Novas páginas de gestão
const AcoesPage = lazy(() => import('./pages/DATModule/AcoesPage'));
const ComprasPage = lazy(() => import('./pages/DATModule/ComprasPage'));
const CadastrosPage = lazy(() => import('./pages/DATModule/CadastrosPage'));
const FormacoesPage = lazy(() => import('./pages/DATModule/FormacoesPage'));
const PlanoFormacoesPage = lazy(() => import('./pages/DATModule/PlanoFormacoesPage'));
const CoordenadoresPage = lazy(() => import('./pages/DATModule/CoordenadoresPage'));

const { Header, Content, Sider } = Layout;
const { SubMenu } = Menu;
const { Text } = Typography;

/**
 * Alerts summary interface
 */
interface AlertsSummary {
  errors: number;
  pending: number;
  published: number;
  none: number;
}

/**
 * Hook return interface for menu open keys
 */
interface UseMenuOpenKeysReturn {
  openKeys: string[];
  onOpenChange: (keys: string[]) => void;
  closeAllSubmenus: () => void;
}

// Hook para controlar abertura de submenus (apenas um aberto por vez)
function useMenuOpenKeys(): UseMenuOpenKeysReturn {
  const [openKeys, setOpenKeys] = useState<string[]>([]);

  const onOpenChange = (keys: string[]) => {
    // Pegar apenas a última key aberta (fecha as outras)
    const latestOpenKey = keys.find((key) => openKeys.indexOf(key) === -1);
    setOpenKeys(latestOpenKey ? [latestOpenKey] : []);
  };

  // Fecha todos os submenus ao clicar em item fora de submenu
  const closeAllSubmenus = () => {
    setOpenKeys([]);
  };

  return { openKeys, onOpenChange, closeAllSubmenus };
}

// Mapeamento de rotas para keys do menu
const ROUTE_TO_MENU_KEY: Record<string, string> = {
  '/': 'home',
  '/home': 'home',
  '/aprovacoes': 'aprovacoes',
  '/bloqueios': 'bloqueios',
  // Controle module
  '/controle': 'controle-ops',
  '/controle/acoes': 'controle-acoes',
  '/controle/compras': 'controle-compras',
  '/controle/formacoes': 'controle-formacoes',
  '/controle/plano-formacoes': 'controle-plano-formacoes',
  '/controle/pre-agenda': 'controle-pre-agenda',
  '/dat/etl-reports': 'dat-etl-reports',
  // Item único
  '/deslocamentos': 'deslocamentos',
  // Dashboards
  '/dashboards': 'dashboard-geral',
  '/dashboards/equipe': 'dashboard-equipe',
  '/dashboards/gcal': 'gcal-dashboard',
  '/mapa-brasil': 'mapa-brasil',
  // DAT module
  '/dat/admin': 'dat-admin',
  '/dat/cadastros': 'dat-cadastros',
  '/dat/coordenadores': 'dat-coordenadores',
  '/dat/importacao': 'dat-importacao',
  '/dat/registros': 'dat-registros',
  // Outros
  '/disponibilidade': 'grade-mensal',
  '/solicitacoes/minhas': 'minhas-solicitacoes',
  '/solicitacoes/nova': 'nova-solicitacao',
};

// Mapeamento de menu keys para seus submenus pais
const MENU_KEY_TO_PARENT: Record<string, string> = {
  // Controle submenu
  'controle-ops': 'controle-submenu',
  'controle-acoes': 'controle-submenu',
  'controle-compras': 'controle-submenu',
  'controle-formacoes': 'controle-submenu',
  'controle-plano-formacoes': 'controle-submenu',
  'controle-pre-agenda': 'controle-submenu',
  // Dashboards submenu
  'dashboard-geral': 'dashboards-submenu',
  'dashboard-equipe': 'dashboards-submenu',
  'gcal-dashboard': 'dashboards-submenu',
  'mapa-brasil': 'dashboards-submenu',
  // DAT submenu
  'dat-admin': 'dat-submenu',
  'dat-cadastros': 'dat-submenu',
  'dat-coordenadores': 'dat-submenu',
  'dat-etl-reports': 'dat-submenu',
  'dat-importacao': 'dat-submenu',
  'dat-registros': 'dat-submenu',
  // Solicitações submenu
  'minhas-solicitacoes': 'solicitacoes-submenu',
  'nova-solicitacao': 'solicitacoes-submenu',
};

// Hook para obter a key do menu baseada na rota atual
function useSelectedMenuKey(): string {
  const location = useLocation();
  return useMemo(() => {
    // Tenta match exato primeiro
    if (ROUTE_TO_MENU_KEY[location.pathname]) {
      return ROUTE_TO_MENU_KEY[location.pathname];
    }
    // Tenta match parcial para rotas com parâmetros (ex: /solicitacoes/:id/editar)
    for (const [route, key] of Object.entries(ROUTE_TO_MENU_KEY)) {
      if (location.pathname.startsWith(route) && route !== '/') {
        return key;
      }
    }
    return 'home';
  }, [location.pathname]);
}

// Props do SidebarMenu
interface SidebarMenuProps {
  openKeys: string[];
  onOpenChange: (keys: string[]) => void;
  children: React.ReactNode;
}

// Componente que usa useLocation para seleção dinâmica do menu
function SidebarMenu({ openKeys, onOpenChange, children }: SidebarMenuProps): JSX.Element {
  const selectedKey = useSelectedMenuKey();

  // Auto-abrir submenu pai quando navegar diretamente para uma rota interna
  useEffect(() => {
    const parentKey = MENU_KEY_TO_PARENT[selectedKey];
    if (parentKey && !openKeys.includes(parentKey)) {
      onOpenChange([parentKey]);
    }
  }, [selectedKey]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <Menu
      theme="dark"
      mode="inline"
      selectedKeys={[selectedKey]}
      openKeys={openKeys}
      onOpenChange={onOpenChange}
      style={{ borderRight: 0 }}
    >
      {children}
    </Menu>
  );
}

// Componente de loading para Suspense
function PageLoader(): JSX.Element {
  return (
    <div className="flex justify-center items-center" style={{ height: '100%', minHeight: '300px' }}>
      <Spin size="large" tip="Carregando página..." />
    </div>
  );
}

// Componente 403 Forbidden
function Forbidden(): JSX.Element {
  return <Result status="403" title="Sem permissão" subTitle="Você não tem permissão para acessar esta página." />;
}

// Componente principal que usa o tema
function AppContent(): JSX.Element {
  const { antThemeConfig } = useTheme();
  const colors = useBrandColors();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  // Issue #97: GCal Alerts (badge + toast)
  const [alerts, setAlerts] = useState<AlertsSummary>({ errors: 0, pending: 0, published: 0, none: 0 });
  const [lastErrorsCount, setLastErrorsCount] = useState<number>(0);
  const [cooldownUntil, setCooldownUntil] = useState<number>(0);

  // Issue #255: Ref para evitar memory leak (atualizações após unmount)
  const isMountedRef = useRef<boolean>(true);

  // Controle de submenus (apenas um aberto por vez)
  const { openKeys, onOpenChange, closeAllSubmenus } = useMenuOpenKeys();

  // Carregar dados do usuário - useCallback para poder passar como prop
  const loadUser = useCallback(async () => {
    try {
      const userData = await getMe();
      if (isMountedRef.current) {
        setUser(userData as unknown as CurrentUser);
        // Issue #418: Preload search data after successful login
        preloadSearchData().catch((err) => logger.warn('Search preload failed:', err));
      }
    } catch (error) {
      if (isMountedRef.current) {
        logger.error('Erro ao carregar usuário:', error);
        setUser(null);
      }
    } finally {
      if (isMountedRef.current) {
        setLoading(false);
      }
    }
  }, []);

  // Carregar usuário no mount e cleanup no unmount
  useEffect(() => {
    isMountedRef.current = true;
    loadUser();

    return () => {
      isMountedRef.current = false;
    };
  }, [loadUser]);

  // Issue #97: Polling de alertas GCal (badge + toast)
  // Issue #259: Pausar polling quando aba não está visível (Page Visibility API)
  useEffect(() => {
    // Só ativar polling para Controle (Gerentes de Controle)
    const inControle = user?.setores?.includes('Controle');

    if (!inControle && !user?.is_superuser) {
      return; // Não tem permissão, não fazer polling
    }

    let intervalId: ReturnType<typeof setInterval> | null = null;

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
          setCooldownUntil(now + TIMING.TOAST_COOLDOWN_MS);
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

    // Issue #259: Funções para controlar polling baseado em visibilidade
    const startPolling = () => {
      if (!intervalId) {
        intervalId = setInterval(fetchAlerts, TIMING.ALERT_POLL_INTERVAL_MS);
      }
    };

    const stopPolling = () => {
      if (intervalId) {
        clearInterval(intervalId);
        intervalId = null;
      }
    };

    const handleVisibilityChange = () => {
      if (document.hidden) {
        stopPolling();
      } else {
        // Fetch imediato ao voltar, depois retomar polling
        fetchAlerts();
        startPolling();
      }
    };

    // Carregar lastErrorsCount do localStorage na inicialização
    const stored = localStorage.getItem('gcalAlertsLastErrors');
    if (stored) {
      setLastErrorsCount(parseInt(stored, 10) || 0);
    }

    // Setup: listener de visibilidade
    document.addEventListener('visibilitychange', handleVisibilityChange);

    // Fetch inicial e iniciar polling se aba está visível
    fetchAlerts();
    if (!document.hidden) {
      startPolling();
    }

    // Cleanup: parar polling e remover listener
    return () => {
      stopPolling();
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [user, lastErrorsCount, cooldownUntil]);

  if (loading) {
    return <Spin size="large" tip="Carregando..." fullscreen />;
  }

  // Se não autenticado, mostrar página de login
  if (!user) {
    return (
      <ConfigProvider locale={ptBR} theme={antThemeConfig}>
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
    } catch (error) {
      // Log detalhado do erro
      logger.error('Erro no logout:', error);
      message.warning('Sessão encerrada localmente');
    } finally {
      // Sempre limpar estado local e redirecionar, mesmo se API falhar
      setUser(null);
      // Recarregar a página para voltar para tela de login
      window.location.reload();
    }
  };

  // Calcular flags de permissão (RBAC com Setor + Função)
  // Extrair setores e funções da API
  const setores = user?.setores || [];
  const funcoes = user?.funcoes || [];

  // Permissões baseadas em FUNÇÃO
  const isCoordenador = funcoes.includes('Coordenador') || funcoes.includes('Apoio de Coordenação');

  // Permissões baseadas em SETOR
  const inDAT = setores.includes('DAT');
  const inControle = setores.includes('Controle');
  const inDiretoria = setores.includes('Diretoria');

  // Permissões compostas (Setor + Função)
  // canApproveSuper = pode aprovar solicitações SUPER (Gerente + Superintendência)
  const canApproveSuper = user?.can_approve_super || false;
  // canCoordenador = pode criar solicitações
  const canCoordenador = user?.is_superuser || isCoordenador || inDAT;
  // canControle = acesso a funcionalidades de Controle
  const canControle = user?.is_superuser || inControle;
  // canDAT = acesso a Admin DAT
  const canDAT = user?.is_superuser || inDAT;
  // canDashboards = acesso aos dashboards (Diretoria, DAT, superuser)
  const canDashboards = user?.is_superuser || inDiretoria || inDAT;
  // canDisponibilidade = acesso à grade mensal (todos exceto Controle)
  const canDisponibilidade = user?.is_superuser || !inControle;

  return (
    <ConfigProvider locale={ptBR} theme={antThemeConfig}>
      <Router>
        {/* Issue #416: Offline warning banner */}
        <OfflineBanner />
        <Layout style={{ minHeight: '100vh', background: colors.pageBackground }}>
          {/* Sider lateral fixo */}
          <Sider
            width={LAYOUT.SIDEBAR_WIDTH}
            style={{
              overflow: 'auto',
              height: '100vh',
              position: 'fixed',
              left: 0,
              top: 0,
              bottom: 0,
              background: colors.sidebarBackground,
            }}
          >
            {/* Logo/Título */}
            <div
              className="flex items-center justify-center font-bold"
              style={{
                height: '64px',
                color: 'white',
                fontSize: '22px',
                borderBottom: `1px solid ${colors.borderLight}`,
              }}
            >
              Aprender Sistema
            </div>

            {/* Menu vertical - Ordem alfabética (exceto Página Inicial) */}
            <SidebarMenu
              openKeys={openKeys}
              onOpenChange={onOpenChange}
            >
              {/* 1. Página Inicial (sempre primeiro) */}
              <Menu.Item key="home" icon={<HomeOutlined />} onClick={closeAllSubmenus}>
                <Link to="/home">Página Inicial</Link>
              </Menu.Item>

              {/* 2. Aprovações */}
              {canApproveSuper && (
                <Menu.Item key="aprovacoes" icon={<SafetyOutlined />} onClick={closeAllSubmenus}>
                  <Link to="/aprovacoes">Aprovações</Link>
                </Menu.Item>
              )}

              {/* 3. Bloqueios */}
              {(canControle || canCoordenador || user?.groups?.includes('Formador')) && (
                <Menu.Item key="bloqueios" icon={<CalendarOutlined />} onClick={closeAllSubmenus}>
                  <Link to="/bloqueios">Bloqueios</Link>
                </Menu.Item>
              )}

              {/* 4. Controle */}
              {canControle && (
                <SubMenu key="controle-submenu" icon={<CheckCircleOutlined />} title="Controle">
                  <Menu.Item key="controle-acoes">
                    <Link to="/controle/acoes">Ações</Link>
                  </Menu.Item>
                  <Menu.Item key="controle-compras">
                    <Link to="/controle/compras">Compras</Link>
                  </Menu.Item>
                  <Menu.Item key="controle-formacoes">
                    <Link to="/controle/formacoes">Formações</Link>
                  </Menu.Item>
                  <Menu.Item key="controle-ops">
                    <Link to="/controle">Painel de Controle</Link>
                  </Menu.Item>
                  <Menu.Item key="controle-plano-formacoes">
                    <Link to="/controle/plano-formacoes">Plano Anual</Link>
                  </Menu.Item>
                  <Menu.Item key="controle-pre-agenda">
                    <Link to="/controle/pre-agenda">Pré-agenda</Link>
                  </Menu.Item>
                </SubMenu>
              )}

              {/* 5. Deslocamentos (item único) */}
              {(canControle || canCoordenador || canDAT) && (
                <Menu.Item key="deslocamentos" icon={<CalendarOutlined />} onClick={closeAllSubmenus}>
                  <Link to="/deslocamentos">Deslocamentos</Link>
                </Menu.Item>
              )}

              {/* 5. Dashboards */}
              {canDashboards && (
                <SubMenu key="dashboards-submenu" icon={<BarChartOutlined />} title="Dashboards">
                  <Menu.Item key="dashboard-geral">
                    <Link to="/dashboards">Dashboard Geral</Link>
                  </Menu.Item>
                  <Menu.Item key="dashboard-equipe">
                    <Link to="/dashboards/equipe">Dashboard Equipe</Link>
                  </Menu.Item>
                  <Menu.Item key="gcal-dashboard">
                    <Link to="/dashboards/gcal">
                      <Badge count={alerts.errors} offset={[10, 0]} size="small">
                        Dashboard GCal
                      </Badge>
                    </Link>
                  </Menu.Item>
                  <Menu.Item key="mapa-brasil">
                    <Link to="/mapa-brasil">Mapa do Brasil</Link>
                  </Menu.Item>
                </SubMenu>
              )}

              {/* 6. DAT */}
              {canDAT && (
                <SubMenu key="dat-submenu" icon={<SolutionOutlined />} title="DAT">
                  <Menu.Item key="dat-admin">
                    <Link to="/dat/admin">Administração</Link>
                  </Menu.Item>
                  <Menu.Item key="dat-cadastros">
                    <Link to="/dat/cadastros">Cadastros</Link>
                  </Menu.Item>
                  <Menu.Item key="dat-coordenadores">
                    <Link to="/dat/coordenadores">Coordenadores</Link>
                  </Menu.Item>
                  <Menu.Item key="dat-importacao">
                    <Link to="/dat/importacao">Importação</Link>
                  </Menu.Item>
                  <Menu.Item key="dat-registros">
                    <Link to="/dat/registros">Registros de Turmas</Link>
                  </Menu.Item>
                  <Menu.Item key="dat-etl-reports">
                    <Link to="/dat/etl-reports">Relatórios ETL</Link>
                  </Menu.Item>
                </SubMenu>
              )}

              {/* 7. Grade Mensal (todos exceto Controle) */}
              {canDisponibilidade && (
                <Menu.Item key="grade-mensal" icon={<TableOutlined />} onClick={closeAllSubmenus}>
                  <Link to="/disponibilidade">Grade Mensal</Link>
                </Menu.Item>
              )}

              {/* 8. Solicitações */}
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
            </SidebarMenu>
          </Sider>

          {/* Layout com margem para compensar Sider fixo */}
          <Layout style={{ marginLeft: LAYOUT.SIDEBAR_WIDTH, minHeight: '100vh', background: colors.pageBackground }}>
            {/* Header com info do usuário */}
            <Header
              className="flex items-center justify-end w-full"
              style={{
                background: colors.cardBackground,
                padding: '0 24px',
                borderBottom: `1px solid ${colors.borderDefault}`,
              }}
            >
              <div className="flex items-center gap-4" style={{ whiteSpace: 'nowrap' }}>
                {/* Toggle de tema - ocultado temporariamente
                <Tooltip title={isDark ? 'Modo claro' : 'Modo escuro'}>
                  <Button
                    type="text"
                    icon={isDark ? <SunOutlined /> : <MoonOutlined />}
                    onClick={toggleTheme}
                    style={{ color: isDark ? '#fff' : undefined }}
                  />
                </Tooltip>
                */}
                <div className="flex items-center gap-2">
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
            <Content style={{ padding: '0', minHeight: 'calc(100vh - 64px)', background: colors.pageBackground }}>
              <Suspense fallback={<PageLoader />}>
                <Routes>
                  <Route path="/" element={<HomePage />} />
                  <Route path="/home" element={<HomePage />} />

                  {/* Dashboards (Diretoria, DAT, superuser) */}
                  <Route
                    path="/dashboards"
                    element={canDashboards ? <DashboardsPage /> : <Forbidden />}
                  />

                  {/* Dashboard Equipe (Diretoria, DAT, superuser) */}
                  <Route
                    path="/dashboards/equipe"
                    element={canDashboards ? <EquipeDashboardPage /> : <Forbidden />}
                  />

                  {/* GCal Dashboard (Diretoria, DAT, superuser) */}
                  <Route
                    path="/dashboards/gcal"
                    element={canDashboards ? <GCalDashboardPage /> : <Forbidden />}
                  />

                  {/* Mapa do Brasil (Diretoria, DAT, superuser) */}
                  <Route
                    path="/mapa-brasil"
                    element={canDashboards ? <MapaBrasilPage /> : <Forbidden />}
                  />

                  <Route
                    path="/disponibilidade"
                    element={canDisponibilidade ? <MonthlyPage /> : <Forbidden />}
                  />
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
                  <Route
                    path="/solicitacoes/:id/editar"
                    element={user ? <EditSolicitacaoPage /> : <Forbidden />}
                  />

                  {/* PR15: Rota de aprovações (Gerente + Superintendência) */}
                  <Route
                    path="/aprovacoes"
                    element={canApproveSuper ? <ApprovalsPage /> : <Forbidden />}
                  />

                  {/* ========== CONTROLE MODULE ========== */}
                  <Route path="/controle" element={canControle ? <ControlePage /> : <Forbidden />} />
                  <Route
                    path="/controle/acoes"
                    element={canControle ? <AcoesPage /> : <Forbidden />}
                  />
                  <Route
                    path="/controle/compras"
                    element={canControle ? <ComprasPage /> : <Forbidden />}
                  />
                  {/* Deslocamentos (item único no menu) */}
                  <Route
                    path="/deslocamentos"
                    element={(canControle || canCoordenador || canDAT) ? <DeslocamentosPage /> : <Forbidden />}
                  />
                  <Route
                    path="/controle/formacoes"
                    element={canControle ? <FormacoesPage /> : <Forbidden />}
                  />
                  <Route
                    path="/controle/plano-formacoes"
                    element={canControle ? <PlanoFormacoesPage /> : <Forbidden />}
                  />
                  <Route
                    path="/controle/pre-agenda"
                    element={canControle ? <PreAgendaPage /> : <Forbidden />}
                  />
                  <Route
                    path="/dat/etl-reports"
                    element={canDAT ? <EtlReportsPage /> : <Forbidden />}
                  />

                  {/* ========== DAT MODULE ========== */}
                  <Route
                    path="/dat/admin"
                    element={canDAT ? <AdminDATHomePage /> : <Forbidden />}
                  />
                  <Route
                    path="/dat/admin/usuarios"
                    element={canDAT ? <UsuariosPage /> : <Forbidden />}
                  />
                  <Route
                    path="/dat/admin/municipios"
                    element={canDAT ? <MunicipiosPage /> : <Forbidden />}
                  />
                  <Route
                    path="/dat/admin/projetos"
                    element={canDAT ? <ProjetosPage /> : <Forbidden />}
                  />
                  <Route
                    path="/dat/admin/grupos"
                    element={canDAT ? <GruposPage /> : <Forbidden />}
                  />
                  <Route
                    path="/dat/admin/configuracoes"
                    element={canDAT ? <ConfiguracoesPage /> : <Forbidden />}
                  />
                  <Route
                    path="/dat/cadastros"
                    element={canDAT ? <CadastrosPage /> : <Forbidden />}
                  />
                  <Route
                    path="/dat/coordenadores"
                    element={canDAT ? <CoordenadoresPage /> : <Forbidden />}
                  />
                  <Route
                    path="/dat/importacao"
                    element={canDAT ? <DATPage /> : <Forbidden />}
                  />
                  <Route
                    path="/dat/registros"
                    element={canDAT ? <DATRegistrosPage /> : <Forbidden />}
                  />
                </Routes>
              </Suspense>
            </Content>
          </Layout>
        </Layout>
      </Router>
    </ConfigProvider>
  );
}

// App wrapper com ThemeProvider
function App(): JSX.Element {
  return (
    <ThemeProvider>
      <AppContent />
    </ThemeProvider>
  );
}

export default App;
