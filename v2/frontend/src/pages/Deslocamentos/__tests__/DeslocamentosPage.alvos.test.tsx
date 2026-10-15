/**
 * PR 8 das permissões (P16; decisão do dono O8-5, 15/10/2026): no formulário de deslocamento, o
 * campo "Formador" aparece só para quem pode registrar o deslocamento de outra pessoa e oferece só
 * esses formadores (`GET /api/deslocamentos/alvos/`): a gerente e a coordenadora veem os formadores
 * das próprias gerências. Quem não delega (ex.: Apoio) registra o próprio, sem o campo. Antes o
 * campo listava os formadores do setor para todos, e o servidor respondia 403.
 */

import { fireEvent, render, screen, within } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { MemoryRouter } from 'react-router';

import { ComAcesso } from '../../../test/comAcesso';

const { listDeslocamentosMock, listFormadoresMock, listAlvosMock } = vi.hoisted(() => ({
  listDeslocamentosMock: vi.fn(),
  listFormadoresMock: vi.fn(),
  listAlvosMock: vi.fn(),
}));

vi.mock('../../../api/deslocamentos', () => ({
  listDeslocamentos: listDeslocamentosMock,
  listFormadoresDoSetor: listFormadoresMock,
  listAlvosDeslocamento: listAlvosMock,
  createDeslocamento: vi.fn(),
  updateDeslocamento: vi.fn(),
  deleteDeslocamento: vi.fn(),
}));
vi.mock('../../../components/DatImportsCentralizedBanner', () => ({ default: () => null }));

import DeslocamentosPage from '../DeslocamentosPage';

async function abrirNovo(): Promise<HTMLElement> {
  render(
    <MemoryRouter>
      <ComAcesso policies={['access_travel']}>
        <DeslocamentosPage />
      </ComAcesso>
    </MemoryRouter>,
  );
  fireEvent.click(await screen.findByRole('button', { name: /Novo Deslocamento/ }, { timeout: 5000 }));
  return await screen.findByRole('dialog');
}

describe('DeslocamentosPage — seletor de formador por delegação (PR 8, P16)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listDeslocamentosMock.mockResolvedValue({ count: 0, next: null, previous: null, results: [] });
    listFormadoresMock.mockResolvedValue([{ id: 6, first_name: 'Caio', last_name: 'DoSetor' }]);
  });

  test('quem delega vê o campo com só os formadores que pode registrar', async () => {
    listAlvosMock.mockResolvedValue([{ id: 5, first_name: 'Bia', last_name: 'DaGerencia' }]);
    const dialogo = await abrirNovo();

    const campo = await within(dialogo).findByLabelText('Formador');
    fireEvent.mouseDown(campo);
    expect(await screen.findByText('Bia DaGerencia')).toBeInTheDocument();
    expect(screen.queryByText('Caio DoSetor')).not.toBeInTheDocument();
  });

  test('quem não delega não vê o campo (registra o próprio deslocamento)', async () => {
    listAlvosMock.mockResolvedValue([]);
    const dialogo = await abrirNovo();

    expect(await within(dialogo).findByLabelText('Origem')).toBeInTheDocument();
    expect(within(dialogo).queryByLabelText('Formador')).not.toBeInTheDocument();
  });
});
