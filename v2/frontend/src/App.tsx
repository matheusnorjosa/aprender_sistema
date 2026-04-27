/**
 * App Principal - AS v2 Frontend
 *
 * Composition layer: wires hooks, providers, and layout components.
 * All logic is extracted to dedicated hooks and components.
 *
 * Issue #927: App.tsx decomposition (Frente A — Arquitetura Frontend)
 */

import { useState, useEffect, useRef, useCallback, lazy, Suspense } from 'react';
import { BrowserRouter as Router } from 'react-router-dom';
import { ConfigProvider, Layout, message } from 'antd';
import logger from './utils/logger';
import { isAuthError } from './utils/errors';
import { ThemeProvider, useTheme, useBrandColors } from './contexts/ThemeContext';
import ptBR from 'antd/locale/pt_BR';
import { getMe } from './api/availability';
import { getMyPolicies } from './api/me';
import { logout as apiLogout } from './api/auth';
import { Toaster } from 'react-hot-toast';
import { LAYOUT } from './constants';
import { preloadSearchData } from './services/preloadSearchData';
import OfflineBanner from './components/OfflineBanner';
import { ErrorBoundary } from './components/ErrorBoundary';
import { FullscreenLoader } from './components/FullscreenLoader';
import { AppSidebar } from './components/AppSidebar';
import { AppHeader } from './components/AppHeader';
import { AppRoutes } from './components/AppRoutes';
import { usePermissions } from './hooks/usePermissions';
import { useResponsive } from './hooks/useResponsive';
import { useGCalAlertsPolling } from './hooks/useGCalAlertsPolling';
import { useUnreadNotificationsPolling } from './hooks/useUnreadNotificationsPolling';
import type { CurrentUser } from './types';
import './App.css';

const LoginPage = lazy(() => import('./pages/Auth/LoginPage'));

const { Content } = Layout;

function AppContent(): JSX.Element {
  const { antThemeConfig } = useTheme();
  const colors = useBrandColors();

  // ── User state ──
  const [user, setUser] = useState<CurrentUser | null>(null);
  // Policies do user via GET /api/me/policies/ (Epic 4.4 + Epic 3 #1228).
  // Empty array = "ainda não carregadas" OU "anonymous" — distinção via `loading`.
  const [policies, setPolicies] = useState<readonly string[]>([]);
  const [loading, setLoading] = useState(true);
  const isMountedRef = useRef(true);

  // ── Mobile responsiveness ──
  const { isMobile, sidebarCollapsed, toggleSidebar } = useResponsive();

  // ── Permissions (single source of truth) ──
  const permissions = usePermissions(user);

  // ── Load user ──
  // Fetch de `getMe()` e `getMyPolicies()` em paralelo. Erro em policies não
  // bloqueia login — degrada graciosamente para `[]` (componentes mostram
  // Forbidden em rotas com policy). Erro em getMe → não autenticado.
  const loadUser = useCallback(async () => {
    try {
      const [userData, policiesData] = await Promise.all([
        getMe(),
        getMyPolicies().catch((err) => {
          logger.warn('Erro ao carregar policies (degradando para []):', err);
          return [] as string[];
        }),
      ]);
      if (isMountedRef.current) {
        setUser(userData);
        setPolicies(policiesData);
      }
    } catch (error) {
      if (isMountedRef.current) {
        if (!isAuthError(error)) {
          logger.error('Erro ao carregar usuário:', error);
        }
        setUser(null);
        setPolicies([]);
      }
    } finally {
      if (isMountedRef.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    isMountedRef.current = true;
    loadUser();
    return () => { isMountedRef.current = false; };
  }, [loadUser]);

  // ── Preload search data (once per session, decoupled from user loading) ──
  const preloadedRef = useRef(false);
  useEffect(() => {
    if (user && !preloadedRef.current) {
      preloadedRef.current = true;
      preloadSearchData().catch((err) => logger.warn('Search preload failed:', err));
    }
  }, [user]);

  // ── GCal alerts polling ──
  const gcalEnabled = !!(user?.setores?.includes('Controle') || user?.is_superuser);
  const { alerts } = useGCalAlertsPolling({ enabled: gcalEnabled });

  // ── Notification badge polling ──
  const { unreadNotifications } = useUnreadNotificationsPolling({
    enabled: permissions.canAcoesInternas,
    userId: user?.id,
  });

  // ── Logout ──
  // TODO(tech-debt): replace window.location.reload() with state-driven
  // cleanup once a centralized auth store is in place (#927)
  const handleLogout = useCallback(async () => {
    try {
      await apiLogout();
      message.success('Logout realizado com sucesso');
    } catch (error) {
      logger.error('Erro no logout:', error);
      message.warning('Sessão encerrada localmente');
    } finally {
      setUser(null);
      window.location.reload();
    }
  }, []);

  // ── Render ──
  if (loading) {
    return <FullscreenLoader />;
  }

  if (!user) {
    return (
      <ConfigProvider locale={ptBR} theme={antThemeConfig}>
        <Suspense fallback={<FullscreenLoader />}>
          <LoginPage onLoginSuccess={loadUser} />
        </Suspense>
      </ConfigProvider>
    );
  }

  return (
    <ConfigProvider locale={ptBR} theme={antThemeConfig}>
      <Toaster position="top-right" toastOptions={{ duration: 5000 }} />
      <Router>
        <OfflineBanner />
        <Layout style={{ minHeight: '100vh', background: colors.pageBackground }}>
          <AppSidebar
            permissions={permissions}
            policies={policies}
            gcalErrorCount={alerts.errors}
            unreadNotifications={unreadNotifications}
            isMobile={isMobile}
            sidebarCollapsed={sidebarCollapsed}
            toggleSidebar={toggleSidebar}
            colors={{ sidebarBackground: colors.sidebarBackground, borderLight: colors.borderLight }}
          />
          <Layout style={{
            marginLeft: isMobile ? 0 : (sidebarCollapsed ? LAYOUT.SIDEBAR_COLLAPSED_WIDTH : LAYOUT.SIDEBAR_WIDTH),
            minHeight: '100vh',
            background: colors.pageBackground,
            transition: 'margin-left 0.2s ease',
          }}>
            <AppHeader
              user={user}
              canAcoesInternas={permissions.canAcoesInternas}
              unreadNotifications={unreadNotifications}
              isMobile={isMobile}
              sidebarCollapsed={sidebarCollapsed}
              toggleSidebar={toggleSidebar}
              onLogout={handleLogout}
              colors={{ cardBackground: colors.cardBackground, borderDefault: colors.borderDefault }}
            />
            <Content
              id="main"
              role="main"
              style={{ padding: '0', minHeight: 'calc(100vh - 64px)', background: colors.pageBackground }}
            >
              <AppRoutes user={user} permissions={permissions} policies={policies} />
            </Content>
          </Layout>
        </Layout>
      </Router>
    </ConfigProvider>
  );
}

function App(): JSX.Element {
  return (
    <ThemeProvider>
      <ErrorBoundary>
        <AppContent />
      </ErrorBoundary>
    </ThemeProvider>
  );
}

export default App;
