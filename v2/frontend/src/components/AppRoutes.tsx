import { lazy, Suspense, type JSX } from 'react';
import { Routes, Route, Navigate } from 'react-router';
import { Spin } from 'antd';
import type { Permissions } from '../hooks/usePermissions';
import { useCanAccess } from '../hooks/useCanAccess';
import { RequirePolicy } from './access/RequirePolicy';
import type { CurrentUser } from '../types';

// Lazy-loaded pages (code-splitting)
const DisponibilidadeBlocks = lazy(() => import('../pages/Disponibilidade'));
const MonthlyPage = lazy(() => import('../pages/Disponibilidade/MonthlyPage'));
const ControlePage = lazy(() => import('../pages/Controle/ControlePage'));
const DATImportacoesPage = lazy(() => import('../pages/DAT/ImportacoesPage'));
const PerfilPage = lazy(() => import('../pages/Perfil/PerfilPage'));
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

interface AppRoutesProps {
  user: CurrentUser;
  permissions: Permissions;
  policies: readonly string[];
}

export function AppRoutes({ user, permissions, policies }: AppRoutesProps): JSX.Element {
  const {
    canCoordenador, canControle, canDAT, canApproveSuper, canDisponibilidade, isFormador,
  } = permissions;

  // #1271: rotas gateadas por <RequirePolicy> (policy= direto p/ policies públicas, allow=
  // p/ composites/auth). `access` (useCanAccess) permanece só para os composites de
  // disponibilidade/bloqueios (view_all_availability OU escopo próprio, sem policy única).
  const access = useCanAccess(policies, {
    canBloqueios: canControle || canCoordenador || isFormador,
  });

  return (
    <Suspense fallback={<PageLoader />}>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/home" element={<HomePage />} />

        {/* Dashboards — #1271: gate por policy pública (RequirePolicy). Fallback padrão
            do RequirePolicy é a mesma tela genérica ("Recurso indisponível", OWASP). */}
        <Route path="/dashboards" element={<RequirePolicy policy="view_overview_dashboard" policies={policies}><DashboardsPage /></RequirePolicy>} />
        <Route path="/dashboards/compras" element={<RequirePolicy policy="view_compras_dashboard" policies={policies}><ComprasDashboardPage /></RequirePolicy>} />
        <Route path="/dashboards/equipe" element={<RequirePolicy policy="view_team_dashboard" policies={policies}><EquipeDashboardPage /></RequirePolicy>} />
        <Route path="/dashboards/gcal" element={<RequirePolicy policy="view_gcal_dashboard" policies={policies}><GCalDashboardPage /></RequirePolicy>} />
        <Route path="/mapa-brasil" element={<RequirePolicy policy="view_map_metrics" policies={policies}><MapaBrasilPage /></RequirePolicy>} />

        {/* === Solicitações (agrupamento — Epic 3, Issue #1227) === */}
        {/* Páginas pré-existentes mantidas */}
        <Route path="/solicitacoes/minhas" element={<RequirePolicy policy="create_solicitation" policies={policies}><MySolicitacoesPage /></RequirePolicy>} />
        <Route path="/solicitacoes/nova" element={<RequirePolicy policy="create_solicitation" policies={policies}><NewSolicitacaoWizard /></RequirePolicy>} />
        {/* :id/editar — composite (#1169): owner plausível OU privilegiado, sem policy única. */}
        <Route path="/solicitacoes/:id/editar" element={<RequirePolicy allow={canCoordenador || canApproveSuper}><EditSolicitacaoPage /></RequirePolicy>} />

        {/* Páginas movidas para sob /solicitacoes/* (com redirects abaixo) */}
        <Route path="/solicitacoes/aprovacoes" element={<RequirePolicy policy="access_solicitation_approvals" policies={policies}><ApprovalsPage /></RequirePolicy>} />
        {/* Grade Mensal / Bloqueios / Deslocamentos — composites: policy view_all_availability
            OU acesso scoped/próprio (Coordenador/Formador) sem policy pública. */}
        <Route path="/solicitacoes/disponibilidade" element={<RequirePolicy allow={access.can('view_all_availability') || canDisponibilidade}><MonthlyPage /></RequirePolicy>} />
        <Route path="/solicitacoes/bloqueios" element={<RequirePolicy allow={access.canAccessBlocks}><DisponibilidadeBlocks /></RequirePolicy>} />
        <Route path="/solicitacoes/deslocamentos" element={<RequirePolicy allow={access.can('view_all_availability') || canControle || canCoordenador || canDAT}><DeslocamentosPage /></RequirePolicy>} />
        <Route path="/solicitacoes/meus-eventos" element={<RequirePolicy allow={!!user}><MeusEventosPage /></RequirePolicy>} />
        <Route path="/perfil" element={<RequirePolicy allow={!!user}><PerfilPage user={user} /></RequirePolicy>} />

        {/* Redirects de URLs legadas → novas (preserva deep-links/bookmarks) */}
        <Route path="/aprovacoes" element={<Navigate to="/solicitacoes/aprovacoes" replace />} />
        <Route path="/disponibilidade" element={<Navigate to="/solicitacoes/disponibilidade" replace />} />
        <Route path="/bloqueios" element={<Navigate to="/solicitacoes/bloqueios" replace />} />
        <Route path="/deslocamentos" element={<Navigate to="/solicitacoes/deslocamentos" replace />} />
        <Route path="/meus-eventos" element={<Navigate to="/solicitacoes/meus-eventos" replace />} />

        {/* Controle Module — #1271: policy access_controle_section (paridade com canControle);
            compras somam DAT via allow (composite sem policy única). */}
        <Route path="/controle" element={<RequirePolicy policy="access_controle_section" policies={policies}><ControlePage /></RequirePolicy>} />
        <Route path="/controle/acoes" element={<RequirePolicy policy="access_controle_section" policies={policies}><AcoesPage /></RequirePolicy>} />
        <Route path="/controle/compras" element={<RequirePolicy allow={canControle || canDAT}><DATComprasPage /></RequirePolicy>} />
        <Route path="/controle/coordenadores" element={<RequirePolicy policy="access_controle_section" policies={policies}><CoordenadoresPage /></RequirePolicy>} />
        <Route path="/compras-materiais" element={<RequirePolicy allow={canControle || canDAT}><DATComprasPage /></RequirePolicy>} />
        {/* /deslocamentos movido para /solicitacoes/deslocamentos (Epic 3, Issue #1227 — redirect já registrado acima) */}
        <Route path="/controle/formacoes" element={<RequirePolicy policy="access_controle_section" policies={policies}><FormacoesPage /></RequirePolicy>} />
        <Route path="/controle/plano-formacoes" element={<RequirePolicy policy="access_controle_section" policies={policies}><PlanoFormacoesPage /></RequirePolicy>} />
        <Route path="/controle/pre-agenda" element={<RequirePolicy policy="access_controle_section" policies={policies}><PreAgendaPage /></RequirePolicy>} />
        <Route path="/pre-agenda" element={<RequirePolicy policy="access_controle_section" policies={policies}><PreAgendaPage /></RequirePolicy>} />

        {/* Ações/Notificações — #1271: policy manage_internal_actions. */}
        <Route path="/acoes-notificacao" element={<RequirePolicy policy="manage_internal_actions" policies={policies}><AcoesNotificacaoPage /></RequirePolicy>} />
        <Route path="/acoes-notificacao/timeline" element={<RequirePolicy policy="manage_internal_actions" policies={policies}><AcoesTimelinePage /></RequirePolicy>} />
        <Route path="/notificacoes-internas" element={<RequirePolicy policy="manage_internal_actions" policies={policies}><NotificacoesInternasPage /></RequirePolicy>} />
        {/* DAT Module — #1271: policy manage_admin_registries (paridade com canDAT). */}
        <Route path="/dat/admin" element={<RequirePolicy policy="manage_admin_registries" policies={policies}><AdminDATHomePage /></RequirePolicy>} />
        <Route path="/dat/admin/usuarios" element={<RequirePolicy policy="manage_admin_registries" policies={policies}><UsuariosPage /></RequirePolicy>} />
        <Route path="/dat/admin/municipios" element={<RequirePolicy policy="manage_admin_registries" policies={policies}><MunicipiosPage /></RequirePolicy>} />
        <Route path="/dat/admin/projetos" element={<RequirePolicy policy="manage_admin_registries" policies={policies}><ProjetosPage /></RequirePolicy>} />
        <Route path="/dat/admin/grupos" element={<RequirePolicy policy="manage_admin_registries" policies={policies}><GruposPage /></RequirePolicy>} />
        <Route path="/dat/admin/setores" element={<RequirePolicy policy="manage_admin_registries" policies={policies}><SetoresPage /></RequirePolicy>} />
        <Route path="/dat/admin/funcoes" element={<RequirePolicy policy="manage_admin_registries" policies={policies}><FuncoesPage /></RequirePolicy>} />
        <Route path="/dat/admin/gerencias" element={<RequirePolicy policy="manage_admin_registries" policies={policies}><GerenciasPage /></RequirePolicy>} />
        <Route path="/dat/admin/produtos" element={<RequirePolicy policy="manage_admin_registries" policies={policies}><ProdutosPage /></RequirePolicy>} />
        <Route path="/dat/admin/configuracoes" element={<RequirePolicy policy="manage_admin_registries" policies={policies}><ConfiguracoesPage /></RequirePolicy>} />
        <Route path="/dat/admin/colecoes" element={<RequirePolicy policy="manage_admin_registries" policies={policies}><ColecoesImportPage /></RequirePolicy>} />
        <Route path="/dat/admin/equipe-gerencia" element={<RequirePolicy policy="manage_admin_registries" policies={policies}><EquipeGerenciaImportPage /></RequirePolicy>} />
        <Route path="/dat/cadastros" element={<RequirePolicy policy="manage_admin_registries" policies={policies}><CadastrosPage /></RequirePolicy>} />
        <Route path="/dat/compras-materiais" element={<RequirePolicy allow={canControle || canDAT}><DATComprasPage /></RequirePolicy>} />
        <Route path="/dat/coordenadores" element={<RequirePolicy policy="access_controle_section" policies={policies}><CoordenadoresPage /></RequirePolicy>} />
        {/* PR-C DAT Imports (2026-04-29): /dat/importacao (singular, página antiga
            de Cadastros DAT) redireciona para /dat/importacoes (plural, página
            unificada de imports). Evita 404 em links antigos. */}
        <Route path="/dat/importacao" element={<Navigate to="/dat/importacoes" replace />} />
        <Route path="/dat/importacoes" element={<RequirePolicy policy="manage_admin_registries" policies={policies}><DATImportacoesPage /></RequirePolicy>} />
        <Route path="/dat/registros" element={<RequirePolicy policy="manage_admin_registries" policies={policies}><DATRegistrosPage /></RequirePolicy>} />
      </Routes>
    </Suspense>
  );
}
