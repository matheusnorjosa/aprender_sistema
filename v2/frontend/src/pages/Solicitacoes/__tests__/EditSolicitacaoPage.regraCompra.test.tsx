/**
 * EditSolicitacaoPage — regra da compra nas listas (14/10/2026).
 *
 * A lista de projetos esconde o projeto "em espera" (`com_compra`) e a de municípios segue o
 * projeto escolhido (`com_compra` + `projeto_id`). Quem é isento (superusuário ou a capacidade)
 * recebe tudo do servidor, então a tela manda os filtros sempre.
 */
import { useEffect } from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { beforeEach, describe, expect, test, vi } from 'vitest';

const { getSolicitacaoMock, lookupProjetosMock, lookupMunicipiosWithFiltersMock } = vi.hoisted(() => ({
  getSolicitacaoMock: vi.fn(),
  lookupProjetosMock: vi.fn(),
  lookupMunicipiosWithFiltersMock: vi.fn(),
}));

vi.mock('../../../api/solicitacoes', () => ({
  getSolicitacao: getSolicitacaoMock,
  updateSolicitacao: vi.fn(),
}));
vi.mock('../../../api/lookup', () => ({
  lookupMunicipiosWithFilters: lookupMunicipiosWithFiltersMock,
  lookupProjetos: lookupProjetosMock,
  lookupTiposEvento: vi.fn().mockResolvedValue([]),
}));
vi.mock('../../../components/DateTimeRange', () => ({ default: () => null }));
vi.mock('../../../components/FormadoresPicker', () => ({ default: () => null }));

function MockComboBox({
  placeholder = '',
  lookupFunction,
  onChange,
}: {
  placeholder?: string;
  lookupFunction: (query: string) => Promise<unknown[]>;
  onChange?: (item: unknown) => void;
}) {
  useEffect(() => {
    void lookupFunction('');
  }, [lookupFunction]);
  return (
    <button type="button" onClick={() => onChange?.({ id: 77, label: 'Projeto Novo' })}>
      {placeholder}
    </button>
  );
}
vi.mock('../../../components/ComboBox', () => ({ default: MockComboBox }));

import EditSolicitacaoPage from '../EditSolicitacaoPage';

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/solicitacoes/42/editar']}>
      <Routes>
        <Route path="/solicitacoes/:id/editar" element={<EditSolicitacaoPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('EditSolicitacaoPage — regra da compra', { timeout: 20000 }, () => {
  beforeEach(() => {
    if (!window.matchMedia) {
      Object.defineProperty(window, 'matchMedia', {
        writable: true,
        value: vi.fn().mockImplementation((query: string) => ({
          matches: false,
          media: query,
          onchange: null,
          addListener: vi.fn(),
          removeListener: vi.fn(),
          addEventListener: vi.fn(),
          removeEventListener: vi.fn(),
          dispatchEvent: vi.fn(),
        })),
      });
    }
    vi.clearAllMocks();
    lookupProjetosMock.mockResolvedValue([]);
    lookupMunicipiosWithFiltersMock.mockResolvedValue([]);
    getSolicitacaoMock.mockResolvedValue({
      id: 42,
      municipio: 5,
      municipio_nome: 'Sobral',
      projeto: 10,
      projeto_nome: 'Vidas',
      tipo_evento: 2,
      tipo_evento_nome: 'Formação',
      coordenador_acompanha: false,
      inicio: '2026-10-10T12:00:00Z',
      fim: '2026-10-10T15:00:00Z',
      status: 'aprovado',
      participations: [],
      fluxo: 'NAO_SUPER',
      gcal_status: 'NONE',
    });
  });

  test('projetos com com_compra e municípios pelo projeto escolhido', async () => {
    renderPage();

    await waitFor(() => {
      expect(lookupProjetosMock).toHaveBeenCalledWith('', { com_compra: true });
      expect(lookupMunicipiosWithFiltersMock).toHaveBeenLastCalledWith({ q: '', com_compra: true, projeto_id: 10 });
    });

    // Trocar o projeto recarrega os municípios com o projeto novo.
    fireEvent.click(screen.getByRole('button', { name: 'Busque ou selecione um projeto' }));
    await waitFor(() => {
      expect(lookupMunicipiosWithFiltersMock).toHaveBeenLastCalledWith({ q: '', com_compra: true, projeto_id: 77 });
    });
  });
});
