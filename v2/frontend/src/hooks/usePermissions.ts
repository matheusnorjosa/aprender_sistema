import { useMemo } from 'react';
import type { CurrentUser } from '../types';

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
  canDisponibilidade: false,
};

function computePermissionsInternal(user: CurrentUser): Permissions {
  const setores = user.setores || [];
  const funcoes = user.funcoes || [];

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
  const canDashboardOverview = user.is_superuser || inSuperintendencia || inGerencia || inDiretoria;
  const canDashboardEquipe = user.is_superuser || inControle || inGerencia || inSuperintendencia || inDiretoria;
  const canDashboardGcal = user.is_superuser || inControle || inSuperintendencia;
  const canDashboardCompras = user.is_superuser || inDiretoria || inDAT;
  const canMapaBrasil = user.is_superuser || inControle || inDAT || inSuperintendencia || inGerencia || inDiretoria;
  const canDashboardsMenu =
    canDashboardOverview || canDashboardCompras || canDashboardEquipe || canDashboardGcal || canMapaBrasil;
  const canDisponibilidade = user.is_superuser || !inControle;

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
