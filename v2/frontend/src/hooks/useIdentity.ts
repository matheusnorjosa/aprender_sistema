/**
 * useIdentity — "quem é o usuário" (Issue #1269, RBAC 3.1).
 *
 * Camada de **identidade/organograma**: setor e função do usuário + dados de
 * display (nome, badge). É **DISPLAY-ONLY** — NÃO decide autorização. Para "o que
 * o usuário pode fazer", use `useCapabilities(policies)`, derivado exclusivamente
 * de policies públicas.
 *
 * A separação existe para o lint (futuro) distinguir "quem é" de "o que pode":
 * `useIdentity.*` em contexto de route/guard/gate é um smell (autorizar por
 * organograma). Co-existe com `usePermissions` (legacy) até a migração de callers
 * (ondas 3.2/3.3); `usePermissions` será removido na onda 4.5.
 */
import { useMemo } from 'react';
import type { CurrentUser } from '../types';

export interface Identity {
  /** `is_superuser`. Escape hatch de admin — não usar para regra de negócio. */
  isAdmin: boolean;
  isCoordenador: boolean;
  isFormador: boolean;
  isGerente: boolean;
  inSuperintendencia: boolean;
  inDAT: boolean;
  inControle: boolean;
  inDiretoria: boolean;
  /** Nome legível: `name` do backend, com fallback para `username`. */
  displayName: string;
  /**
   * Rótulo curto de papel para exibição (chip/tag). Prioridade determinística:
   * Admin > Gerente > Coordenador/Apoio > Formador > primeiro setor > 'Usuário'.
   * Display-only — o caller pode sobrescrever com um rótulo específico da tela.
   */
  badge: string;
}

const ANONYMOUS_IDENTITY: Identity = {
  isAdmin: false,
  isCoordenador: false,
  isFormador: false,
  isGerente: false,
  inSuperintendencia: false,
  inDAT: false,
  inControle: false,
  inDiretoria: false,
  displayName: '',
  badge: 'Usuário',
};

interface RoleFlags {
  isAdmin: boolean;
  isGerente: boolean;
  isCoordenador: boolean;
  isFormador: boolean;
}

function computeBadge(user: CurrentUser, roles: RoleFlags): string {
  if (roles.isAdmin) return 'Admin';
  if (roles.isGerente) return 'Gerente';
  if (roles.isCoordenador) {
    return (user.funcoes || []).includes('Coordenador') ? 'Coordenador' : 'Apoio de Coordenação';
  }
  if (roles.isFormador) return 'Formador';
  return (user.setores || [])[0] ?? 'Usuário';
}

/** Versão pura (sem React) — usada em tests e call sites sem render. */
export function computeIdentity(user: CurrentUser | null): Identity {
  if (!user) return ANONYMOUS_IDENTITY;

  const setores = user.setores || [];
  const funcoes = user.funcoes || [];

  const isAdmin = user.is_superuser === true;
  const isCoordenador = funcoes.includes('Coordenador') || funcoes.includes('Apoio de Coordenação');
  const isFormador = funcoes.includes('Formador');
  const isGerente = funcoes.includes('Gerente');

  const inSuperintendencia = setores.includes('Superintendência');
  const inDAT = setores.includes('DAT');
  const inControle = setores.includes('Controle');
  const inDiretoria = setores.includes('Diretoria');

  const displayName = user.name || user.username || '';
  const badge = computeBadge(user, { isAdmin, isGerente, isCoordenador, isFormador });

  return {
    isAdmin,
    isCoordenador,
    isFormador,
    isGerente,
    inSuperintendencia,
    inDAT,
    inControle,
    inDiretoria,
    displayName,
    badge,
  };
}

/** Hook React memoizado por `user`. */
export function useIdentity(user: CurrentUser | null): Identity {
  return useMemo(() => computeIdentity(user), [user]);
}
