/**
 * Deslocamentos decide pela policy `access_travel` (PR 7 das permissões), a mesma da rota e do menu.
 *
 * O servidor soma na policy o que antes o front lia do /me: view_all_availability, grupo e o
 * vínculo de gestão vigente (PR A). Antes a página tinha regra própria (com Superintendência e sem
 * view_all_availability) e divergia da rota: quem entrava por uma caía em "Sem permissão" na outra.
 */

import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { MemoryRouter } from 'react-router';

import { ComAcesso } from '../../../test/comAcesso';

const { listDeslocamentosMock, listFormadoresMock } = vi.hoisted(() => ({
  listDeslocamentosMock: vi.fn(),
  listFormadoresMock: vi.fn(),
}));

vi.mock('../../../api/deslocamentos', () => ({
  listDeslocamentos: listDeslocamentosMock,
  listFormadoresDoSetor: listFormadoresMock,
  listAlvosDeslocamento: vi.fn().mockResolvedValue([]),
  createDeslocamento: vi.fn(),
  updateDeslocamento: vi.fn(),
  deleteDeslocamento: vi.fn(),
}));
vi.mock('../../../components/DatImportsCentralizedBanner', () => ({ default: () => null }));

import DeslocamentosPage from '../DeslocamentosPage';

function renderPage(policies: readonly string[]) {
  return render(
    <MemoryRouter>
      <ComAcesso policies={policies}>
        <DeslocamentosPage />
      </ComAcesso>
    </MemoryRouter>,
  );
}

describe('DeslocamentosPage — policy access_travel (PR 7)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listDeslocamentosMock.mockResolvedValue({ count: 0, next: null, previous: null, results: [] });
    listFormadoresMock.mockResolvedValue([]);
  });

  test('com access_travel (ex.: gestor só por vínculo): abre a página e lista', async () => {
    renderPage(['access_travel']);

    await waitFor(() => expect(listDeslocamentosMock).toHaveBeenCalled(), { timeout: 3000 });
    expect(screen.queryByText('Sem permissão')).not.toBeInTheDocument();
  });

  test('sem access_travel (ex.: Formador, só view_all_availability não basta sem a policy): negado', async () => {
    renderPage(['view_all_availability', 'access_availability_blocks']);

    expect(await screen.findByText('Sem permissão', {}, { timeout: 3000 })).toBeInTheDocument();
    expect(listDeslocamentosMock).not.toHaveBeenCalled();
  });
});
