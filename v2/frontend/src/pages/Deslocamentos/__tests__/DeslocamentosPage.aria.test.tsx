/**
 * #1742 — a11y: botões só-ícone Editar/Excluir da tabela de Deslocamentos.
 *
 * Fix sob teste (DeslocamentosPage.tsx, coluna "Ações"):
 *   os botões só-ícone ganharam aria-label="Editar deslocamento" e
 *   aria-label="Excluir deslocamento".
 *
 * Prova do RED (por que falharia SEM o fix):
 *   um <Button icon={<EditOutlined/>} /> sem texto e sem aria-label não expõe
 *   accessible name algum — `getByRole('button', { name: /Editar deslocamento/i })`
 *   não encontraria nada (leitor de tela anuncia "botão" sem rótulo). Com o
 *   aria-label, o botão passa a ter accessible name e a query o localiza.
 */

import { render, screen } from '@testing-library/react';
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

const UMA_LINHA = {
  count: 1,
  next: null,
  previous: null,
  results: [
    {
      id: 1,
      usuario: 1,
      usuario_nome: 'Fulano de Tal',
      origem: 'Fortaleza',
      destino: 'Sobral',
      start_date: '2026-01-01',
      end_date: '2026-01-02',
      observacao: 'ida e volta',
    },
  ],
};

function renderPage() {
  return render(
    <MemoryRouter>
      <DeslocamentosPage />
    </MemoryRouter>
  );
}

describe('DeslocamentosPage — aria-label dos botões de ação (#1742)', () => {
  beforeEach(() => {
    getMeMock.mockReset();
    listDeslocamentosMock.mockReset();
    listFormadoresMock.mockReset();
    getMeMock.mockResolvedValue({ id: 1, username: 'coord', groups: ['Coordenador'] });
    listDeslocamentosMock.mockResolvedValue(UMA_LINHA);
    listFormadoresMock.mockResolvedValue([]);
  });

  test('botões só-ícone Editar/Excluir expõem accessible name', async () => {
    renderPage();

    // Aguarda a linha renderizar na tabela (célula usuario_nome).
    await screen.findByText('Fulano de Tal', undefined, { timeout: 8000 });

    // findAllByRole é robusto a eventual duplicação de DOM da coluna fixa do antd.
    const editar = await screen.findAllByRole('button', {
      name: /Editar deslocamento/i,
    });
    const excluir = await screen.findAllByRole('button', {
      name: /Excluir deslocamento/i,
    });

    expect(editar.length).toBeGreaterThanOrEqual(1);
    expect(excluir.length).toBeGreaterThanOrEqual(1);

    // O accessible name é exatamente o esperado (não só um "match parcial").
    expect(editar[0]).toHaveAccessibleName('Editar deslocamento');
    expect(excluir[0]).toHaveAccessibleName('Excluir deslocamento');
  }, 20000);
});
