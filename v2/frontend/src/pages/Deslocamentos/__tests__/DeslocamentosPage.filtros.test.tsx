/**
 * #1622 [M09-06] Deslocamentos: filtros Origem/Destino inutilizáveis.
 *
 * Bug: `loading` é estado único → o early-return `if (loading) return <Carregando/>`
 * desmonta a página inteira a cada fetch de filtro (input perde foco/valor), os inputs
 * Origem/Destino são não-controlados (voltam vazios ao remontar) e `loadFormadores`
 * refaz a chamada de opções a cada tecla.
 */

import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { MemoryRouter } from 'react-router';

const { getMeMock, listDeslocamentosMock, listFormadoresMock } = vi.hoisted(() => ({
  getMeMock: vi.fn(),
  listDeslocamentosMock: vi.fn(),
  listFormadoresMock: vi.fn(),
}));

vi.mock('../../../api/availability', () => ({ getMe: getMeMock }));
vi.mock('../../../api/deslocamentos', () => ({
  listDeslocamentos: listDeslocamentosMock,
  listFormadoresDoSetor: listFormadoresMock,
  createDeslocamento: vi.fn(),
  updateDeslocamento: vi.fn(),
  deleteDeslocamento: vi.fn(),
}));
vi.mock('../../../hooks/usePermissions', () => ({
  computePermissions: () => ({
    canControle: false,
    canCoordenador: true,
    canDAT: false,
    inSuperintendencia: false,
  }),
}));
vi.mock('../../../components/DatImportsCentralizedBanner', () => ({ default: () => null }));

import DeslocamentosPage from '../DeslocamentosPage';

function renderPage() {
  return render(
    <MemoryRouter>
      <DeslocamentosPage />
    </MemoryRouter>
  );
}

describe('DeslocamentosPage — filtros (#1622)', () => {
  beforeEach(() => {
    getMeMock.mockReset();
    listDeslocamentosMock.mockReset();
    listFormadoresMock.mockReset();
    getMeMock.mockResolvedValue({ id: 1, username: 'coord', groups: ['Coordenador'] });
    listDeslocamentosMock.mockResolvedValue({ count: 0, next: null, previous: null, results: [] });
    listFormadoresMock.mockResolvedValue([]);
  });

  test('digitar no filtro Origem: input preserva valor, página não desmonta, opções não refetadas', async () => {
    renderPage();

    const origem = (await screen.findByPlaceholderText('Origem', undefined, { timeout: 5000 })) as HTMLInputElement;
    await waitFor(() => expect(listFormadoresMock).toHaveBeenCalledTimes(1));

    // Digita no filtro (um único change com o valor completo evita corridas de remontagem).
    fireEvent.change(origem, { target: { value: 'Fortaleza' } });

    // O fetch de filtro (debounced) acontece com o valor digitado.
    await waitFor(() =>
      expect(listDeslocamentosMock).toHaveBeenCalledWith(expect.objectContaining({ origem: 'Fortaleza' }))
    );

    // A página NÃO desmontou para "Carregando..." — o card de Filtros permanece.
    expect(screen.getByText('Filtros')).toBeInTheDocument();

    // O input mantém o valor digitado (controlado).
    expect((screen.getByPlaceholderText('Origem') as HTMLInputElement).value).toBe('Fortaleza');

    // As opções de formador NÃO são refetadas a cada mudança de filtro.
    expect(listFormadoresMock).toHaveBeenCalledTimes(1);
  });
});
