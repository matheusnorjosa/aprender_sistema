/**
 * Acesso da pessoa logada — fonte única para menu, rotas, botões e Página Inicial (PR 7 das permissões).
 *
 * - `caps`: as policies de `GET /api/me/policies/`, calculadas no servidor sobre a união
 *   grupos + pacote do perfil da gerência. Toda decisão de "pode ver/fazer" lê daqui.
 * - `ehSuperusuario`: só onde a regra É o superusuário (importação pela tela, PA-02 do próprio,
 *   campos que só ele grava, widget de debug). Fora disso, use uma policy.
 *
 * Setor, função e grupos de `/api/me/` são exibição (`useIdentity`): não decidem acesso
 * (trava em `src/test/lint/acessoSoPorPolicy.test.ts`). O backend continua autoritativo.
 */
import { createContext, useContext } from 'react';

import { computeCapabilities, type Capabilities } from '../hooks/useCapabilities';

export interface Acesso {
  caps: Capabilities;
  ehSuperusuario: boolean;
  /** True enquanto `/me` e `/me/policies` não chegaram (o App mostra o carregando). */
  loading: boolean;
}

/** A regra É o superusuário. Helper único: não leia `is_superuser` direto para decidir. */
export function ehSuperusuario(user: { is_superuser?: boolean } | null | undefined): boolean {
  return user?.is_superuser === true;
}

export function montarAcesso(
  policies: readonly string[],
  user: { is_superuser?: boolean } | null | undefined,
  loading = false,
): Acesso {
  return { caps: computeCapabilities(policies), ehSuperusuario: ehSuperusuario(user), loading };
}

/** Sem provedor (fora do App): ninguém pode nada. */
export const AcessoContext = createContext<Acesso>(montarAcesso([], null));

export function useAcesso(): Acesso {
  return useContext(AcessoContext);
}
