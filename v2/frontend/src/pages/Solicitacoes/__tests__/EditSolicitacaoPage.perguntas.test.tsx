/**
 * EditSolicitacaoPage — respostas de "acompanha?" e "pretende avaliar o formador?" (05/10/2026).
 *
 * A edição mostra o coordenador responsável e as duas respostas gravadas, deixa trocá-las e
 * envia o que mudou. Evento antigo sem resposta de avaliar mostra "Não informado" e salva
 * sem obrigar a responder.
 */
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { beforeEach, describe, expect, test, vi } from 'vitest';

const { getSolicitacaoMock, updateSolicitacaoMock } = vi.hoisted(() => ({
  getSolicitacaoMock: vi.fn(),
  updateSolicitacaoMock: vi.fn(),
}));

vi.mock('../../../api/solicitacoes', () => ({
  getSolicitacao: getSolicitacaoMock,
  updateSolicitacao: updateSolicitacaoMock,
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
import type { Solicitacao } from '../../../types';

function makeSolic(extra: Partial<Solicitacao> = {}): Solicitacao {
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
    coordenador: 1,
    coordenador_username: 'coord1',
    coordenador_nome: 'Ana Coordenadora',
    pretende_avaliar_formador: true,
    formador_avaliado: 99,
    formador_avaliado_nome: 'Bruno Formador',
    avaliaveis_ids: [99],
    projeto_pergunta_avaliar_formador: true,
    inicio: '2026-10-10T12:00:00Z',
    fim: '2026-10-10T15:00:00Z',
    status: 'aprovado',
    observacoes: null,
    local: null,
    is_online: false,
    external_event_id: null,
    created_at: '2026-09-01T12:00:00Z',
    updated_at: '2026-09-01T12:00:00Z',
    participations: [
      {
        usuario: { id: 99, username: 'bruno', first_name: 'Bruno', last_name: 'Formador', email: 'b@example.invalid' },
        guest_email: null,
        guest_nome: null,
        email: 'b@example.invalid',
        role: 'FORMADOR',
        ch_horas: null,
        observacao: null,
      },
    ] as unknown as Solicitacao['participations'],
    fluxo: 'NAO_SUPER',
    gcal_status: 'NONE',
    gcal_last_sync_at: null,
    gcal_last_error: null,
    meet_link: null,
    ...extra,
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

const ACOMPANHA = /O coordenador responsável vai acompanhar o evento\?/;
const AVALIAR = /Você pretende avaliar o formador nesse evento\?/;

describe('EditSolicitacaoPage — responsável e perguntas', () => {
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
    getSolicitacaoMock.mockReset();
    updateSolicitacaoMock.mockReset();
    updateSolicitacaoMock.mockResolvedValue({});
  });

  test('mostra o responsável e as respostas gravadas', async () => {
    getSolicitacaoMock.mockResolvedValue(makeSolic());
    renderPage();
    expect(await screen.findByText('Ana Coordenadora')).toBeInTheDocument();
    expect(within(screen.getByRole('radiogroup', { name: ACOMPANHA })).getByLabelText('Não')).toBeChecked();
    expect(within(screen.getByRole('radiogroup', { name: AVALIAR })).getByLabelText('Sim')).toBeChecked();
    expect(screen.getByText('Bruno Formador', { selector: '.ant-select-selection-item' })).toBeInTheDocument();
  });

  test('trocar a resposta de acompanhar envia o valor novo', async () => {
    getSolicitacaoMock.mockResolvedValue(makeSolic());
    renderPage();
    await screen.findByText('Ana Coordenadora');
    fireEvent.click(within(screen.getByRole('radiogroup', { name: ACOMPANHA })).getByLabelText('Sim'));
    fireEvent.click(screen.getByRole('button', { name: /Salvar Alterações/ }));
    await waitFor(() => expect(updateSolicitacaoMock).toHaveBeenCalled());
    const payload = updateSolicitacaoMock.mock.calls[0][1];
    expect(payload.coordenador_acompanha).toBe(true);
    expect(payload.pretende_avaliar_formador).toBe(true);
    expect(payload.formador_avaliado).toBe(99);
  });

  test('evento antigo sem resposta de avaliar: "Não informado" e salva sem obrigar', async () => {
    getSolicitacaoMock.mockResolvedValue(makeSolic({ pretende_avaliar_formador: null, formador_avaliado: null }));
    renderPage();
    await screen.findByText('Ana Coordenadora');
    expect(screen.getByText('Não informado')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Salvar Alterações/ }));
    await waitFor(() => expect(updateSolicitacaoMock).toHaveBeenCalled());
    expect(updateSolicitacaoMock.mock.calls[0][1].pretende_avaliar_formador).toBeNull();
  });

  test('gerência do projeto que não pergunta: a pergunta não aparece e não vai resposta', async () => {
    getSolicitacaoMock.mockResolvedValue(
      makeSolic({ projeto_pergunta_avaliar_formador: false, pretende_avaliar_formador: null, formador_avaliado: null })
    );
    renderPage();
    await screen.findByText('Ana Coordenadora');
    expect(screen.queryByRole('radiogroup', { name: AVALIAR })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Salvar Alterações/ }));
    await waitFor(() => expect(updateSolicitacaoMock).toHaveBeenCalled());
    expect(updateSolicitacaoMock.mock.calls[0][1].pretende_avaliar_formador).toBeNull();
    expect(updateSolicitacaoMock.mock.calls[0][1].formador_avaliado).toBeNull();
  });
});
