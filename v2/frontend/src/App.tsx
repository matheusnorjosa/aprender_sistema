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
import { getErrorStatus, isAuthError } from './utils/errors';
import { ThemeProvider, useTheme, useBrandColors } from './contexts/ThemeContext';
import ptBR from 'antd/locale/pt_BR';
import { getMe } from './api/availability';
import { getMyPolicies } from './api/me';
import { logout as apiLogout } from './api/auth';
import { Toaster } from 'react-hot-toast';
import { LAYOUT } from './constants';
import { preloadSearchData } from './services/preloadSearchData';
import { clearApiCaches } from './services/swCache';
import { apagarAvisoDoLogin, avisarSaidaAsOutrasAbas, guardarAvisoDoLogin, storageKeys } from './utils/storage';
import OfflineBanner from './components/OfflineBanner';
import { ErrorBoundary } from './components/ErrorBoundary';
import { FullscreenLoader } from './components/FullscreenLoader';
import { AppSidebar } from './components/AppSidebar';
import { AppHeader } from './components/AppHeader';
import { AppRoutes } from './components/AppRoutes';
import { usePermissions } from './hooks/usePermissions';
import { useCanAccess } from './hooks/useCanAccess';
import { useResponsive, sidebarSobrepondo } from './hooks/useResponsive';
import { useGCalAlertsPolling } from './hooks/useGCalAlertsPolling';
import { useUnreadNotificationsPolling } from './hooks/useUnreadNotificationsPolling';
import useSessionMonitor from './hooks/useSessionMonitor';
import SessionExpiryWarning from './components/SessionExpiryWarning';
import type { CurrentUser } from './types';
import './App.css';

const LoginPage = lazy(() => import('./pages/Auth/LoginPage'));

const { Content } = Layout;

const AVISO_INATIVIDADE = 'Sua sessão expirou por inatividade. Entre de novo.';
const AVISO_SESSAO_EXPIRADA = 'Sua sessão expirou. Entre de novo.';
const AVISO_SAIU_EM_OUTRA_ABA = 'Você saiu do sistema em outra aba. Entre de novo.';

/**
 * Monitor e aviso de sessão: só existem com usuário logado (na tela de login não há sessão
 * para vigiar, e o monitor ali chegava a fazer POST de logout — auditoria UX 30/09).
 */
