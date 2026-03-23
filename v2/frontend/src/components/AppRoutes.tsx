import { lazy, Suspense } from 'react';
import { Routes, Route, } from 'react-router-dom';
import { Spin, Result } from 'antd';
import type { Permissions } from '../hooks/usePermissions';
import type { CurrentUser } from '../types';

// Lazy-loaded pages (code-splitting)
const DisponibilidadeBlocks = lazy(() => import('../pages/Disponibilidade'));
const MonthlyPage = lazy(() => import('../pages/Disponibilidade/MonthlyPage'));
const ControlePage = lazy(() => import('../pages/Controle/ControlePage'));
const EtlReportsPage = lazy(() => import('../pages/Controle/EtlReportsPage'));
const DATPage = lazy(() => import('../pages/DAT/DATPage'));
const NewSolicitacaoWizard = lazy(() => import('../pages/Solicitacoes/NewSolicitacaoWizard'));
const EditSolicitacaoPage = lazy(() => import('../pages/Solicitacoes/EditSolicitacaoPage'));
const MySolicitacoesPage = lazy(() => import('../pages/Solicitacoes/MySolicitacoesPage'));
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

function PageLoader(): JSX.Element {
  return (
    <div className="flex justify-center items-center" style={{ height: '100%', minHeight: '300px' }}>
      <Spin size="large" tip="Carregando página..." />
    </div>
  );
}

function Forbidden(): JSX.Element {
  return <Result status="403" title="Sem permissão" subTitle="Você não tem permissão para acessar esta página." />;
}

interface AppRoutesProps {
  user: CurrentUser;
  permissions: Permissions;
}

export function AppRoutes({ user, permissions }: AppRoutesProps): JSX.Element {
  const {
    canApproveSuper, canCoordenador, canControle, canDAT, canAcoesInternas,
    canDashboardOverview, canDashboardEquipe, canDashboardGcal, canDashboardCompras,
    canMapaBrasil, canDisponibilidade,
  } = permissions;

  return (
    <Suspense fallback={<PageLoader />}>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/home" element={<HomePage />} />

        {/* Dashboards */}
        <Route path="/dashboards" element={canDashboardOverview ? <DashboardsPage /> : <Forbidden />} />
        <Route path="/dashboards/compras" element={canDashboardCompras ? <ComprasDashboardPage /> : <Forbidden />} />
        <Route path="/dashboards/equipe" element={canDashboardEquipe ? <EquipeDashboardPage /> : <Forbidden />} />
        <Route path="/dashboards/gcal" element={canDashboardGcal ? <GCalDashboardPage /> : <Forbidden />} />
        <Route path="/mapa-brasil" element={canMapaBrasil ? <MapaBrasilPage /> : <Forbidden />} />

        {/* Disponibilidade */}
        <Route path="/disponibilidade" element={canDisponibilidade ? <MonthlyPage /> : <Forbidden />} />
        <Route path="/bloqueios" element={<DisponibilidadeBlocks />} />

        {/* Solicitações */}
        <Route path="/solicitacoes/minhas" element={canCoordenador ? <MySolicitacoesPage /> : <Forbidden />} />
        <Route path="/solicitacoes/nova" element={canCoordenador ? <NewSolicitacaoWizard /> : <Forbidden />} />
        <Route path="/solicitacoes/:id/editar" element={user ? <EditSolicitacaoPage /> : <Forbidden />} />

        {/* Aprovações */}
        <Route path="/aprovacoes" element={canApproveSuper ? <ApprovalsPage /> : <Forbidden />} />

        {/* Controle Module */}
        <Route path="/controle" element={canControle ? <ControlePage /> : <Forbidden />} />
        <Route path="/controle/acoes" element={canControle ? <AcoesPage /> : <Forbidden />} />
        <Route path="/controle/compras" element={(canControle || canDAT) ? <DATComprasPage /> : <Forbidden />} />
        <Route path="/compras-materiais" element={(canControle || canDAT) ? <DATComprasPage /> : <Forbidden />} />
        <Route path="/deslocamentos" element={(canControle || canCoordenador || canDAT) ? <DeslocamentosPage /> : <Forbidden />} />
        <Route path="/controle/formacoes" element={canControle ? <FormacoesPage /> : <Forbidden />} />
        <Route path="/controle/plano-formacoes" element={canControle ? <PlanoFormacoesPage /> : <Forbidden />} />
        <Route path="/controle/pre-agenda" element={canControle ? <PreAgendaPage /> : <Forbidden />} />
        <Route path="/pre-agenda" element={canControle ? <PreAgendaPage /> : <Forbidden />} />

        {/* Ações/Notificações */}
        <Route path="/acoes-notificacao" element={canAcoesInternas ? <AcoesNotificacaoPage /> : <Forbidden />} />
        <Route path="/acoes-notificacao/timeline" element={canAcoesInternas ? <AcoesTimelinePage /> : <Forbidden />} />
        <Route path="/notificacoes-internas" element={canAcoesInternas ? <NotificacoesInternasPage /> : <Forbidden />} />
        <Route path="/dat/etl-reports" element={canDAT ? <EtlReportsPage /> : <Forbidden />} />

        {/* DAT Module */}
        <Route path="/dat/admin" element={canDAT ? <AdminDATHomePage /> : <Forbidden />} />
        <Route path="/dat/admin/usuarios" element={canDAT ? <UsuariosPage /> : <Forbidden />} />
        <Route path="/dat/admin/municipios" element={canDAT ? <MunicipiosPage /> : <Forbidden />} />
        <Route path="/dat/admin/projetos" element={canDAT ? <ProjetosPage /> : <Forbidden />} />
        <Route path="/dat/admin/grupos" element={canDAT ? <GruposPage /> : <Forbidden />} />
        <Route path="/dat/admin/configuracoes" element={canDAT ? <ConfiguracoesPage /> : <Forbidden />} />
        <Route path="/dat/admin/colecoes" element={canDAT ? <ColecoesImportPage /> : <Forbidden />} />
        <Route path="/dat/admin/equipe-gerencia" element={canDAT ? <EquipeGerenciaImportPage /> : <Forbidden />} />
        <Route path="/dat/cadastros" element={canDAT ? <CadastrosPage /> : <Forbidden />} />
        <Route path="/dat/compras-materiais" element={(canControle || canDAT) ? <DATComprasPage /> : <Forbidden />} />
        <Route path="/dat/coordenadores" element={canDAT ? <CoordenadoresPage /> : <Forbidden />} />
        <Route path="/dat/importacao" element={canDAT ? <DATPage /> : <Forbidden />} />
        <Route path="/dat/registros" element={canDAT ? <DATRegistrosPage /> : <Forbidden />} />
      </Routes>
    </Suspense>
  );
}
