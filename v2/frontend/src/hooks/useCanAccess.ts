/**
 * useCanAccess — Capability Policy Layer (frontend) — Epic 3, Issue #1228.
 *
 * Camada de tradução semântica entre `PUBLIC_POLICY_KEYS` (consumidas via
 * `GET /api/me/policies/`, Epic 4.4) e os componentes React. Componentes
 * usam **derived flags** (ex: `canAccessApprovals`); a origem (policy
 * pública vs legacy flag computada por `usePermissions`) é detalhe
 * interno deste hook.
 *
 * Quando uma policy pública for criada (ex: Epic 4.6 expõe `approve_*`),
 * basta trocar 1 linha aqui — componentes não mudam.
 */

import { useMemo } from 'react';

/**
 * Flags legacy do hook `usePermissions` que ainda não têm policy pública
 * equivalente. Servem como fallback durante migração — ver comentários de
 * cada derived flag abaixo.
 */
export interface LegacyAccessFlags {
  /** Composite Gerente+Superintendência. Migrar quando Epic 4.6 criar policy `approve_*` pública. */
  canApproveSuper?: boolean;
  /** `canControle || canCoordenador || isFormador`. Formador owns own bloqueio (RD-02/RD-03). */
  canBloqueios?: boolean;
  /** Hoje 100% legacy. Sem policy pública pra "criar solicitação" (apenas auth + role). */
  canCoordenador?: boolean;
  /** Hardcoded `is_superuser || inDiretoria || inDAT`. Migrável agora — policy `view_compras_dashboard` em PUBLIC_POLICY_KEYS. */
  canDashboardCompras?: boolean;
}

/**
 * Estado de acesso retornado pelo hook. `loading` permite UIs renderizarem
 * skeleton enquanto policies ainda não chegaram do backend.
 */
export interface AccessState {
  /** Lista de policy keys que o usuário possui (subset de `PUBLIC_POLICY_KEYS`). */
  readonly policies: readonly string[];
  /** Match exato contra `PUBLIC_POLICY_KEYS`. False para anonymous, true para superuser (todas). */
  can: (key: string) => boolean;

  // ── Derived flags (semantic translation layer) ──
  // Cada flag combina policy + legacy. Componentes consomem isto, não `can()` direto.
  // Migrar = trocar OR aqui.

  /**
   * Pode acessar fila de aprovações.
   * Composite Setor × Função aprovado em PR 3 hardening RBAC (2026-04-29):
   * Gerente da Superintendência OU Assistente Administrativo do Controle.
   * Fonte de verdade: policy pública `access_solicitation_approvals`.
   * `legacy.canApproveSuper` permanece como fallback compat durante a
   * transição para clientes que ainda não consomem `/api/me/policies/`.
   */
  canAccessApprovals: boolean;

  /**
   * Pode acessar página de bloqueios. Inclui Formador (escopo próprio via queryset).
   * Hoje: `view_all_availability` OU legacy.canBloqueios. Sem policy pública para Formador-owns-own.
   */
  canAccessBlocks: boolean;

  /**
   * Pode criar nova solicitação. Hoje: 100% legacy (Coordenador / Apoio de Coordenação / Gerente / Superuser).
   * Sem policy pública mapeada — frontend confere flag, backend ainda valida via permission_classes específica.
   */
  canCreateSolicitation: boolean;

  /**
   * Pode ver Dashboard de Compras. Onda 2 A2 (2026-04-27): consome policy
   * pública `view_compras_dashboard` (atribuída a Diretoria + DAT no seed).
   * Legacy fallback preservado durante transição.
   */
  canViewComprasDashboard: boolean;
}

/**
 * Versão pura (sem React) — usada em tests e para call sites sem render.
 * O hook `useCanAccess` é apenas um wrapper memoizado.
 */
export function computeAccess(
  policies: readonly string[],
  legacy: LegacyAccessFlags = {}
): AccessState {
  const policySet = new Set(policies);
  const can = (key: string): boolean => policySet.has(key);

  const canAccessApprovals =
    can('access_solicitation_approvals') ||   // PR 3 hardening RBAC (2026-04-29)
    legacy.canApproveSuper === true;

  const canAccessBlocks =
    can('view_all_availability') ||
    legacy.canBloqueios === true;

  const canCreateSolicitation =
    legacy.canCoordenador === true;

  const canViewComprasDashboard =
    can('view_compras_dashboard') ||
    legacy.canDashboardCompras === true;

  return {
    policies,
    can,
    canAccessApprovals,
    canAccessBlocks,
    canCreateSolicitation,
    canViewComprasDashboard,
  };
}

/**
 * Hook React. Memoiza o `AccessState` por `policies` + `legacy` flags
 * para evitar re-render desnecessário em componentes consumidores.
 */
export function useCanAccess(
  policies: readonly string[],
  legacy: LegacyAccessFlags = {}
): AccessState {
  return useMemo(
    () => computeAccess(policies, legacy),
    // Dependências granulares — `legacy` é objeto, vamos por chaves.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [
      policies,
      legacy.canApproveSuper,
      legacy.canBloqueios,
      legacy.canCoordenador,
      legacy.canDashboardCompras,
    ]
  );
}
