/**
 * Aba aberta de uma versão que saiu do ar: a tela não carrega porque o pedaço dela sumiu do servidor.
 * O boundary manda recarregar uma vez e, no lugar do texto técnico em inglês, diz que o sistema foi
 * atualizado. Erro comum segue com "Algo deu errado".
 */
import { describe, expect, test, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ErrorBoundary } from '../ErrorBoundary';
import { recarregarSeVersaoAntiga } from '../../utils/recargaVersaoNova';

vi.mock('../../utils/recargaVersaoNova', async (original) => {
  const real = await original<typeof import('../../utils/recargaVersaoNova')>();
  return { ...real, recarregarSeVersaoAntiga: vi.fn(() => true) };
});

function TelaQueSumiu(): never {
  throw new TypeError('Failed to fetch dynamically imported module: https://x/assets/HomePage-BKUHwhJH.js');
}

function Boom(): never {
  throw new Error('boom');
}

describe('ErrorBoundary com página de versão antiga', () => {
  test('pedaço de tela que sumiu: manda recarregar e diz que o sistema foi atualizado', async () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});
    render(<ErrorBoundary><TelaQueSumiu /></ErrorBoundary>);

    expect(await screen.findByText('O sistema foi atualizado')).toBeInTheDocument();
    expect(screen.getByText('Recarregue a página para continuar.')).toBeInTheDocument();
    expect(screen.queryByText(/Failed to fetch/)).toBeNull();
    expect(recarregarSeVersaoAntiga).toHaveBeenCalledTimes(1);
    spy.mockRestore();
  });

  test('erro comum continua com "Algo deu errado"', async () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});
    render(<ErrorBoundary><Boom /></ErrorBoundary>);

    expect(await screen.findByText('Algo deu errado')).toBeInTheDocument();
    expect(screen.getByText('boom')).toBeInTheDocument();
    spy.mockRestore();
  });
});
