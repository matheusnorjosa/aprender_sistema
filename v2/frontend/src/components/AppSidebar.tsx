import { useState, useEffect, useMemo, useCallback, useRef, type JSX } from 'react';
import { Layout, Menu, Badge, Button, type MenuProps } from 'antd';
import { Link, useLocation } from 'react-router';
import {
  CalendarOutlined,
  CarOutlined,
  CheckCircleOutlined,
  CloseOutlined,
  FileTextOutlined,
  SafetyOutlined,
  BarChartOutlined,
  HomeOutlined,
  SolutionOutlined,
  StopOutlined,
  BellOutlined,
  TableOutlined,
} from '@ant-design/icons';
import type { Permissions } from '../hooks/usePermissions';
import { useCapabilities } from '../hooks/useCapabilities';
import { LAYOUT } from '../constants';
import { ID_NAVEGACAO_PRINCIPAL, sidebarSobrepondo, type ModoSidebar } from '../hooks/useResponsive';

const { Sider } = Layout;
const { SubMenu } = Menu;

// ============================================================================
// Route ↔ Menu key mappings (single source of truth)
// ============================================================================

const ROUTE_TO_MENU_KEY: Record<string, string> = {
  '/': 'home',
  '/home': 'home',
  // Solicitações (Epic 3, Issue #1227 — agrupamento sob /solicitacoes/*)
  '/solicitacoes/aprovacoes': 'aprovacoes',
  '/solicitacoes/bloqueios': 'bloqueios',
  '/solicitacoes/deslocamentos': 'deslocamentos',
  '/solicitacoes/disponibilidade': 'grade-mensal',
  '/solicitacoes/meus-eventos': 'meus-eventos',
  '/solicitacoes/minhas': 'minhas-solicitacoes',
  '/solicitacoes/nova': 'nova-solicitacao',
  '/solicitacoes/publicacao': 'publicacao-setor',
  // Backward-compat: rotas legadas redirecionam, mas o menu key segue válido para deep-links cacheados
  '/aprovacoes': 'aprovacoes',
  '/bloqueios': 'bloqueios',
  '/deslocamentos': 'deslocamentos',
  '/disponibilidade': 'grade-mensal',
  '/meus-eventos': 'meus-eventos',
  '/controle': 'controle-ops',
  '/controle/acoes': 'controle-acoes',
  '/controle/compras': 'controle-compras',
  '/controle/coordenadores': 'controle-coordenadores',
  '/controle/plano-formacoes': 'controle-plano-formacoes',
  '/controle/pre-agenda': 'controle-pre-agenda',
  '/compras-materiais': 'controle-compras',
  '/pre-agenda': 'controle-pre-agenda',
  '/acoes-notificacao': 'acoes-notificacao-ciclo',
  '/acoes-notificacao/timeline': 'acoes-notificacao-timeline',
  '/notificacoes-internas': 'acoes-notificacao-inbox',
  '/dashboards': 'dashboard-geral',
  '/dashboards/compras': 'dashboard-compras',
  '/dashboards/equipe': 'dashboard-equipe',
  '/dashboards/gcal': 'gcal-dashboard',
  '/mapa-brasil': 'mapa-brasil',
  '/dat/admin': 'dat-admin',
  '/dat/admin/equipe-gerencia': 'dat-importacoes',
  '/dat/admin/gerencias': 'dat-admin',
  '/dat/admin/produtos': 'dat-admin',
  '/dat/cadastros': 'dat-cadastros',
  '/dat/compras-materiais': 'controle-compras',
  '/dat/coordenadores': 'controle-coordenadores',
  '/dat/importacao': 'dat-importacoes',
  '/dat/importacoes': 'dat-importacoes',
  '/dat/registros': 'dat-registros',
};

const MENU_KEY_TO_PARENT: Record<string, string> = {
  'controle-ops': 'controle-submenu',
  'controle-acoes': 'controle-submenu',
  'controle-compras': 'controle-submenu',
  'controle-coordenadores': 'controle-submenu',
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
  'dat-cadastros': 'dat-submenu',
  'dat-importacoes': 'dat-submenu',
  'dat-registros': 'dat-submenu',
  'minhas-solicitacoes': 'solicitacoes-submenu',
  'nova-solicitacao': 'solicitacoes-submenu',
  'publicacao-setor': 'solicitacoes-submenu',
};

// ============================================================================
// Internal hooks (moved from App.tsx)
// ============================================================================

