/**
 * Home do Admin DAT: os cartões não prometem poder que grupo e função não dão (PR 12, o acesso
 * vem da lotação), não falam do Django Admin e dizem o que a tela faz. O cartão Grupos (a lista
 * com os grupos sem classificação) aparece só para o superusuário.
 */
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { beforeEach, describe, expect, test, vi } from 'vitest';

vi.mock('../../../api/auth', () => ({ checkAuth: vi.fn() }));

import { checkAuth } from '../../../api/auth';
import AdminDATHomePage from '../AdminDATHomePage';

function renderPage(): void {
  render(
    <MemoryRouter>
      <AdminDATHomePage />
    </MemoryRouter>,
  );
}

describe('AdminDATHomePage: textos dos cartões', { timeout: 20000 }, () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(checkAuth).mockResolvedValue({ authenticated: true, user: { is_superuser: false } } as never);
  });

  test('setores e funções são etiquetas que não dão acesso', async () => {
    renderPage();

    expect(
      await screen.findByText('Etiquetas de setor (não dão acesso; o acesso vem da lotação na gerência)'),
    ).toBeInTheDocument();
    expect(screen.getByText('Etiquetas de função (cargo; não dá acesso)')).toBeInTheDocument();
    expect(screen.queryByText(/o que cada usuário pode fazer/)).not.toBeInTheDocument();
    expect(screen.queryByText(/onde cada usuário atua/)).not.toBeInTheDocument();
  });

  test('usuários e configurações dizem o que a tela faz, sem Django Admin', async () => {
    renderPage();

    expect(await screen.findByText('Contas, senha e lotação')).toBeInTheDocument();
    expect(screen.getByText('Buffer de deslocamento e teto de horas')).toBeInTheDocument();
    expect(screen.queryByText(/Django Admin/)).not.toBeInTheDocument();
    expect(screen.queryByText(/CPF, grupos e perfis/)).not.toBeInTheDocument();
  });

  test('superusuário vê o cartão Grupos', async () => {
    vi.mocked(checkAuth).mockResolvedValue({ authenticated: true, user: { is_superuser: true } } as never);
    renderPage();

    expect(await screen.findByRole('heading', { name: 'Grupos' })).toBeInTheDocument();
  });

  test('quem não é superusuário não vê o cartão Grupos', async () => {
    renderPage();

    await waitFor(() => expect(checkAuth).toHaveBeenCalled());
    await screen.findByRole('heading', { name: 'Setores' });
    expect(screen.queryByRole('heading', { name: 'Grupos' })).not.toBeInTheDocument();
  });

  test('falha ao consultar a sessão: sem o cartão Grupos', async () => {
    vi.mocked(checkAuth).mockRejectedValue(new Error('falhou'));
    renderPage();

    await waitFor(() => expect(checkAuth).toHaveBeenCalled());
    await screen.findByRole('heading', { name: 'Setores' });
    expect(screen.queryByRole('heading', { name: 'Grupos' })).not.toBeInTheDocument();
  });
});
