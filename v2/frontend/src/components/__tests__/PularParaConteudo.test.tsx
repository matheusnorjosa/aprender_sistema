/**
 * "Pular para o conteúdo" leva o foco ao conteúdo sem criar entrada no histórico.
 *
 * O link nativo (`href="#main"`) empurrava uma entrada sem o estado do roteador. Voltar até ela
 * chegava ao `useBlocker` sem distância (delta nulo) e a Nova Solicitação saía sem perguntar,
 * perdendo o que foi preenchido.
 */
import type { JSX } from 'react';
import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, test } from 'vitest';
import { createBrowserRouter, useBlocker } from 'react-router';
import { RouterProvider } from 'react-router/dom';
import { PularParaConteudo } from '../PularParaConteudo';

afterEach(() => {
  window.history.replaceState(null, '', '/');
});

describe('PularParaConteudo', () => {
  test('pelo teclado, foca o conteúdo sem criar entrada no histórico nem mudar o endereço', async () => {
    window.history.replaceState(null, '', '/');
    render(
      <>
        <PularParaConteudo />
        <main id="main">Conteúdo</main>
      </>,
    );
    const entradas = window.history.length;
    const user = userEvent.setup();

    await user.tab();
    const link = screen.getByRole('link', { name: 'Pular para o conteúdo principal' });
    expect(link).toHaveFocus();
    await user.keyboard('{Enter}');

    expect(screen.getByRole('main')).toHaveFocus();
    expect(window.history.length).toBe(entradas);
    expect(window.location.hash).toBe('');
  });

  test('sem conteúdo na tela (carregando), não navega', async () => {
    window.history.replaceState(null, '', '/');
    render(<PularParaConteudo />);
    const entradas = window.history.length;

    await userEvent.setup().click(screen.getByRole('link', { name: 'Pular para o conteúdo principal' }));

    expect(window.history.length).toBe(entradas);
    expect(window.location.hash).toBe('');
  });

  test('com o roteador do navegador, o Voltar depois do link ainda passa pelo bloqueio', async () => {
    window.history.replaceState(null, '', '/');
    function Formulario(): JSX.Element {
      const bloqueio = useBlocker(true);
      return <main id="main">{bloqueio.state === 'blocked' ? 'SEGURADO' : 'FORMULARIO'}</main>;
    }
    const router = createBrowserRouter([
      { path: '/', element: <main id="main">INICIO</main> },
      { path: '/nova', element: <Formulario /> },
    ]);
    render(
      <>
        <PularParaConteudo />
        <RouterProvider router={router} />
      </>,
    );
    const user = userEvent.setup();

    await user.click(screen.getByRole('link', { name: 'Pular para o conteúdo principal' }));
    await act(() => router.navigate('/nova'));
    expect(await screen.findByText('FORMULARIO')).toBeInTheDocument();

    act(() => window.history.back());

    await waitFor(() => expect(screen.getByText('SEGURADO')).toBeInTheDocument());
    router.dispose();
  });
});
