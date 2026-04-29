import { useMemo } from 'react';
import type { CurrentUser } from '../types';

export interface Permissions {
  /**
   * `is_superuser` exposto via flag canônica para escape hatches de admin
   * (debug widgets, bypass de validações em wizards). Use SOMENTE quando a
   * intenção é admin-only — para regras de negócio normais, prefira
   * `canSeeAllSectors`/`canControle`/derived flag específica.
   */
  isAdmin: boolean;
  // Role flags
  isCoordenador: boolean;
  isFormador: boolean;
  isGerente: boolean;
  // Sector flags
  inSuperintendencia: boolean;
  inGerencia: boolean;
  inDAT: boolean;
  inControle: boolean;
  inDiretoria: boolean;
  // Capability flags
  canApproveSuper: boolean;
  canCoordenador: boolean;
  canControle: boolean;
  canDAT: boolean;
  canAcoesInternas: boolean;
  canDashboardOverview: boolean;
  canDashboardEquipe: boolean;
  canDashboardGcal: boolean;
  canDashboardCompras: boolean;
  canMapaBrasil: boolean;
  canDashboardsMenu: boolean;
  canDisponibilidade: boolean;
  /**
   * "Vê todas as gerências/setores" — semântica unificada para auto-seleção
   * de filtros e widgets cross-setor (FiltersBar, GerenciaSelector, etc.).
   *
   * Inclui: superuser, Superintendência (campo `is_superintendencia` do
   * backend OU presença em `setores`).
   *
   * Substitui hardcodes do tipo `is_superuser || is_superintendencia ||
   * groups.includes('Superintendência')` espalhados em páginas (Epic 3.3).
   */
  canSeeAllSectors: boolean;
}

const EMPTY_PERMISSIONS: Permissions = {
  isAdmin: false,
  isCoordenador: false,
  isFormador: false,
  isGerente: false,
  inSuperintendencia: false,
  inGerencia: false,
  inDAT: false,
  inControle: false,
  inDiretoria: false,
  canApproveSuper: false,
  canCoordenador: false,
  canControle: false,
  canDAT: false,
  canAcoesInternas: false,
  canDashboardOverview: false,
  canDashboardEquipe: false,
  canDashboardGcal: false,
  canDashboardCompras: false,
  canMapaBrasil: false,
  canDashboardsMenu: false,
  canDisponibilidade: false,
  canSeeAllSectors: false,
};

function computePermissionsInternal(user: CurrentUser): Permissions {
  const setores = user.setores || [];
  const funcoes = user.funcoes || [];

  // Admin escape hatch (use com parcimônia — apenas para widgets debug/bypass).
  const isAdmin = user.is_superuser === true;
  // Role flags
  const isCoordenador = funcoes.includes('Coordenador') || funcoes.includes('Apoio de Coordenação');
  const isFormador = funcoes.includes('Formador');
  const isGerente = funcoes.includes('Gerente');

  // Sector flags
  const inSuperintendencia = setores.includes('Superintendência');
  const inGerencia = setores.includes('Gerência');
  const inDAT = setores.includes('DAT');
  const inControle = setores.includes('Controle');
  const inDiretoria = setores.includes('Diretoria');

  // Capability flags
  const canApproveSuper = user.can_approve_super || false;
  const canCoordenador = user.is_superuser || isCoordenador || inDAT;
  const canControle = user.is_superuser || inControle;
  const canDAT = user.is_superuser || inDAT;
  const canAcoesInternas = user.is_superuser || inDAT || isCoordenador || isGerente;
  // Dashboards — alinhado com `v2/docs/rbac_authorization_matrix.md` §3 + decisão D7.
  // Bug 2 fix (Onda 1, C1, 2026-04-27): regras antigas tinham Controle/Gerência/
  // Superintendência indevidamente em vários dashboards. Corrigido para refletir
  // a tabela canônica: Diretoria é o decisor; DAT é ator transversal de
  // suporte/validação; Controle vê apenas Dashboard GCal (operação do calendário).
  const canDashboardOverview = user.is_superuser || inDiretoria;
  const canDashboardEquipe = user.is_superuser || inDiretoria || inDAT;
  const canDashboardGcal = user.is_superuser || inDiretoria || inDAT || inControle;
  const canDashboardCompras = user.is_superuser || inDiretoria || inDAT;
  const canMapaBrasil = user.is_superuser || inDiretoria || inDAT;
  const canDashboardsMenu =
    canDashboardOverview || canDashboardCompras || canDashboardEquipe || canDashboardGcal || canMapaBrasil;
  // canDisponibilidade — decisões D8 + D9 (2026-04-28).
  //
  // Acesso à Grade Mensal:
  //   ALLOW global (cap view_all_availability): Superuser, Controle, DAT
  //   ALLOW scoped (via EquipeGerencia ativa):  Gerente, Coordenador, Apoio
  //   DENY:                                      Diretoria, Formador, sem vínculo
  //
  // D8 (PR #1288): Formador removido (caso especial RD-02/RD-03). Diretoria
  // mantém DENY (decisão executiva, não consulta operacional).
  //
  // D9 (PR atual): Gerente pedagógico/Sup perde cap global e cai em scope
  // via EquipeGerencia (Gerente Vidas vê só Vidas; Gerente Sup vê só Sup).
  // DAT recebe cap global (ator transversal admin).
  const canDisponibilidade =
    user.is_superuser || inControle || inDAT || isGerente || isCoordenador;
  // Epic 3.3: derived flag unificada para "vê todos os setores/gerências".
  // Substitui hardcodes is_superuser || is_superintendencia || groups.includes('Superintendência')
  // em FiltersBar, PreAgendaPage, Solicitacoes, ApprovalsPage.
  const canSeeAllSectors =
    user.is_superuser || user.is_superintendencia === true || inSuperintendencia;

  return {
    isAdmin,
    isCoordenador,
    isFormador,
    isGerente,
    inSuperintendencia,
    inGerencia,
    inDAT,
    inControle,
    inDiretoria,
    canApproveSuper,
    canCoordenador,
    canControle,
    canDAT,
    canAcoesInternas,
    canDashboardOverview,
    canDashboardEquipe,
    canDashboardGcal,
    canDashboardCompras,
    canMapaBrasil,
    canDashboardsMenu,
    canDisponibilidade,
    canSeeAllSectors,
  };
}

/**
 * Compute all RBAC permission flags from user data.
 * Single source of truth for permission checks (Setor + Função).
 */
export function usePermissions(user: CurrentUser | null): Permissions {
  return useMemo(() => {
    if (!user) return EMPTY_PERMISSIONS;
    return computePermissionsInternal(user);
  }, [user]);
}

/**
 * Pure function version for testing (no React dependency).
 */
export function computePermissions(user: CurrentUser | null): Permissions {
  if (!user) return EMPTY_PERMISSIONS;
  return computePermissionsInternal(user);
}
