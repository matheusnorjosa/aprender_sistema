import { lazy, Suspense } from 'react';
import { Routes, Route, Navigate, Link } from 'react-router-dom';
import { Spin, Result, Button } from 'antd';
import type { Permissions } from '../hooks/usePermissions';
import { useCanAccess } from '../hooks/useCanAccess';
import type { CurrentUser } from '../types';

// Lazy-loaded pages (code-splitting)
const DisponibilidadeBlocks = lazy(() => import('../pages/Disponibilidade'));
const MonthlyPage = lazy(() => import('../pages/Disponibilidade/MonthlyPage'));
const ControlePage = lazy(() => import('../pages/Controle/ControlePage'));
// DATPage (página antiga de /dat/importacao, Cadastros DAT) deixou de ser
// usada após PR-C DAT Imports (2026-04-29) — rota agora redireciona para
// /dat/importacoes. O componente continua existindo para o card "Cadastros
// DAT" dentro de ImportacoesPage; remoção definitiva fica em PR-D.
const DATImportacoesPage = lazy(() => import('../pages/DAT/ImportacoesPage'));
const NewSolicitacaoWizard = lazy(() => import('../pages/Solicitacoes/NewSolicitacaoWizard'));
const EditSolicitacaoPage = lazy(() => import('../pages/Solicitacoes/EditSolicitacaoPage'));
const MySolicitacoesPage = lazy(() => import('../pages/Solicitacoes/MySolicitacoesPage'));
const MeusEventosPage = lazy(() => import('../pages/MeusEventos/MeusEventosPage'));
const ApprovalsPage = lazy(() => import('../pages/Aprovacoes/ApprovalsPage'));
const PreAgendaPage = lazy(() => import('../pages/PreAgenda/PreAgendaPage'));
const HomePage = lazy(() => import('../pages/Home/HomePage'));
const DashboardsPage = lazy(() => import('../pages/Dashboards/DashboardsPage'));
const EquipeDashboardPage = lazy(() => import('../pages/Dashboards/EquipeDashboardPage'));
const GCalDashboardPage = lazy(() => import('../pages/Dashboards/GCalDashboardPage'));
const ComprasDashboardPage = lazy(() => import('../pages/Dashboards/ComprasDashboardPage'));
const MapaBrasilPage = lazy(() => import('../pages/MapaBrasil/MapaBrasilPage'));
const AdminDATHomePage = lazy(() => import('../pages/AdminDAT/AdminDATHomePage'));
const UsuariosPage = lazy(() => import('../pages/AdminDAT/UsuariosPage'));
const MunicipiosPage = lazy(() => import('../pages/AdminDAT/MunicipiosPage'));
const ProjetosPage = lazy(() => import('../pages/AdminDAT/ProjetosPage'));
const GruposPage = lazy(() => import('../pages/AdminDAT/GruposPage'));
const SetoresPage = lazy(() => import('../pages/AdminDAT/SetoresPage'));
const FuncoesPage = lazy(() => import('../pages/AdminDAT/FuncoesPage'));
const ConfiguracoesPage = lazy(() => import('../pages/AdminDAT/ConfiguracoesPage'));
const ColecoesImportPage = lazy(() => import('../pages/AdminDAT/ColecoesImportPage'));
const EquipeGerenciaImportPage = lazy(() => import('../pages/AdminDAT/EquipeGerenciaImportPage'));
const DeslocamentosPage = lazy(() => import('../pages/Deslocamentos/DeslocamentosPage'));
const DATRegistrosPage = lazy(() => import('../pages/DATModule/DATRegistrosPage'));
const AcoesPage = lazy(() => import('../pages/DATModule/AcoesPage'));
const DATComprasPage = lazy(() => import('../pages/DATModule/ComprasPage'));
const CadastrosPage = lazy(() => import('../pages/DATModule/CadastrosPage'));
const FormacoesPage = lazy(() => import('../pages/DATModule/FormacoesPage'));
const PlanoFormacoesPage = lazy(() => import('../pages/DATModule/PlanoFormacoesPage'));
const CoordenadoresPage = lazy(() => import('../pages/DATModule/CoordenadoresPage'));
const AcoesNotificacaoPage = lazy(() => import('../pages/Controle/AcoesNotificacaoPage'));
const NotificacoesInternasPage = lazy(() => import('../pages/Controle/NotificacoesInternasPage'));
const AcoesTimelinePage = lazy(() => import('../pages/Controle/AcoesTimelinePage'));
const GerenciasPage = lazy(() => import('../pages/AdminDAT/GerenciasPage'));
const ProdutosPage = lazy(() => import('../pages/AdminDAT/ProdutosPage'));

