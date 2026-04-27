/**
 * RequirePolicy — Route guard wrapper (Epic 3, Issue #1228).
 *
 * Renderiza children se o user possui a policy (ou se `allow=true`).
 * Caso contrário, mostra `fallback` (default: <Forbidden /> Ant Design).
 *
 * Aceita 2 modos:
 *   1. Por policy literal: `<RequirePolicy policy="view_compras_dashboard" policies={...}>`
 *   2. Por flag derivada (escape hatch): `<RequirePolicy allow={canAccessApprovals}>`
 *
 * O segundo modo é necessário para acessos compostos sem policy pública
 * mapeada hoje (ex: aprovações = composite Gerente+Superintendência;
 * bloqueios = view_all_availability OR Formador-owns-own).
 *
 * Componente é PURO: recebe `policies` por prop, não busca do backend.
 * Testabilidade alta, zero side-effects.
 */

import type { ReactNode } from 'react';
import { Result } from 'antd';

interface RequirePolicyProps {
  children: ReactNode;
  /** Lista de policy keys do user. Required quando usar `policy`, ignorado se `allow` for definido. */
  policies?: readonly string[];
  /** Policy key a verificar (modo 1). */
  policy?: string;
  /** Override semântico: se `true`, renderiza children incondicionalmente (modo 2). */
  allow?: boolean;
  /** Fallback custom (default: <Forbidden /> 403 Result). */
  fallback?: ReactNode;
  /** Se `true`, renderiza `loadingFallback` em vez de children/fallback. Evita flash de 403. */
  loading?: boolean;
  /** Loader custom mostrado enquanto `loading=true`. Default: null (nada). */
  loadingFallback?: ReactNode;
}

function DefaultForbidden(): JSX.Element {
  return (
    <Result
      status="403"
      title="Sem permissão"
      subTitle="Você não tem permissão para acessar esta página."
    />
  );
}

export function RequirePolicy({
  children,
  policies,
  policy,
  allow,
  fallback,
  loading = false,
  loadingFallback = null,
}: RequirePolicyProps): JSX.Element {
  if (loading) {
    return <>{loadingFallback}</>;
  }

  // Decisão de acesso: `allow` (explicit override) ganha; senão verifica `policy` em `policies`.
  let granted: boolean;
  if (typeof allow === 'boolean') {
    granted = allow;
  } else if (policy && policies) {
    granted = policies.includes(policy);
  } else {
    // Sem policy nem allow → fail-secure
    granted = false;
  }

  if (granted) {
    return <>{children}</>;
  }

  return <>{fallback ?? <DefaultForbidden />}</>;
}
