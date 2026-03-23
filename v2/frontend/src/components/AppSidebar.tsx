import { useState, useEffect, useMemo, useCallback } from 'react';
import { Layout, Menu, Badge } from 'antd';
import { Link, useLocation } from 'react-router-dom';
import {
  CalendarOutlined,
  CheckCircleOutlined,
  FileTextOutlined,
  SafetyOutlined,
  BarChartOutlined,
  HomeOutlined,
  SolutionOutlined,
  BellOutlined,
  TableOutlined,
} from '@ant-design/icons';
import type { Permissions } from '../hooks/usePermissions';
import type { CurrentUser } from '../types';
import { LAYOUT } from '../constants';

const { Sider } = Layout;
const { SubMenu } = Menu;

// ============================================================================
// Route ↔ Menu key mappings (single source of truth)
// ============================================================================

const ROUTE_TO_MENU_KEY: Record<string, string> = {
  '/': 'home',
  '/home': 'home',
  '/aprovacoes': 'aprovacoes',
  '/bloqueios': 'bloqueios',
  '/controle': 'controle-ops',
  '/controle/acoes': 'controle-acoes',
  '/controle/compras': 'controle-compras',
  '/controle/formacoes': 'controle-formacoes',
  '/controle/plano-formacoes': 'controle-plano-formacoes',
  '/controle/pre-agenda': 'controle-pre-agenda',
  '/compras-materiais': 'controle-compras',
  '/pre-agenda': 'controle-pre-agenda',
  '/acoes-notificacao': 'acoes-notificacao-ciclo',
  '/acoes-notificacao/timeline': 'acoes-notificacao-timeline',
  '/notificacoes-internas': 'acoes-notificacao-inbox',
  '/dat/etl-reports': 'dat-etl-reports',
  '/deslocamentos': 'deslocamentos',
  '/dashboards': 'dashboard-geral',
  '/dashboards/compras': 'dashboard-compras',
  '/dashboards/equipe': 'dashboard-equipe',
  '/dashboards/gcal': 'gcal-dashboard',
  '/mapa-brasil': 'mapa-brasil',
  '/dat/admin': 'dat-admin',
  '/dat/admin/colecoes': 'dat-admin-colecoes',
  '/dat/admin/equipe-gerencia': 'dat-admin-equipe-gerencia',
  '/dat/cadastros': 'dat-cadastros',
  '/dat/compras-materiais': 'controle-compras',
  '/dat/coordenadores': 'dat-coordenadores',
  '/dat/importacao': 'dat-importacao',
  '/dat/registros': 'dat-registros',
  '/disponibilidade': 'grade-mensal',
  '/solicitacoes/minhas': 'minhas-solicitacoes',
  '/solicitacoes/nova': 'nova-solicitacao',
};

const MENU_KEY_TO_PARENT: Record<string, string> = {
  'controle-ops': 'controle-submenu',
  'controle-acoes': 'controle-submenu',
  'controle-compras': 'controle-submenu',
  'controle-formacoes': 'controle-submenu',
  'controle-plano-formacoes': 'controle-submenu',
  'controle-pre-agenda': 'controle-submenu',
  'acoes-notificacao-ciclo': 'acoes-notificacao-submenu',
  'acoes-notificacao-timeline': 'acoes-notificacao-submenu',
  'acoes-notificacao-inbox': 'acoes-notificacao-submenu',
  'dashboard-geral': 'dashboards-submenu',
  'dashboard-compras': 'dashboards-submenu',
  'dashboard-equipe': 'dashboards-submenu',
  'gcal-dashboard': 'dashboards-submenu',
  'mapa-brasil': 'dashboards-submenu',
  'dat-admin': 'dat-submenu',
  'dat-admin-colecoes': 'dat-submenu',
  'dat-admin-equipe-gerencia': 'dat-submenu',
  'dat-cadastros': 'dat-submenu',
  'dat-coordenadores': 'dat-submenu',
  'dat-etl-reports': 'dat-submenu',
  'dat-importacao': 'dat-submenu',
  'dat-registros': 'dat-submenu',
  'minhas-solicitacoes': 'solicitacoes-submenu',
  'nova-solicitacao': 'solicitacoes-submenu',
};

// ============================================================================
// Internal hooks (moved from App.tsx)
// ============================================================================

function useSelectedMenuKey(): string {
  const location = useLocation();
  return useMemo(() => {
    if (ROUTE_TO_MENU_KEY[location.pathname]) {
      return ROUTE_TO_MENU_KEY[location.pathname];
    }
    for (const [route, key] of Object.entries(ROUTE_TO_MENU_KEY)) {
      if (location.pathname.startsWith(route) && route !== '/') {
        return key;
      }
    }
    return 'home';
  }, [location.pathname]);
}

