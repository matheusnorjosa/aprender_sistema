/**
 * App Principal - AS v2 Frontend
 *
 * Composition layer: wires hooks, providers, and layout components.
 * All logic is extracted to dedicated hooks and components.
 *
 * Issue #927: App.tsx decomposition (Frente A — Arquitetura Frontend)
 */

import { useState, useEffect, useRef, useCallback, lazy, Suspense, type JSX } from 'react';
import { BrowserRouter as Router } from 'react-router';
import { ConfigProvider, Layout, message, Result, Button } from 'antd';
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
import { clearApiCaches } from './services/swCache';
import OfflineBanner from './components/OfflineBanner';
import { ErrorBoundary } from './components/ErrorBoundary';
import { FullscreenLoader } from './components/FullscreenLoader';
import { AppSidebar } from './components/AppSidebar';
import { AppHeader } from './components/AppHeader';
import { AppRoutes } from './components/AppRoutes';
import { usePermissions } from './hooks/usePermissions';
import { useCanAccess } from './hooks/useCanAccess';
import { useResponsive } from './hooks/useResponsive';
import { useGCalAlertsPolling } from './hooks/useGCalAlertsPolling';
import { useUnreadNotificationsPolling } from './hooks/useUnreadNotificationsPolling';
import useSessionMonitor from './hooks/useSessionMonitor';
import SessionExpiryWarning from './components/SessionExpiryWarning';
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
  // #1741 (F2): erro transitório (5xx/rede) no boot → tela de erro com retry,
  // NÃO logout. Distingue "falhou ao carregar" de "sessão ausente".
  const [bootError, setBootError] = useState(false);
  const isMountedRef = useRef(true);

  // ── Mobile responsiveness ──
  const { isMobile, sidebarCollapsed, toggleSidebar } = useResponsive();

  // ── Permissions (single source of truth) ──
  const permissions = usePermissions(user);
  // Issue #1263: Ações Internas é policy-driven (manage_internal_actions), não mais
  // a flag legacy por grupo. Policy-only, então basta `policies` (sem legacy flags).
  const access = useCanAccess(policies);

  // ── Load user ──
  // `getMe()` primeiro (estabelece sessão); `getMyPolicies()` depois APENAS se
  // autenticado. Sequencial é trade-off consciente — paralelo gerava 403 no
  // console pre-login (DRF IsAuthenticated → 403) que poluía console-errors
  // E2E checks. Latência adicional ~100-300ms apenas no primeiro mount.
  const loadUser = useCallback(async () => {
    setLoading(true);
    setBootError(false);
    try {
      const userData = await getMe();
      if (!isMountedRef.current) return;
      setUser(userData);

      // Só busca policies se user autenticado (evita 403 espúrio pre-login).
      try {
        const policiesData = await getMyPolicies();
        if (isMountedRef.current) setPolicies(policiesData);
      } catch (err) {
        if (!isAuthError(err)) {
          logger.warn('Erro ao carregar policies (degradando para []):', err);
        }
        if (isMountedRef.current) setPolicies([]);
      }
    } catch (error) {
      if (isMountedRef.current) {
        if (isAuthError(error)) {
          // Genuinamente sem sessão (401/403) → login.
          setUser(null);
          setPolicies([]);
        } else {
          // #1741 (F2): erro transitório (5xx/rede) NÃO desloga uma sessão
          // possivelmente válida — mostra tela de erro com retry em vez do login.
          logger.error('Erro ao carregar usuário:', error);
          setBootError(true);
        }
      }
    } finally {
      if (isMountedRef.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    isMountedRef.current = true;
    void loadUser();
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
  // Epic 3.3 cleanup: usa flag derivada do usePermissions (canControle já cobre superuser).
  const { alerts } = useGCalAlertsPolling({ enabled: permissions.canControle });

  // ── Notification badge polling ──
  const { unreadNotifications } = useUnreadNotificationsPolling({
    enabled: access.canManageInternalActions,
    userId: user?.id,
  });

  // ── Monitor proativo de sessão (Issue #164, religado em #1376) ──
  // Aviso de expiração iminente + renovação via /api/auth/ping/. Até então era
  // dead code (nunca montado). A UI (SessionExpiryWarning) é renderizada dentro
  // do <Router> no fluxo autenticado (usa useNavigate).
  const sessionMonitor = useSessionMonitor();

  // ── Tratamento global de sessão expirada no 401 (Issue #1376) ──
  // `fetchAPI` dispara `auth:expired` em qualquer 401. Se havia usuário logado,
  // limpamos o estado de sessão → App re-renderiza a LoginPage (redirect global
  // para o login, sem cada tela tratar o 401). O guard `userRef.current` evita
  // loop no load inicial e em rotas públicas: um 401 sem sessão prévia é ignorado.
  const userRef = useRef<CurrentUser | null>(null);
  useEffect(() => {
    userRef.current = user;
  }, [user]);

  useEffect(() => {
    const handleAuthExpired = (): void => {
      if (!userRef.current || !isMountedRef.current) return;
      message.warning('Sua sessão expirou. Faça login novamente.');
      setUser(null);
      setPolicies([]);
    };
    window.addEventListener('auth:expired', handleAuthExpired);
    return () => window.removeEventListener('auth:expired', handleAuthExpired);
  }, []);

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
      // Remove os caches de identidade do SW antes do reload (Issue #1461):
      // impede servir /api/me/* de um usuário anterior offline. Roda mesmo se o
      // POST de logout falhar (está no finally) e nunca lança (no-op seguro).
      await clearApiCaches();
      setUser(null);
      window.location.reload();
    }
  }, []);

  // ── Render ──
  if (loading) {
    return <FullscreenLoader />;
  }

  // #1741 (F2): boot falhou por erro transitório (5xx/rede) — NÃO deslogar; oferecer
  // retry. Só 401/403 caem no fluxo de login abaixo (via `setUser(null)`).
  if (bootError) {
    return (
      <ConfigProvider locale={ptBR} theme={antThemeConfig}>
        <Result
          status="warning"
          title="Não foi possível carregar sua sessão"
          subTitle="Ocorreu um erro temporário e sua sessão pode continuar válida. Tente novamente."
          extra={
            <Button type="primary" onClick={() => void loadUser()}>
              Tentar novamente
            </Button>
          }
        />
      </ConfigProvider>
    );
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
        <SessionExpiryWarning
          showWarning={sessionMonitor.showWarning}
          timeLeft={sessionMonitor.timeLeft}
          renewSession={sessionMonitor.renewSession}
        />
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
              canManageInternalActions={access.canManageInternalActions}
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
