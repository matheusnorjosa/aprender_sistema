/**
 * Endereço desconhecido na área logada (item 38, ensaio de 20/10/2026).
 *
 * Nenhuma rota casava e a área logada ficava em branco, só a casca. '/login' não é rota (o login
 * aparece quando não há sessão): quem entra com ele no endereço vai para a Página Inicial, como
 * qualquer outro endereço desconhecido (não há página de "não encontrado").
 */
import type { JSX } from 'react';
import { MemoryRouter, useLocation } from 'react-router';
import { render, screen } from '@testing-library/react';
import { describe, expect, test, vi } from 'vitest';

import { AppRoutes } from '../AppRoutes';
import type { CurrentUser } from '../../types';
import { ComAcesso } from '../../test/comAcesso';

// Páginas lazy (Suspense): na CI, cerca de 4x mais lenta, o 1º render passa dos 5 s padrão.
vi.setConfig({ testTimeout: 20_000 });

vi.mock('../../pages/Home/HomePage', () => ({ default: () => <h1>Página Inicial</h1> }));

const USUARIO: CurrentUser = {
  id: 1,
  username: 'coord',
  email: 'coord@test.com',
  first_name: 'Coord',
  last_name: 'Teste',
  name: 'Coord Teste',
  groups: [],
  setores: ['Vidas'],
  funcoes: ['Coordenador'],
  gerencias: [],
  is_superuser: false,
  is_superintendencia: false,
  can_approve_super: false,
  permissions: [],
};

function Endereco(): JSX.Element {
  return <output aria-label="endereço">{useLocation().pathname}</output>;
}

function renderRota(rota: string): void {
  render(
    <MemoryRouter initialEntries={[rota]}>
      <ComAcesso policies={[]}>
        <AppRoutes user={USUARIO} />
        <Endereco />
      </ComAcesso>
    </MemoryRouter>,
  );
}

describe('AppRoutes — endereço desconhecido depois de entrar', () => {
  test('/login vai para a Página Inicial', async () => {
    renderRota('/login');

    expect(await screen.findByRole('heading', { name: 'Página Inicial' }, { timeout: 5000 })).toBeInTheDocument();
    expect(screen.getByRole('status', { name: 'endereço' })).toHaveTextContent(/^\/$/);
  });

  test('outro endereço desconhecido também vai para a Página Inicial', async () => {
    renderRota('/solicitacoes/pagina-que-nao-existe');

    expect(await screen.findByRole('heading', { name: 'Página Inicial' }, { timeout: 5000 })).toBeInTheDocument();
    expect(screen.getByRole('status', { name: 'endereço' })).toHaveTextContent(/^\/$/);
  });

  test('rota que existe não é desviada para a Página Inicial', async () => {
    renderRota('/home');

    expect(await screen.findByRole('heading', { name: 'Página Inicial' }, { timeout: 5000 })).toBeInTheDocument();
    expect(screen.getByRole('status', { name: 'endereço' })).toHaveTextContent(/^\/home$/);
  });
});