function useMenuOpenKeys() {
  const [openKeys, setOpenKeys] = useState<string[]>([]);

  const onOpenChange = useCallback((keys: string[]) => {
    const latestOpenKey = keys.find((key) => openKeys.indexOf(key) === -1);
    setOpenKeys(latestOpenKey ? [latestOpenKey] : []);
  }, [openKeys]);

  const closeAllSubmenus = useCallback(() => {
    setOpenKeys([]);
  }, []);

  return { openKeys, onOpenChange, closeAllSubmenus };
}

// ============================================================================
// SidebarMenu (internal component that uses useLocation)
// ============================================================================

interface SidebarMenuProps {
  openKeys: string[];
  onOpenChange: (keys: string[]) => void;
  onItemClick?: () => void;
  children: React.ReactNode;
}

function SidebarMenu({ openKeys, onOpenChange, onItemClick, children }: SidebarMenuProps): JSX.Element {
  const selectedKey = useSelectedMenuKey();

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
      onClick={onItemClick}
      style={{ borderRight: 0 }}
    >
      {children}
    </Menu>
  );
}

// ============================================================================
// AppSidebar (exported component)
// ============================================================================

interface AppSidebarProps {
  user: CurrentUser;
  permissions: Permissions;
  gcalErrorCount: number;
  unreadNotifications: number;
  isMobile: boolean;
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
  colors: {
    sidebarBackground: string;
    borderLight: string;
  };
}