function useSelectedMenuKey(): string {
  const location = useLocation();
  return useMemo(() => {
    const exact = ROUTE_TO_MENU_KEY[location.pathname];
    if (exact) {
      return exact;
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
  /** Só ícones: os submenus abrem como flyout, sem abrir o do item atual sozinho. */
  recolhido: boolean;
  openKeys: string[];
  onOpenChange: (keys: string[]) => void;
  onItemClick?: MenuProps['onClick'];
  children: React.ReactNode;
}

function SidebarMenu({ recolhido, openKeys, onOpenChange, onItemClick, children }: SidebarMenuProps): JSX.Element {
  const selectedKey = useSelectedMenuKey();

  // Abre o submenu pai da página atual também ao expandir (sair de recolhido): recolher fecha todos.
  useEffect(() => {
    const parentKey = MENU_KEY_TO_PARENT[selectedKey];
    if (parentKey && !recolhido && !openKeys.includes(parentKey)) {
      onOpenChange([parentKey]);
    }
  }, [selectedKey, recolhido]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <Menu
      theme="dark"
      mode="inline"
      selectedKeys={[selectedKey]}
      openKeys={openKeys}
      onOpenChange={onOpenChange}
      {...(onItemClick !== undefined && { onClick: onItemClick })}
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
  permissions: Permissions;
  policies: readonly string[];
  gcalErrorCount: number;
  unreadNotifications: number;
  modo: ModoSidebar;
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
  colors: {
    sidebarBackground: string;
    borderLight: string;
  };
}

export function AppSidebar({
  permissions,
  policies,
  gcalErrorCount,
  unreadNotifications,
  modo,
  sidebarCollapsed,
  toggleSidebar,
  colors,
}: AppSidebarProps): JSX.Element {
  const { openKeys, onOpenChange, closeAllSubmenus } = useMenuOpenKeys();
  // Abaixo de 1280 px a sidebar aberta fica POR CIMA do conteúdo (fundo escuro fecha).
  const sobrepondo = sidebarSobrepondo(modo, sidebarCollapsed);
  const navRef = useRef<HTMLDivElement>(null);
  const { pathname } = useLocation();
  const rotaRef = useRef(pathname);

  // Por cima do conteúdo, a sidebar é um diálogo: o foco vai para o 1º item e Esc fecha.
  // O ☰ recebe o foco de volta (AppHeader); cabeçalho e conteúdo ficam inertes (App).
  useEffect(() => {
    if (sobrepondo) navRef.current?.querySelector<HTMLElement>('.ant-menu a[href]')?.focus();
  }, [sobrepondo]);

  useEffect(() => {
    if (!sobrepondo) return undefined;
    const fecharComEsc = (evento: KeyboardEvent): void => {
      if (evento.key === 'Escape') toggleSidebar();
    };
    document.addEventListener('keydown', fecharComEsc);
    return () => document.removeEventListener('keydown', fecharComEsc);
  }, [sobrepondo, toggleSidebar]);

  // Rota mudou por fora do menu (voltar do navegador, link no conteúdo): fecha. Pelo menu,
  // o clique no item já fechou (onItemClick) e aqui `sobrepondo` chega false.
  useEffect(() => {
    if (rotaRef.current === pathname) return;
    rotaRef.current = pathname;
    if (sobrepondo) toggleSidebar();
  }, [pathname]); // eslint-disable-line react-hooks/exhaustive-deps

  // #1270 (RBAC 3.2): os itens de menu derivam de `useCapabilities` (policy pura,
  // fonte de verdade do backend). As flags legacy de organograma permanecem SÓ onde
  // não há policy pública equivalente: escopo próprio de Formador/Coordenador em
  // Bloqueios/Deslocamentos e o acesso scoped da Grade Mensal (`canDisponibilidade`).
  // Todas são flags can*/is* (não `in*`).
  const {
    canCoordenador, canControle, canDAT, isFormador, canDisponibilidade, isGestorPorVinculo,
  } = permissions;

  const caps = useCapabilities(policies);

  return (
    <>
      {/* Fundo escuro que fecha a sidebar aberta por cima do conteúdo */}
      {sobrepondo && (
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
        ref={navRef}
        id={ID_NAVEGACAO_PRINCIPAL}
        // Sobreposta fechada: escondida (largura 0), fora do Tab e do leitor de tela.
        inert={modo === 'sobreposta' && sidebarCollapsed}
        width={LAYOUT.SIDEBAR_WIDTH}
        collapsedWidth={modo === 'sobreposta' ? 0 : LAYOUT.SIDEBAR_COLLAPSED_WIDTH}
        collapsed={sidebarCollapsed}
        collapsible
        trigger={null}
        role="navigation"
        aria-label="Navegacao principal"
        className={sobrepondo ? 'mobile-sidebar-open' : ''}
        style={{
          overflow: 'auto',
          height: '100vh',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
          background: colors.sidebarBackground,
          zIndex: sobrepondo ? 1000 : 1,
          transition: 'all 0.2s ease',
        }}
      >
        <header
          role="banner"
          className={`flex items-center font-bold ${sobrepondo ? 'justify-between' : 'justify-center'}`}
          style={{
            height: '64px',
            color: 'white',
            fontSize: '22px',
            borderBottom: `1px solid ${colors.borderLight}`,
            ...(sobrepondo && { paddingInline: 12 }),
          }}
        >
          {sidebarCollapsed && modo === 'recolhida' ? (
            <>
              <span aria-hidden="true">AS</span>
              <span className="sr-only">Aprender Sistema</span>
            </>
          ) : (
            'Aprender Sistema'
          )}
          {/* Por cima do conteúdo o ☰ fica inerte e o fundo, aria-hidden: sem Esc (leitor de
              tela no toque), é este botão que fecha. O foco volta ao ☰ (AppHeader). */}
          {sobrepondo && (
            <Button
              type="text"
              className="sidebar-fechar-menu"
              icon={<CloseOutlined />}
              aria-label="Fechar menu"
              onClick={toggleSidebar}
              style={{ color: 'white' }}
            />
          )}
        </header>

        {!(modo === 'sobreposta' && sidebarCollapsed) && (
          <SidebarMenu
            recolhido={sidebarCollapsed}
            openKeys={openKeys}
            onOpenChange={onOpenChange}
            onItemClick={(info) => {
              // Enter: o rc-menu chama o onClick já no keydown. Fechar ali levaria o foco ao ☰
              // antes da ação padrão do <a> (o link não navegaria e o keypress reabriria o
              // menu). O Enter segue para o <a>, e o clique que ele gera fecha por aqui.
              if (info.domEvent.type === 'keydown') return;
              if (sobrepondo) {
                toggleSidebar();
                closeAllSubmenus();
              }
            }}
          >
            <Menu.Item key="home" icon={<HomeOutlined />} onClick={closeAllSubmenus}>
              <Link to="/home">Página Inicial</Link>
            </Menu.Item>

            {/* Meus Eventos — qualquer user autenticado (Issue #1225, Epic 2 / Epic 3 #1227 — sob /solicitacoes/*) */}
            <Menu.Item key="meus-eventos" icon={<CalendarOutlined />} onClick={closeAllSubmenus}>
              <Link to="/solicitacoes/meus-eventos">Meus Eventos</Link>
            </Menu.Item>

            {caps.canAccessApprovals && (
              <Menu.Item key="aprovacoes" icon={<SafetyOutlined />} onClick={closeAllSubmenus}>
                <Link to="/solicitacoes/aprovacoes">Aprovações</Link>
              </Menu.Item>
            )}

            {/* Bloqueios: policy view_all_availability + escopo próprio de Formador/Coordenador
                (sem policy pública) e Controle (access_controle_section). */}
            {(caps.canViewAllAvailability || canControle || canCoordenador || isFormador || isGestorPorVinculo) && (
              <Menu.Item key="bloqueios" icon={<StopOutlined />} onClick={closeAllSubmenus}>
                <Link to="/solicitacoes/bloqueios">Bloqueios</Link>
              </Menu.Item>
            )}

            {caps.canAccessControleSection && (
              <SubMenu key="controle-submenu" icon={<CheckCircleOutlined />} title="Controle">
                <Menu.Item key="controle-acoes"><Link to="/controle/acoes">Ações</Link></Menu.Item>
                <Menu.Item key="controle-compras"><Link to="/controle/compras">Compras</Link></Menu.Item>
                <Menu.Item key="controle-coordenadores"><Link to="/controle/coordenadores">Coordenadores</Link></Menu.Item>
                <Menu.Item key="controle-ops"><Link to="/controle">Painel de Controle</Link></Menu.Item>
                <Menu.Item key="controle-plano-formacoes"><Link to="/controle/plano-formacoes">Plano Anual</Link></Menu.Item>
                <Menu.Item key="controle-pre-agenda"><Link to="/controle/pre-agenda">Pré-agenda</Link></Menu.Item>
              </SubMenu>
            )}

            {caps.canManageInternalActions && (
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

            {(caps.canViewAllAvailability || canControle || canCoordenador || canDAT || isGestorPorVinculo) && (
              <Menu.Item key="deslocamentos" icon={<CarOutlined />} onClick={closeAllSubmenus}>
                <Link to="/solicitacoes/deslocamentos">Deslocamentos</Link>
              </Menu.Item>
            )}

            {(caps.canViewOverviewDashboard ||
              caps.canViewComprasDashboard ||
              caps.canViewTeamDashboard ||
              caps.canViewGcalDashboard ||
              caps.canViewMapMetrics) && (
              <SubMenu key="dashboards-submenu" icon={<BarChartOutlined />} title="Dashboards">
                {caps.canViewOverviewDashboard && (
                  <Menu.Item key="dashboard-geral"><Link to="/dashboards">Dashboard Geral</Link></Menu.Item>
                )}
                {caps.canViewComprasDashboard && (
                  <Menu.Item key="dashboard-compras"><Link to="/dashboards/compras">Dashboard Compras</Link></Menu.Item>
                )}
                {caps.canViewTeamDashboard && (
                  <Menu.Item key="dashboard-equipe"><Link to="/dashboards/equipe">Dashboard Equipe</Link></Menu.Item>
                )}
                {caps.canViewGcalDashboard && (
                  <Menu.Item key="gcal-dashboard">
                    <Link to="/dashboards/gcal">
                      <Badge count={gcalErrorCount} offset={[10, 0]} size="small">Dashboard GCal</Badge>
                    </Link>
                  </Menu.Item>
                )}
                {caps.canViewMapMetrics && (
                  <Menu.Item key="mapa-brasil"><Link to="/mapa-brasil">Mapa do Brasil</Link></Menu.Item>
                )}
              </SubMenu>
            )}

            {caps.canManageAdminRegistries && (
              <SubMenu key="dat-submenu" icon={<SolutionOutlined />} title="DAT">
                <Menu.Item key="dat-admin"><Link to="/dat/admin">Administração</Link></Menu.Item>
                <Menu.Item key="dat-cadastros"><Link to="/dat/cadastros">Cadastros</Link></Menu.Item>
                {/* Importação pela tela: só superusuário (decisão do dono, 02/10/2026). */}
                {permissions.isAdmin && (
                  <Menu.Item key="dat-importacoes"><Link to="/dat/importacoes">Importações</Link></Menu.Item>
                )}
                <Menu.Item key="dat-registros"><Link to="/dat/registros">Registros de Turmas</Link></Menu.Item>
              </SubMenu>
            )}

            {/* Grade Mensal: policy view_all_availability (Controle/DAT global) + acesso
                scoped de Coordenador/Apoio/Gerente via canDisponibilidade (sem policy pública). */}
            {(caps.canViewAllAvailability || canDisponibilidade) && (
              <Menu.Item key="grade-mensal" icon={<TableOutlined />} onClick={closeAllSubmenus}>
                <Link to="/solicitacoes/disponibilidade">Grade Mensal</Link>
              </Menu.Item>
            )}

            {/* #1656: cada item pelo próprio gate; "Publicar na agenda" é da Apoio de
                Coordenação (publish_setor_solicitacao), não de quem cria solicitação. */}
            {(caps.canCreateSolicitation || caps.canPublishSetorSolicitacao) && (
              <SubMenu key="solicitacoes-submenu" icon={<FileTextOutlined />} title="Solicitações">
                {caps.canCreateSolicitation && (
                  <Menu.Item key="minhas-solicitacoes"><Link to="/solicitacoes/minhas">Minhas Solicitações</Link></Menu.Item>
                )}
                {caps.canCreateSolicitation && (
                  <Menu.Item key="nova-solicitacao"><Link to="/solicitacoes/nova">Nova Solicitação</Link></Menu.Item>
                )}
                {caps.canPublishSetorSolicitacao && (
                  <Menu.Item key="publicacao-setor"><Link to="/solicitacoes/publicacao">Publicar na agenda</Link></Menu.Item>
                )}
              </SubMenu>
            )}
          </SidebarMenu>
        )}
      </Sider>
    </>
  );
}
