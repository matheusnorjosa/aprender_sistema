/**
 * Monta a tela num data router de memória, como o App monta (`createBrowserRouter`, App.tsx): o
 * `useBlocker` só funciona em data router. A tela fica em `em`, com `antes` no histórico (para o
 * Voltar ter para onde ir); qualquer outro endereço mostra "Outra página".
 */
import type { ReactNode } from 'react';
import { render, type RenderResult } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router';

type Roteador = ReturnType<typeof createMemoryRouter>;

export function renderNoRoteador(
  tela: ReactNode,
  { em = '/', antes = [] }: { em?: string; antes?: string[] } = {},
): RenderResult & { router: Roteador } {
  const router = createMemoryRouter(
    [
      { path: em, element: tela },
      { path: '*', element: <p>Outra página</p> },
    ],
    { initialEntries: [...antes, em], initialIndex: antes.length },
  );
  return { ...render(<RouterProvider router={router} />), router };
}

/** Endereço atual do roteador (caminho + busca). */
export function enderecoAtual(router: Roteador): string {
  const { pathname, search } = router.state.location;
  return pathname + search;
}
