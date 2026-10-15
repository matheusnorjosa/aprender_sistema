/**
 * Provedor de acesso para testes: monta o `AcessoContext` como o App monta (policies de
 * `/api/me/policies/` + superusuário do `/api/me/`).
 */
import type { JSX, ReactNode } from 'react';

import { AcessoContext, montarAcesso } from '../contexts/AcessoContext';

export function ComAcesso({
  policies,
  superusuario = false,
  children,
}: {
  policies: readonly string[];
  superusuario?: boolean;
  children: ReactNode;
}): JSX.Element {
  return (
    <AcessoContext.Provider value={montarAcesso(policies, { is_superuser: superusuario })}>
      {children}
    </AcessoContext.Provider>
  );
}