function MonitorDeSessao({ onExpirada, onSair }: {
  onExpirada: () => Promise<void>;
  onSair: () => Promise<void>;
}): JSX.Element {
  const monitor = useSessionMonitor(onExpirada);
  return (
    <SessionExpiryWarning
      showWarning={monitor.showWarning}
      timeLeft={monitor.timeLeft}
      renewSession={monitor.renewSession}
      renewError={monitor.renewError}
      onLogout={onSair}
    />
  );
}

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
  const { modo, sidebarCollapsed, toggleSidebar } = useResponsive();
  // Sobreposta: o conteúdo ocupa a largura toda. Recolhida: a sidebar aberta fica POR CIMA
  // do conteúdo (margem de 80 px sempre). Aberta: a sidebar empurra o conteúdo.
  const margemDoConteudo = modo === 'sobreposta'
    ? 0
    : modo === 'aberta' && !sidebarCollapsed ? LAYOUT.SIDEBAR_WIDTH : LAYOUT.SIDEBAR_COLLAPSED_WIDTH;
  // Sidebar aberta por cima: cabeçalho e conteúdo atrás do fundo saem do Tab e do leitor de tela.
  const conteudoInerte = sidebarSobrepondo(modo, sidebarCollapsed);

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
      // Sessão viva: um motivo guardado para o login (ex.: expiração dada por engano) não vale mais.
      apagarAvisoDoLogin();

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

  // ── Logout ──
  // TODO(tech-debt): replace window.location.reload() with state-driven
  // cleanup once a centralized auth store is in place (#927)
  // Só para a ação explícita: "Sair" do cabeçalho e "Sair agora" do aviso. '/login' e
  // '/logout' não são rotas — o login aparece quando não há sessão.
  const handleLogout = useCallback(async () => {
    try {
      await apiLogout();
      message.success('Logout realizado com sucesso');
    } catch (error) {
      // A sessão já acabou no servidor (401, ou 403 com code NOT_AUTHENTICATED, como no
      // fetchAPI): segue para o login. Outro 403 (ex.: CSRF Failed) é com a sessão viva.
      const status = getErrorStatus(error);
      const codigo = (error as { response?: { data?: { code?: string } } }).response?.data?.code;
      if (!(status === 401 || (status === 403 && codigo === 'NOT_AUTHENTICATED'))) {
        // Sem rede, 5xx ou 403 de CSRF, a sessão continua aberta no servidor: recarregar
        // mostraria uma tela quebrada (o JSON offline do service worker) ou a mesma conta
        // logada, sem aviso. Fica na tela e pede para tentar de novo (auditoria UX 30/09,
        // rodadas 3 e 4).
        logger.error('Erro no logout:', error);
        message.error(error instanceof TypeError
          ? 'Não foi possível sair: sem conexão. Tente de novo.'
          : 'Não foi possível sair: erro no servidor. Tente de novo.');
        return;
      }
    }
    // As outras abas vão ao login na hora: sem isto, contavam das respostas deste logout e
    // seguiam com cara de logadas por mais 2 h (auditoria UX 30/09, rodada 6).
    avisarSaidaAsOutrasAbas();
    // Remove os caches de identidade do SW antes do reload (Issue #1461):
    // impede servir /api/me/* de um usuário anterior offline. Nunca lança (no-op seguro).
    await clearApiCaches();
    setUser(null);
    window.location.reload();
  }, []);

  // ── Sessão encerrada pelo servidor (expirou, ou caiu em outra aba) ──
  // SEM POST de logout: não há sessão para encerrar, e o POST de uma aba ociosa derrubava
  // a sessão das outras (o cookie é do navegador). Limpa os caches de identidade do SW,
  // guarda o motivo para o login e recarrega (o reload zera o estado em memória, como no
  // logout) — auditoria UX 30/09, rodada 2.
  const encerradaRef = useRef(false);
  const handleSessaoEncerrada = useCallback(async (aviso: string): Promise<void> => {
    if (encerradaRef.current) return;
    encerradaRef.current = true;
    guardarAvisoDoLogin(aviso);
    await clearApiCaches();
    window.location.reload();
  }, []);
  const handleInatividade = useCallback(
    () => handleSessaoEncerrada(AVISO_INATIVIDADE),
    [handleSessaoEncerrada],
  );

  // ── Tratamento global de sessão expirada (Issue #1376) ──
  // `fetchAPI` dispara `auth:expired` em 401 e no 403 do DRF sem sessão (code
  // NOT_AUTHENTICATED; SessionAuthentication não manda WWW-Authenticate, então o DRF
  // responde 403). Antes de tirar alguém do sistema, pergunta ao servidor (GET /api/me/):
  // sem sessão → login com o motivo; sessão viva → fica (a tela já mostrou o erro dela).
  // O guard `userRef.current` evita loop no load inicial e na tela de login.
  // O "Sair" em outra aba apaga o horário comum às abas (handleLogout): o evento 'storage', que
  // o navegador entrega só às outras abas, faz a mesma pergunta, com o motivo certo (rodada 6).
  const userRef = useRef<CurrentUser | null>(null);
  useEffect(() => {
    userRef.current = user;
  }, [user]);

  const conferindoRef = useRef(false);
  useEffect(() => {
    const conferirSessao = async (aviso: string): Promise<void> => {
      if (!userRef.current || !isMountedRef.current || conferindoRef.current) return;
      conferindoRef.current = true;
      try {
        await getMe();
      } catch (err) {
        if (isAuthError(err)) await handleSessaoEncerrada(aviso);
      } finally {
        conferindoRef.current = false;
      }
    };
    const ouvinte = (): void => {
      void conferirSessao(AVISO_SESSAO_EXPIRADA);
    };
    const saiuEmOutraAba = (e: StorageEvent): void => {
      if (e.key === storageKeys.sessaoUltimaResposta && e.newValue === null) {
        void conferirSessao(AVISO_SAIU_EM_OUTRA_ABA);
      }
    };
    window.addEventListener('auth:expired', ouvinte);
    window.addEventListener('storage', saiuEmOutraAba);
    return () => {
      window.removeEventListener('auth:expired', ouvinte);
      window.removeEventListener('storage', saiuEmOutraAba);
    };
  }, [handleSessaoEncerrada]);

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
        <MonitorDeSessao onExpirada={handleInatividade} onSair={handleLogout} />
        <Layout style={{ minHeight: '100vh', background: colors.pageBackground }}>
          <AppSidebar
            permissions={permissions}
            policies={policies}
            gcalErrorCount={alerts.errors}
            unreadNotifications={unreadNotifications}
            modo={modo}
            sidebarCollapsed={sidebarCollapsed}
            toggleSidebar={toggleSidebar}
            colors={{ sidebarBackground: colors.sidebarBackground, borderLight: colors.borderLight }}
          />
          <Layout inert={conteudoInerte} style={{
            marginLeft: margemDoConteudo,
            minHeight: '100vh',
            background: colors.pageBackground,
            transition: 'margin-left 0.2s ease',
          }}>
            <AppHeader
              user={user}
              canManageInternalActions={access.canManageInternalActions}
              unreadNotifications={unreadNotifications}
              modo={modo}
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