function PageLoader(): JSX.Element {
  return (
    <div className="flex justify-center items-center" style={{ height: '100%', minHeight: '300px' }}>
      <Spin size="large" tip="Carregando página..." />
    </div>
  );
}

/**
 * Forbidden inline (mantido para rotas que ainda não usam <RequirePolicy>).
 * Mesma mensagem genérica do `RequirePolicy` (OWASP — não revelar
 * existência do recurso ou permission necessária).
 */
function Forbidden(): JSX.Element {
  return (
    <Result
      status="info"
      title="Recurso indisponível"
      subTitle="Esta página não está disponível ou não pode ser acessada pela sua conta."
      extra={
        <Link to="/">
          <Button type="primary">Voltar ao início</Button>
        </Link>
      }
    />
  );
}

interface AppRoutesProps {
  user: CurrentUser;
  permissions: Permissions;
  policies: readonly string[];
}

export function AppRoutes({ user, permissions, policies }: AppRoutesProps): JSX.Element {
  const {
    canCoordenador, canControle, canDAT, canAcoesInternas,
    canDashboardOverview, canDashboardEquipe, canDashboardGcal, canDashboardCompras,
    canMapaBrasil, canDisponibilidade, isFormador,
  } = permissions;

  // Camada de tradução semântica (Epic 3): derived flags a partir de policies + legacy.
  // Componentes consomem `access.canAccessApprovals` direto.
  // PR 10 hardening RBAC (2026-04-30): aprovações dependem exclusivamente
  // da policy `access_solicitation_approvals`; legacy `canApproveSuper`
  // saiu do contrato deste hook.
  const access = useCanAccess(policies, {
    canBloqueios: canControle || canCoordenador || isFormador,
    canCoordenador,
    canDashboardCompras,
  });

  return (
    <Suspense fallback={<PageLoader />}>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/home" element={<HomePage />} />

        {/* Dashboards */}
        <Route path="/dashboards" element={canDashboardOverview ? <DashboardsPage /> : <Forbidden />} />
        <Route path="/dashboards/compras" element={access.canViewComprasDashboard ? <ComprasDashboardPage /> : <Forbidden />} />
        <Route path="/dashboards/equipe" element={canDashboardEquipe ? <EquipeDashboardPage /> : <Forbidden />} />
        <Route path="/dashboards/gcal" element={canDashboardGcal ? <GCalDashboardPage /> : <Forbidden />} />
        <Route path="/mapa-brasil" element={canMapaBrasil ? <MapaBrasilPage /> : <Forbidden />} />

        {/* === Solicitações (agrupamento — Epic 3, Issue #1227) === */}
        {/* Páginas pré-existentes mantidas */}
        <Route path="/solicitacoes/minhas" element={access.canCreateSolicitation ? <MySolicitacoesPage /> : <Forbidden />} />
        <Route path="/solicitacoes/nova" element={access.canCreateSolicitation ? <NewSolicitacaoWizard /> : <Forbidden />} />
        <Route path="/solicitacoes/:id/editar" element={user ? <EditSolicitacaoPage /> : <Forbidden />} />

        {/* Páginas movidas para sob /solicitacoes/* (com redirects abaixo) */}
        <Route path="/solicitacoes/aprovacoes" element={access.canAccessApprovals ? <ApprovalsPage /> : <Forbidden />} />
        <Route path="/solicitacoes/disponibilidade" element={access.can('view_all_availability') || canDisponibilidade ? <MonthlyPage /> : <Forbidden />} />
        <Route path="/solicitacoes/bloqueios" element={access.canAccessBlocks ? <DisponibilidadeBlocks /> : <Forbidden />} />
        <Route path="/solicitacoes/deslocamentos" element={access.can('view_all_availability') || canControle || canCoordenador || canDAT ? <DeslocamentosPage /> : <Forbidden />} />
        <Route path="/solicitacoes/meus-eventos" element={user ? <MeusEventosPage /> : <Forbidden />} />

        {/* Redirects de URLs legadas → novas (preserva deep-links/bookmarks) */}
        <Route path="/aprovacoes" element={<Navigate to="/solicitacoes/aprovacoes" replace />} />
        <Route path="/disponibilidade" element={<Navigate to="/solicitacoes/disponibilidade" replace />} />
        <Route path="/bloqueios" element={<Navigate to="/solicitacoes/bloqueios" replace />} />
        <Route path="/deslocamentos" element={<Navigate to="/solicitacoes/deslocamentos" replace />} />
        <Route path="/meus-eventos" element={<Navigate to="/solicitacoes/meus-eventos" replace />} />

        {/* Controle Module */}
        <Route path="/controle" element={canControle ? <ControlePage /> : <Forbidden />} />
        <Route path="/controle/acoes" element={canControle ? <AcoesPage /> : <Forbidden />} />
        <Route path="/controle/compras" element={(canControle || canDAT) ? <DATComprasPage /> : <Forbidden />} />
        <Route path="/controle/coordenadores" element={canControle ? <CoordenadoresPage /> : <Forbidden />} />
        <Route path="/compras-materiais" element={(canControle || canDAT) ? <DATComprasPage /> : <Forbidden />} />
        {/* /deslocamentos movido para /solicitacoes/deslocamentos (Epic 3, Issue #1227 — redirect já registrado acima) */}
        <Route path="/controle/formacoes" element={canControle ? <FormacoesPage /> : <Forbidden />} />
        <Route path="/controle/plano-formacoes" element={canControle ? <PlanoFormacoesPage /> : <Forbidden />} />
        <Route path="/controle/pre-agenda" element={canControle ? <PreAgendaPage /> : <Forbidden />} />
        <Route path="/pre-agenda" element={canControle ? <PreAgendaPage /> : <Forbidden />} />

        {/* Ações/Notificações */}
        <Route path="/acoes-notificacao" element={canAcoesInternas ? <AcoesNotificacaoPage /> : <Forbidden />} />
        <Route path="/acoes-notificacao/timeline" element={canAcoesInternas ? <AcoesTimelinePage /> : <Forbidden />} />
        <Route path="/notificacoes-internas" element={canAcoesInternas ? <NotificacoesInternasPage /> : <Forbidden />} />
        {/* DAT Module */}
        <Route path="/dat/admin" element={canDAT ? <AdminDATHomePage /> : <Forbidden />} />
        <Route path="/dat/admin/usuarios" element={canDAT ? <UsuariosPage /> : <Forbidden />} />
        <Route path="/dat/admin/municipios" element={canDAT ? <MunicipiosPage /> : <Forbidden />} />
        <Route path="/dat/admin/projetos" element={canDAT ? <ProjetosPage /> : <Forbidden />} />
        <Route path="/dat/admin/grupos" element={canDAT ? <GruposPage /> : <Forbidden />} />
        <Route path="/dat/admin/setores" element={canDAT ? <SetoresPage /> : <Forbidden />} />
        <Route path="/dat/admin/funcoes" element={canDAT ? <FuncoesPage /> : <Forbidden />} />
        <Route path="/dat/admin/gerencias" element={canDAT ? <GerenciasPage /> : <Forbidden />} />
        <Route path="/dat/admin/produtos" element={canDAT ? <ProdutosPage /> : <Forbidden />} />
        <Route path="/dat/admin/configuracoes" element={canDAT ? <ConfiguracoesPage /> : <Forbidden />} />
        <Route path="/dat/admin/colecoes" element={canDAT ? <ColecoesImportPage /> : <Forbidden />} />
        <Route path="/dat/admin/equipe-gerencia" element={canDAT ? <EquipeGerenciaImportPage /> : <Forbidden />} />
        <Route path="/dat/cadastros" element={canDAT ? <CadastrosPage /> : <Forbidden />} />
        <Route path="/dat/compras-materiais" element={(canControle || canDAT) ? <DATComprasPage /> : <Forbidden />} />
        <Route path="/dat/coordenadores" element={canControle ? <CoordenadoresPage /> : <Forbidden />} />
        {/* PR-C DAT Imports (2026-04-29): /dat/importacao (singular, página antiga
            de Cadastros DAT) redireciona para /dat/importacoes (plural, página
            unificada de imports). Evita 404 em links antigos. */}
        <Route path="/dat/importacao" element={<Navigate to="/dat/importacoes" replace />} />
        <Route path="/dat/importacoes" element={canDAT ? <DATImportacoesPage /> : <Forbidden />} />
        <Route path="/dat/registros" element={canDAT ? <DATRegistrosPage /> : <Forbidden />} />
      </Routes>
    </Suspense>
  );
}
