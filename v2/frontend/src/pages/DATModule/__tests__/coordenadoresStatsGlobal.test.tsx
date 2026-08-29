/**
 * Coordenadores KPIs — escopo global, não da página. A lista é paginada (pageSize 15), mas
 * os cards de resumo (Ativos, Áreas, Média de Projetos) eram derivados só da PÁGINA atual,
 * enquanto "Total" usava o count global — inclusive o % de Ativos era ativos-da-página /
 * total-global (denominadores inconsistentes). O fix busca a lista completa (entidade pequena)
 * só para os KPIs.
 *
 * RED no código antigo: com a página trazendo 2 (ambos ativos), o card "Ativos" mostrava 2,
 * não o total global de 3 ativos.
 */
import { describe, expect, test, vi, beforeEach } from 'vitest';
import { render, screen, within, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';

const { ALL } = vi.hoisted(() => ({
  ALL: [
    { id: 1, nome: 'Ana', email: 'a@x.com', telefone: '', area: 'DAT', cargo: '', ativo: true, foto_url: null, total_municipios: 1, total_projetos: 4, total_formacoes: 0 },
    { id: 2, nome: 'Bruno', email: 'b@x.com', telefone: '', area: 'DAT', cargo: '', ativo: true, foto_url: null, total_municipios: 1, total_projetos: 4, total_formacoes: 0 },
    { id: 3, nome: 'Carla', email: 'c@x.com', telefone: '', area: 'Pedagógico', cargo: '', ativo: true, foto_url: null, total_municipios: 1, total_projetos: 2, total_formacoes: 0 },
    { id: 4, nome: 'Davi', email: 'd@x.com', telefone: '', area: 'Logística', cargo: '', ativo: false, foto_url: null, total_municipios: 0, total_projetos: 0, total_formacoes: 0 },
    { id: 5, nome: 'Eva', email: 'e@x.com', telefone: '', area: null, cargo: '', ativo: false, foto_url: null, total_municipios: 0, total_projetos: 0, total_formacoes: 0 },
  ],
}));

vi.mock('../../../api/datModule', () => ({
  // A busca de STATS pede a lista completa (page_size grande); a lista paginada pede 15.
  listCoordenadoresDAT: vi.fn((params?: { page_size?: number }) => {
    if (params?.page_size && params.page_size >= 100) {
      return Promise.resolve({ results: ALL, count: ALL.length, next: null, previous: null });
    }
    return Promise.resolve({ results: ALL.slice(0, 2), count: ALL.length, next: null, previous: null });
  }),
  createCoordenadorDAT: vi.fn(),
  updateCoordenadorDAT: vi.fn(),
  deleteCoordenadorDAT: vi.fn(),
  getCoordenadorAlocacoes: vi.fn().mockResolvedValue([]),
  getAreasOptions: vi.fn().mockResolvedValue([]),
  getProjetosOptions: vi.fn().mockResolvedValue([]),
  getMunicipiosOptions: vi.fn().mockResolvedValue([]),
}));

import CoordenadoresPage from '../CoordenadoresPage';

describe('Coordenadores: KPIs refletem o total global, não a página', () => {
  beforeEach(() => vi.clearAllMocks());

  test('o card "Ativos" mostra 3 (global), não 2 (primeira página)', async () => {
    render(
      <MemoryRouter>
        <CoordenadoresPage />
      </MemoryRouter>,
    );
    await screen.findByText('Ativos', {}, { timeout: 15000 });
    await waitFor(
      () => {
        const card = screen.getByText('Ativos').closest('.ant-card') as HTMLElement;
        expect(within(card).getByText('3')).toBeInTheDocument();
      },
      { timeout: 10000 },
    );
  }, 25000);
});
