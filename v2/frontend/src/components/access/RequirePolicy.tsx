/**
 * RequirePolicy — Route guard wrapper (Epic 3, Issue #1228).
 *
 * Renderiza children se o user possui a policy (ou se `allow=true`).
 * Caso contrário, mostra `fallback` (default: <Forbidden /> Ant Design).
 *
 * Aceita 2 modos:
 *   1. Por policy: `<RequirePolicy policy="view_compras_dashboard" policies={...}>`, ou uma
 *      lista (`policy={['a', 'b']}`) quando qualquer uma basta.
 *   2. Por condição que não é policy: `<RequirePolicy allow={...}>` — só autenticado
 *      (`!!user`) e o que é do superusuário (`ehSuperusuario`). PR 7 das permissões: acesso de
 *      negócio é sempre policy.
 *
 * Componente é PURO: recebe `policies` por prop, não busca do backend.
 * Testabilidade alta, zero side-effects.
 */

import type { ReactNode, JSX } from 'react';
import { Button, Result } from 'antd';
import { Link } from 'react-router';

interface RequirePolicyProps {
  children: ReactNode;
  /** Lista de policy keys do user. Required quando usar `policy`, ignorado se `allow` for definido. */
  policies?: readonly string[];
  /** Policy key a verificar (modo 1); numa lista, qualquer uma basta. */
  policy?: string | readonly string[];
  /** Override semântico: se `true`, renderiza children incondicionalmente (modo 2). */
  allow?: boolean;
  /** Fallback custom (default: <Forbidden /> 403 Result). */
  fallback?: ReactNode;
  /** Se `true`, renderiza `loadingFallback` em vez de children/fallback. Evita flash de 403. */
  loading?: boolean;
  /** Loader custom mostrado enquanto `loading=true`. Default: null (nada). */
  loadingFallback?: ReactNode;
}

/**
 * Fallback genérico (OWASP Authorization Cheat Sheet):
 * - NÃO revela que o recurso existe ("403 sem permissão" é vazamento)
 * - NÃO menciona qual permission/role é necessária
 * - NÃO usa código HTTP visível
 * - Mensagem ambígua: pode ser "não existe" ou "não disponível para você"
 *
 * Status visual `info` (não `403`) — neutralidade. CTA único: voltar ao início.
 */
function DefaultForbidden(): JSX.Element {
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
    const aceitas: readonly string[] = typeof policy === 'string' ? [policy] : policy;
    granted = aceitas.some((p) => policies.includes(p));
  } else {
    // Sem policy nem allow → fail-secure
    granted = false;
  }

  if (granted) {
    return <>{children}</>;
  }

  return <>{fallback ?? <DefaultForbidden />}</>;
}
