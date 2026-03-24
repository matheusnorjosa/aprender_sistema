import { useMemo } from 'react';
import type { CurrentUser } from '../types';

const FUNCTIONAL_PERMISSIONS = {
  APROVAR_SUPERINTENDENCIA: 'pode_aprovar_superintendencia',
  CRIAR_SOLICITACAO_COORD_DAT: 'pode_criar_solicitacao_coord_dat',
  IMPORTAR_CONTROLE_SUPER: 'pode_importar_controle_super',
  OPERAR_DAT: 'pode_operar_dat',
  OPERAR_DAT_EXCLUSIVO: 'pode_operar_dat_exclusivo',
  OPERAR_CONTROLE_DAT: 'pode_operar_controle_dat',
  OPERAR_CONTROLE: 'pode_operar_controle',
  OPERAR_GERENCIA: 'pode_operar_gerencia',
  ACESSAR_DASHBOARD_OVERVIEW: 'pode_acessar_dashboard_overview',
  ACESSAR_DASHBOARD_COMPRAS: 'pode_acessar_dashboard_compras',
  ACESSAR_MAP_METRICS: 'pode_acessar_map_metrics',
} as const;

export interface Permissions {
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
  canBloqueios: boolean;
  canDisponibilidade: boolean;
}

const EMPTY_PERMISSIONS: Permissions = {
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
  canBloqueios: false,
  canDisponibilidade: false,
};

function hasAnyPermission(permissionSet: Set<string>, ...codenames: string[]): boolean {
  return codenames.some((codename) => permissionSet.has(codename));
}

function buildPermissionSet(user: CurrentUser): Set<string> {
  return new Set(user.permissions || []);
}

function computePermissionsInternal(user: CurrentUser): Permissions {
  const permissionSet = buildPermissionSet(user);
  const setores = user.setores || [];
  const funcoes = user.funcoes || [];

  // Legacy fallback (kept for compatibility while RBAC functional rollout is completed)
  const isCoordenadorLegacy = funcoes.includes('Coordenador') || funcoes.includes('Apoio de Coordenação');
  const isFormadorLegacy = funcoes.includes('Formador');
  const isGerenteLegacy = funcoes.includes('Gerente');
  const inSuperintendenciaLegacy = setores.includes('Superintendência');
  const inGerenciaLegacy = setores.includes('Gerência');
  const inDATLegacy = setores.includes('DAT');
  const inControleLegacy = setores.includes('Controle');
  const inDiretoriaLegacy = setores.includes('Diretoria');

  // Role flags
  const isCoordenador = user.is_superuser
    || hasAnyPermission(permissionSet, FUNCTIONAL_PERMISSIONS.CRIAR_SOLICITACAO_COORD_DAT)
    || isCoordenadorLegacy;
  const isFormador = isFormadorLegacy;
  const isGerente = user.is_superuser
    || hasAnyPermission(permissionSet, FUNCTIONAL_PERMISSIONS.OPERAR_GERENCIA)
    || isGerenteLegacy;

  // Sector flags (display/compat)
  const inSuperintendencia = inSuperintendenciaLegacy;
  const inGerencia = inGerenciaLegacy;
  const inDAT = inDATLegacy;
  const inControle = inControleLegacy;
  const inDiretoria = inDiretoriaLegacy;

  // Capability flags (permission-first, with legacy fallback)
  const canApproveSuper = user.can_approve_super || hasAnyPermission(
    permissionSet,
    FUNCTIONAL_PERMISSIONS.APROVAR_SUPERINTENDENCIA,
  );
  const canCoordenador = user.is_superuser
    || hasAnyPermission(permissionSet, FUNCTIONAL_PERMISSIONS.CRIAR_SOLICITACAO_COORD_DAT)
    || isCoordenadorLegacy
    || inDATLegacy;
  const canControle = user.is_superuser
    || hasAnyPermission(
      permissionSet,
      FUNCTIONAL_PERMISSIONS.OPERAR_CONTROLE,
      FUNCTIONAL_PERMISSIONS.OPERAR_CONTROLE_DAT,
      FUNCTIONAL_PERMISSIONS.IMPORTAR_CONTROLE_SUPER,
    )
    || inControleLegacy;
  const canDAT = user.is_superuser
    || hasAnyPermission(
      permissionSet,
      FUNCTIONAL_PERMISSIONS.OPERAR_DAT,
      FUNCTIONAL_PERMISSIONS.OPERAR_DAT_EXCLUSIVO,
    )
    || inDATLegacy;
  const canAcoesInternas = user.is_superuser
    || hasAnyPermission(
      permissionSet,
      FUNCTIONAL_PERMISSIONS.CRIAR_SOLICITACAO_COORD_DAT,
      FUNCTIONAL_PERMISSIONS.OPERAR_GERENCIA,
      FUNCTIONAL_PERMISSIONS.OPERAR_DAT,
      FUNCTIONAL_PERMISSIONS.OPERAR_DAT_EXCLUSIVO,
    )
    || inDATLegacy
    || isCoordenadorLegacy
    || isGerenteLegacy;
  const canDashboardOverview = user.is_superuser
    || hasAnyPermission(permissionSet, FUNCTIONAL_PERMISSIONS.ACESSAR_DASHBOARD_OVERVIEW)
    || inSuperintendenciaLegacy
    || inGerenciaLegacy
    || inDiretoriaLegacy;
  const canDashboardEquipe = user.is_superuser
    || hasAnyPermission(
      permissionSet,
      FUNCTIONAL_PERMISSIONS.OPERAR_CONTROLE,
      FUNCTIONAL_PERMISSIONS.OPERAR_CONTROLE_DAT,
      FUNCTIONAL_PERMISSIONS.OPERAR_GERENCIA,
    )
    || inControleLegacy
    || inGerenciaLegacy
    || inSuperintendenciaLegacy
    || inDiretoriaLegacy;
  const canDashboardGcal = user.is_superuser
    || hasAnyPermission(permissionSet, FUNCTIONAL_PERMISSIONS.IMPORTAR_CONTROLE_SUPER)
    || inControleLegacy
    || inSuperintendenciaLegacy;
  const canDashboardCompras = user.is_superuser
    || hasAnyPermission(permissionSet, FUNCTIONAL_PERMISSIONS.ACESSAR_DASHBOARD_COMPRAS)
    || inDiretoriaLegacy
    || inDATLegacy;
  const canMapaBrasil = user.is_superuser
    || hasAnyPermission(permissionSet, FUNCTIONAL_PERMISSIONS.ACESSAR_MAP_METRICS)
    || inControleLegacy
    || inDATLegacy
    || inSuperintendenciaLegacy
    || inGerenciaLegacy
    || inDiretoriaLegacy;
  const canDashboardsMenu =
    canDashboardOverview || canDashboardCompras || canDashboardEquipe || canDashboardGcal || canMapaBrasil;
  const canBloqueios = canControle || canCoordenador || isFormador;
  const canDisponibilidade = user.is_superuser || !inControleLegacy;

  return {
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
    canBloqueios,
    canDisponibilidade,
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
