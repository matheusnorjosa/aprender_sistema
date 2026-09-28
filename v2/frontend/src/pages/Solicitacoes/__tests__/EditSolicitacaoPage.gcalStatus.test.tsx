/**
 * EditSolicitacaoPage — rótulo "GCal:" no cabeçalho (#1656, alinhamento do GCalStatus).
 *
 * O backend nunca manda 'NOT_SYNCED': "não sincronizada" é 'NONE'
 * (`models/solicitacao.py`). Comparar com 'NOT_SYNCED' nunca casava, então o
 * cabeçalho exibia "GCal: NONE" para toda solicitação não publicada.
 *
 * Os campos do formulário (ComboBox/DateTimeRange/FormadoresPicker) são stubs:
 * o teste cobre só o cabeçalho.
 */
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { beforeEach, describe, expect, test, vi } from 'vitest';

const { getSolicitacaoMock } = vi.hoisted(() => ({ getSolicitacaoMock: vi.fn() }));

vi.mock('../../../api/solicitacoes', () => ({
  getSolicitacao: getSolicitacaoMock,
  updateSolicitacao: vi.fn(),
}));
vi.mock('../../../api/lookup', () => ({
  lookupMunicipios: vi.fn().mockResolvedValue([]),
  lookupProjetos: vi.fn().mockResolvedValue([]),
  lookupTiposEvento: vi.fn().mockResolvedValue([]),
}));
vi.mock('../../../components/ComboBox', () => ({ default: () => null }));
vi.mock('../../../components/DateTimeRange', () => ({ default: () => null }));
vi.mock('../../../components/FormadoresPicker', () => ({ default: () => null }));

import EditSolicitacaoPage from '../EditSolicitacaoPage';
import type { GCalStatus, Solicitacao } from '../../../types';

function makeSolic(gcal_status: GCalStatus): Solicitacao {
  return {
    id: 42,
    usuario: 1,
    usuario_username: 'coord1',
    municipio: 5,
    municipio_nome: 'Sobral',
    projeto: 10,
    projeto_nome: 'Vidas',
    tipo_evento: 2,
    tipo_evento_nome: 'Formação',
    tipo: null,
    encontro: null,
    segmento: null,
    coordenador_acompanha: false,
    coordenador: null,
    coordenador_username: null,
    coordenador_nome: null,
    inicio: '2026-10-10T12:00:00Z',
    fim: '2026-10-10T15:00:00Z',
    status: 'aprovado',
    observacoes: null,
    local: null,
    is_online: false,
    external_event_id: null,
    created_at: '2026-09-01T12:00:00Z',
    updated_at: '2026-09-01T12:00:00Z',
    participations: [],
    fluxo: 'NAO_SUPER',
    gcal_status,
    gcal_last_sync_at: null,
    gcal_last_error: null,
    meet_link: null,
  };
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/solicitacoes/42/editar']}>
      <Routes>
        <Route path="/solicitacoes/:id/editar" element={<EditSolicitacaoPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('EditSolicitacaoPage — rótulo GCal do cabeçalho', () => {
  beforeEach(() => {
    getSolicitacaoMock.mockReset();
  });

  test("gcal_status 'NONE' (não sincronizada) não exibe o bloco GCal", async () => {
    getSolicitacaoMock.mockResolvedValue(makeSolic('NONE'));
    renderPage();

    expect(await screen.findByText('Editar Solicitação #42')).toBeInTheDocument();
    expect(screen.queryByText(/GCal:/)).not.toBeInTheDocument();
  });

  test("gcal_status 'ERROR' exibe o bloco GCal com o status", async () => {
    getSolicitacaoMock.mockResolvedValue(makeSolic('ERROR'));
    renderPage();

    expect(await screen.findByText('Editar Solicitação #42')).toBeInTheDocument();
    expect(screen.getByText(/GCal:/)).toBeInTheDocument();
    expect(screen.getByText('ERROR')).toBeInTheDocument();
  });
});