export function AppSidebar({
  user,
  permissions,
  gcalErrorCount,
  unreadNotifications,
  isMobile,
  sidebarCollapsed,
  toggleSidebar,
  colors,
}: AppSidebarProps): JSX.Element {
  const { openKeys, onOpenChange, closeAllSubmenus } = useMenuOpenKeys();

  const {
    canApproveSuper, canCoordenador, canControle, canDAT, canAcoesInternas,
    canDashboardOverview, canDashboardEquipe, canDashboardGcal, canDashboardCompras,
    canMapaBrasil, canDashboardsMenu, canDisponibilidade,
  } = permissions;

  return (
    <>
      {/* Overlay para fechar sidebar em mobile */}
      {isMobile && !sidebarCollapsed && (
        <div
          className="mobile-sidebar-overlay"
          onClick={toggleSidebar}
          aria-hidden="true"
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0, 0, 0, 0.45)',
            zIndex: 999,
          }}
        />
      )}
      <Sider
        width={LAYOUT.SIDEBAR_WIDTH}
        collapsedWidth={isMobile ? 0 : LAYOUT.SIDEBAR_COLLAPSED_WIDTH}
        collapsed={sidebarCollapsed}
        collapsible
        trigger={null}
        role="navigation"
        aria-label="Navegacao principal"
        className={isMobile && !sidebarCollapsed ? 'mobile-sidebar-open' : ''}
        style={{
          overflow: 'auto',
          height: '100vh',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
          background: colors.sidebarBackground,
          zIndex: isMobile ? 1000 : 1,
          transition: 'all 0.2s ease',
        }}
      >
        <header
          role="banner"
          className="flex items-center justify-center font-bold"
          style={{
            height: '64px',
            color: 'white',
            fontSize: '22px',
            borderBottom: `1px solid ${colors.borderLight}`,
          }}
        >
          Aprender Sistema
        </header>

        {!(isMobile && sidebarCollapsed) && (
          <SidebarMenu
            openKeys={openKeys}
            onOpenChange={onOpenChange}
            onItemClick={() => {
              if (isMobile) {
                toggleSidebar();
                closeAllSubmenus();
              }
            }}
          >
            <Menu.Item key="home" icon={<HomeOutlined />} onClick={closeAllSubmenus}>
              <Link to="/home">Página Inicial</Link>
            </Menu.Item>

            {canApproveSuper && (
              <Menu.Item key="aprovacoes" icon={<SafetyOutlined />} onClick={closeAllSubmenus}>
                <Link to="/aprovacoes">Aprovações</Link>
              </Menu.Item>
            )}

            {(canControle || canCoordenador || user.groups?.includes('Formador')) && (
              <Menu.Item key="bloqueios" icon={<CalendarOutlined />} onClick={closeAllSubmenus}>
                <Link to="/bloqueios">Bloqueios</Link>
              </Menu.Item>
            )}

            {canControle && (
              <SubMenu key="controle-submenu" icon={<CheckCircleOutlined />} title="Controle">
                <Menu.Item key="controle-acoes"><Link to="/controle/acoes">Ações</Link></Menu.Item>
                <Menu.Item key="controle-compras"><Link to="/controle/compras">Compras</Link></Menu.Item>
                <Menu.Item key="controle-formacoes"><Link to="/controle/formacoes">Formações</Link></Menu.Item>
                <Menu.Item key="controle-ops"><Link to="/controle">Painel de Controle</Link></Menu.Item>
                <Menu.Item key="controle-plano-formacoes"><Link to="/controle/plano-formacoes">Plano Anual</Link></Menu.Item>
                <Menu.Item key="controle-pre-agenda"><Link to="/controle/pre-agenda">Pré-agenda</Link></Menu.Item>
              </SubMenu>
            )}

            {canAcoesInternas && (
              <SubMenu
                key="acoes-notificacao-submenu"
                icon={<Badge count={unreadNotifications} size="small" offset={[6, 0]}><BellOutlined /></Badge>}
                title="Ações Internas"
              >
                <Menu.Item key="acoes-notificacao-ciclo"><Link to="/acoes-notificacao">Ciclos e Ações</Link></Menu.Item>
                <Menu.Item key="acoes-notificacao-timeline"><Link to="/acoes-notificacao/timeline">Timeline</Link></Menu.Item>
                <Menu.Item key="acoes-notificacao-inbox"><Link to="/notificacoes-internas">Notificações</Link></Menu.Item>
              </SubMenu>
            )}

            {(canControle || canCoordenador || canDAT) && (
              <Menu.Item key="deslocamentos" icon={<CalendarOutlined />} onClick={closeAllSubmenus}>
                <Link to="/deslocamentos">Deslocamentos</Link>
              </Menu.Item>
            )}

            {canDashboardsMenu && (
              <SubMenu key="dashboards-submenu" icon={<BarChartOutlined />} title="Dashboards">
                {canDashboardOverview && (
                  <Menu.Item key="dashboard-geral"><Link to="/dashboards">Dashboard Geral</Link></Menu.Item>
                )}
                {canDashboardCompras && (
                  <Menu.Item key="dashboard-compras"><Link to="/dashboards/compras">Dashboard Compras</Link></Menu.Item>
                )}
                {canDashboardEquipe && (
                  <Menu.Item key="dashboard-equipe"><Link to="/dashboards/equipe">Dashboard Equipe</Link></Menu.Item>
                )}
                {canDashboardGcal && (
                  <Menu.Item key="gcal-dashboard">
                    <Link to="/dashboards/gcal">
                      <Badge count={gcalErrorCount} offset={[10, 0]} size="small">Dashboard GCal</Badge>
                    </Link>
                  </Menu.Item>
                )}
                {canMapaBrasil && (
                  <Menu.Item key="mapa-brasil"><Link to="/mapa-brasil">Mapa do Brasil</Link></Menu.Item>
                )}
              </SubMenu>
            )}

            {canDAT && (
              <SubMenu key="dat-submenu" icon={<SolutionOutlined />} title="DAT">
                <Menu.Item key="dat-admin"><Link to="/dat/admin">Administração</Link></Menu.Item>
                <Menu.Item key="dat-admin-colecoes"><Link to="/dat/admin/colecoes">Importar Coleções</Link></Menu.Item>
                <Menu.Item key="dat-admin-equipe-gerencia"><Link to="/dat/admin/equipe-gerencia">Importar Vínculos</Link></Menu.Item>
                <Menu.Item key="dat-cadastros"><Link to="/dat/cadastros">Cadastros</Link></Menu.Item>
                <Menu.Item key="dat-coordenadores"><Link to="/dat/coordenadores">Coordenadores</Link></Menu.Item>
                <Menu.Item key="dat-importacao"><Link to="/dat/importacao">Importação</Link></Menu.Item>
                <Menu.Item key="dat-registros"><Link to="/dat/registros">Registros de Turmas</Link></Menu.Item>
                <Menu.Item key="dat-etl-reports"><Link to="/dat/etl-reports">Relatórios ETL</Link></Menu.Item>
              </SubMenu>
            )}

            {canDisponibilidade && (
              <Menu.Item key="grade-mensal" icon={<TableOutlined />} onClick={closeAllSubmenus}>
                <Link to="/disponibilidade">Grade Mensal</Link>
              </Menu.Item>
            )}

            {canCoordenador && (
              <SubMenu key="solicitacoes-submenu" icon={<FileTextOutlined />} title="Solicitações">
                <Menu.Item key="minhas-solicitacoes"><Link to="/solicitacoes/minhas">Minhas Solicitações</Link></Menu.Item>
                <Menu.Item key="nova-solicitacao"><Link to="/solicitacoes/nova">Nova Solicitação</Link></Menu.Item>
              </SubMenu>
            )}
          </SidebarMenu>
        )}
      </Sider>
    </>
  );
}
