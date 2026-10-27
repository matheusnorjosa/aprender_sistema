/**
 * GCalDashboardPage — participações no detalhe do evento (S5).
 *
 * O backend manda `email: null` quando o e-mail é o de reserva `<cpf>@placeholder.local` ou
 * leva CPF. O cartão do participante precisa continuar identificando a pessoa pelo nome (ou
 * "Usuario #id"), sem cair em branco.
 */
import { render, screen, fireEvent } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';

const { getEventDetailMock } = vi.hoisted(() => ({ getEventDetailMock: vi.fn() }));

vi.mock('../../../api/gcal', () => ({
  getDashboardMetrics: vi.fn().mockResolvedValue({ counts: {}, recent_errors: [] }),
  listDashboardEvents: vi.fn().mockResolvedValue({
    count: 1,
    results: [
      { id: 7, summary: 'Formação em Sobral', gcal_status: 'PUBLISHED', gcal_last_sync_at: null, gcal_last_error: null },
    ],
  }),
  getDashboardSuccessRate: vi.fn().mockResolvedValue({ published: 0, error: 0, pending: 0, none: 0, rate: 0 }),
  getDashboardTopInsights: vi.fn().mockResolvedValue({ items: [], metric: 'municipios', limit: 5 }),
  getDashboardEventDetail: getEventDetailMock,
  reapplyBatch: vi.fn(),
  resyncBatch: vi.fn(),
  buildDashboardEventsExportUrl: vi.fn(),
}));

import GCalDashboardPage from '../GCalDashboardPage';

// Tela pesada (AntD + tabelas): na CI, cerca de 4x mais lenta que local, o caso passou dos 5 s padrão
// (27/10/2026, 2 vezes seguidas). Só o limite de tempo muda, nenhuma asserção.
vi.setConfig({ testTimeout: 20_000 });

const participacao = (over: Record<string, unknown>) => ({
  usuario: null,
  guest_email: null,
  guest_nome: null,
  email: null,
  role: 'FORMADOR',
  ch_horas: null,
  observacao: null,
  ...over,
});

beforeEach(() => {
  getEventDetailMock.mockResolvedValue({
    id: 7,
    municipio_nome: 'Sobral',
    projeto_nome: 'Projeto',
    tipo_evento_nome: 'Formação',
    inicio: null,
    fim: null,
    usuario_nome: 'Operadora',
    coordenador_nome: null,
    fluxo: 'NAO_SUPER',
    gcal_status: 'PUBLISHED',
    external_event_id: null,
    gcal_last_sync_at: null,
    meet_link: null,
    gcal_payload_hash: null,
    gcal_last_error: null,
    updated_at: null,
    participations: [
      participacao({ usuario: { id: 11, first_name: 'Rita', last_name: 'Souza' } }),
      participacao({ usuario: { id: 12, first_name: '', last_name: '' } }),
    ],
    timeline: [],
  });
});

describe('GCalDashboardPage — participações do evento', () => {
  test('participante com e-mail omitido aparece pelo nome, ou por "Usuario #id"', async () => {
    render(<GCalDashboardPage />);
    fireEvent.click(await screen.findByText('Formação em Sobral'));

    // O Drawer do antd é renderizado em portal, fora do <aside>: a busca é na tela toda.
    expect(await screen.findByText('Participações')).toBeInTheDocument();
    expect(screen.getByText('Rita Souza')).toBeInTheDocument();
    expect(screen.getByText('Usuario #12')).toBeInTheDocument();
  });
});
