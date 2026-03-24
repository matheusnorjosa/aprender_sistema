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
import { ConfigProvider, Layout, Spin, message } from 'antd';
import logger from './utils/logger';
import { isAuthError } from './utils/errors';
import { deduplicatedFetch } from './utils/request';
import { ThemeProvider, useTheme, useBrandColors } from './contexts/ThemeContext';
import ptBR from 'antd/locale/pt_BR';
import { getMe } from './api/availability';
import { logout as apiLogout } from './api/auth';
import { getAlertsSummary } from './api/gcal';
import { getNotificacoesNaoLidasCount } from './api/acoesNotificacao';
import toast, { Toaster } from 'react-hot-toast';
import { LAYOUT, TIMING } from './constants';
import { preloadSearchData } from './services/preloadSearchData';
import OfflineBanner from './components/OfflineBanner';
import { ErrorBoundary } from './components/ErrorBoundary';
import { AppSidebar } from './components/AppSidebar';
import { AppHeader } from './components/AppHeader';
import { AppRoutes } from './components/AppRoutes';
import { usePermissions } from './hooks/usePermissions';
import { usePolling } from './hooks/usePolling';
import type { CurrentUser } from './types';
import './App.css';

const LoginPage = lazy(() => import('./pages/Auth/LoginPage'));

const { Content } = Layout;

interface AlertsSummary {
  errors: number;
  pending: number;
  published: number;
  none: number;
}

// Stable events array (defined outside component to avoid re-renders)
const NOTIF_EVENTS = ['notificacoes:refresh'];

function AppContent(): JSX.Element {
  const { antThemeConfig } = useTheme();
  const colors = useBrandColors();

  // ── User state ──
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);
  const isMountedRef = useRef(true);

  // ── GCal alerts state ──
  const [alerts, setAlerts] = useState<AlertsSummary>({ errors: 0, pending: 0, published: 0, none: 0 });
  const [lastErrorsCount, setLastErrorsCount] = useState(0);
  const [cooldownUntil, setCooldownUntil] = useState(0);

  // ── Notification badge state ──
  const [unreadNotifications, setUnreadNotifications] = useState(0);
  const [lastNotifCount, setLastNotifCount] = useState(-1);
  const [notifCooldownUntil, setNotifCooldownUntil] = useState(0);

  // ── Mobile responsiveness ──
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => window.innerWidth < LAYOUT.MOBILE_BREAKPOINT);
  const [isMobile, setIsMobile] = useState(() => window.innerWidth < LAYOUT.MOBILE_BREAKPOINT);

  useEffect(() => {
    const handleResize = () => {
      const mobile = window.innerWidth < LAYOUT.MOBILE_BREAKPOINT;
      setIsMobile(mobile);
      setSidebarCollapsed(mobile);
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const toggleSidebar = useCallback(() => {
    setSidebarCollapsed(prev => !prev);
  }, []);

  // ── Permissions (single source of truth) ──
  const permissions = usePermissions(user);

  // ── Load user ──
  const loadUser = useCallback(async () => {
    try {
      const userData = await getMe();
      if (isMountedRef.current) {
        setUser(userData);
        preloadSearchData().catch((err) => logger.warn('Search preload failed:', err));
      }
    } catch (error) {
      if (isMountedRef.current) {
        const log = isAuthError(error) ? logger.warn : logger.error;
        log('Erro ao carregar usuário:', error);
        setUser(null);
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

  // ── GCal alerts polling (usePolling) ──
  const gcalEnabled = !!(user?.setores?.includes('Controle') || user?.is_superuser);

  // Use refs to avoid stale closures in polling callback
  const lastErrorsRef = useRef(lastErrorsCount);
  lastErrorsRef.current = lastErrorsCount;
  const cooldownRef = useRef(cooldownUntil);
  cooldownRef.current = cooldownUntil;

  const fetchGCalAlerts = useCallback(async () => {
    try {
      const data = await deduplicatedFetch('gcal-alerts', getAlertsSummary);
      setAlerts(data);

      const now = Date.now();
      if (data.errors > lastErrorsRef.current && now > cooldownRef.current) {
        toast.error(
          `Novos erros de publicação detectados (${lastErrorsRef.current} → ${data.errors})`,
          { duration: 5000 },
        );
        setCooldownUntil(now + TIMING.TOAST_COOLDOWN_MS);
      }

      if (data.errors !== lastErrorsRef.current) {
        setLastErrorsCount(data.errors);
        localStorage.setItem('gcalAlertsLastErrors', data.errors.toString());
      }
    } catch (error) {
      if (isAuthError(error)) return;
      logger.error('[Alerts] Erro ao buscar alertas:', error);
    }
  }, []);

  // Load lastErrorsCount from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem('gcalAlertsLastErrors');
    if (stored) setLastErrorsCount(parseInt(stored, 10) || 0);
  }, []);

  usePolling(fetchGCalAlerts, {
    enabled: gcalEnabled,
    intervalMs: TIMING.ALERT_POLL_INTERVAL_MS,
  });

  // ── Notification badge polling (usePolling) ──
  const notifEnabled = permissions.canAcoesInternas;

  const lastNotifRef = useRef(lastNotifCount);
  lastNotifRef.current = lastNotifCount;
  const notifCooldownRef = useRef(notifCooldownUntil);
  notifCooldownRef.current = notifCooldownUntil;

  const fetchUnreadNotifications = useCallback(async () => {
    try {
      const data = await deduplicatedFetch('unread-count', getNotificacoesNaoLidasCount);
      if (!isMountedRef.current) return;
      setUnreadNotifications(data.count);

      const now = Date.now();
      if (data.count > lastNotifRef.current && lastNotifRef.current >= 0 && now > notifCooldownRef.current) {
        const diff = data.count - lastNotifRef.current;
        toast(`${diff} nova${diff > 1 ? 's' : ''} notificação${diff > 1 ? 'ões' : ''}`, {
          icon: '🔔',
          duration: 5000,
          id: 'new-notifications',
        });
        setNotifCooldownUntil(now + TIMING.TOAST_COOLDOWN_MS);
      }

      if (data.count !== lastNotifRef.current) {
        setLastNotifCount(data.count);
        if (user?.id) localStorage.setItem(`notifLastUnread:${user.id}`, data.count.toString());
      }
    } catch (error) {
      if (isAuthError(error)) return;
      logger.error('[Notifications] Polling error:', error);
    }
  }, [user?.id]);

  // Sync lastNotifCount with localStorage when user changes
  useEffect(() => {
    if (!user?.id) return;
    setUnreadNotifications(0);
    setNotifCooldownUntil(0);
    const stored = localStorage.getItem(`notifLastUnread:${user.id}`);
    const parsed = stored ? parseInt(stored, 10) : NaN;
    setLastNotifCount(Number.isNaN(parsed) ? -1 : parsed);
  }, [user?.id]);

  usePolling(fetchUnreadNotifications, {
    enabled: notifEnabled,
    intervalMs: TIMING.ALERT_POLL_INTERVAL_MS,
    events: NOTIF_EVENTS,
  });

  // ── Logout ──
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
    return <Spin size="large" tip="Carregando..." fullscreen />;
  }

  if (!user) {
    return (
      <ConfigProvider locale={ptBR} theme={antThemeConfig}>
        <Suspense fallback={<Spin size="large" tip="Carregando..." fullscreen />}>
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
              <AppRoutes user={user} permissions={permissions} />
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
