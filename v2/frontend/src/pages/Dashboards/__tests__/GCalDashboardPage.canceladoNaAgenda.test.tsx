/**
 * GCalDashboardPage — evento cancelado na agenda (CON-08 B, revisão da rodada 5).
 *
 * A linha cancelada na agenda segue `gcal_status=PUBLISHED` (o evento está no Google, com "(CANCELADO) " no
 * título). O painel não a chama de "Publicado": mostra a mesma etiqueta das outras telas e não oferece Atualizar
 * nem Reenviar, que o servidor recusa nessa linha.
 */
import { render, screen, fireEvent, within } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';

const { listEventsMock, getEventDetailMock } = vi.hoisted(() => ({
  listEventsMock: vi.fn(),
  getEventDetailMock: vi.fn(),
}));

vi.mock('../../../api/gcal', () => ({
  getDashboardMetrics: vi.fn().mockResolvedValue({ counts: {}, recent_errors: [] }),
  listDashboardEvents: listEventsMock,
  getDashboardSuccessRate: vi.fn().mockResolvedValue({ published: 0, error: 0, pending: 0, none: 0, rate: 0 }),
  getDashboardTopInsights: vi.fn().mockResolvedValue({ items: [], metric: 'municipios', limit: 5 }),
  getDashboardEventDetail: getEventDetailMock,
  reapplyBatch: vi.fn(),
  resyncBatch: vi.fn(),
  buildDashboardEventsExportUrl: vi.fn(),
}));

import GCalDashboardPage from '../GCalDashboardPage';

const evento = (over: Record<string, unknown> = {}) => ({
  id: 7,
  summary: 'Formação em Sobral',
  gcal_status: 'PUBLISHED',
  gcal_last_sync_at: null,
  gcal_last_error: null,
  cancelado_na_agenda: true,
  ...over,
});

const detalhe = (over: Record<string, unknown> = {}) => ({
  id: 7,
  municipio_nome: 'Sobral',
  projeto_nome: 'Projeto',
  tipo_evento_nome: 'Presencial',
  inicio: null,
  fim: null,
  usuario_nome: 'Operadora',
  coordenador_nome: null,
  fluxo: 'NAO_SUPER',
  gcal_status: 'PUBLISHED',
  external_event_id: 'abc123',
  gcal_last_sync_at: null,
  meet_link: null,
  gcal_last_error: null,
  cancelado_na_agenda: true,
  updated_at: null,
  participations: [],
  timeline: [],
  ...over,
});

function listar(...eventos: Array<Record<string, unknown>>): void {
  listEventsMock.mockResolvedValue({ count: eventos.length, results: eventos });
}

async function abrirDetalhe(): Promise<HTMLElement> {
  render(<GCalDashboardPage />);
  fireEvent.click(await screen.findByText('Formação em Sobral'));
  await screen.findByText('Código no Google');
  return screen.getByRole('dialog'); // o Drawer vai para o body, fora da <aside> da página
}

beforeEach(() => {
  vi.clearAllMocks();
  listar(evento());
  getEventDetailMock.mockResolvedValue(detalhe());
});

describe('GCalDashboardPage — evento cancelado na agenda', { timeout: 20000 }, () => {
  test('a lista mostra "Cancelado na agenda", não "Publicado"; a linha sem a marca segue "Publicado"', async () => {
    listar(evento(), evento({ id: 8, summary: 'Formação em Crato', cancelado_na_agenda: false }));
    render(<GCalDashboardPage />);

    const sobral = (await screen.findByText('Formação em Sobral')).closest('tr') as HTMLElement;
    expect(within(sobral).getByText('Cancelado na agenda')).toBeInTheDocument();
    expect(within(sobral).queryByText('Publicado')).not.toBeInTheDocument();
    const crato = screen.getByText('Formação em Crato').closest('tr') as HTMLElement;
    expect(within(crato).getByText('Publicado')).toBeInTheDocument();
  });

  test.each([
    ['PENDING', 'Cancelando…'],
    ['ERROR', 'Erro ao cancelar'],
  ])('na lista, %s marcado: "%s"', async (gcal_status, etiqueta) => {
    listar(evento({ gcal_status }));
    render(<GCalDashboardPage />);

    const linha = (await screen.findByText('Formação em Sobral')).closest('tr') as HTMLElement;
    expect(within(linha).getByText(etiqueta)).toBeInTheDocument();
  });

  test('o detalhe mostra a etiqueta e não oferece Atualizar no Google nem Reenviar', async () => {
    const painel = await abrirDetalhe();

    expect(within(painel).getByText('Cancelado na agenda')).toBeInTheDocument();
    expect(within(painel).queryByText('Publicado')).not.toBeInTheDocument();
    expect(within(painel).getByRole('button', { name: /Atualizar no Google/ })).toBeDisabled();
    expect(within(painel).getByRole('button', { name: /Reenviar/ })).toBeDisabled();
  });

  test('sem a marca, o detalhe segue "Publicado" com Atualizar e Reenviar', async () => {
    listar(evento({ cancelado_na_agenda: false }));
    getEventDetailMock.mockResolvedValue(detalhe({ cancelado_na_agenda: false }));
    const painel = await abrirDetalhe();

    expect(within(painel).getByText('Publicado')).toBeInTheDocument();
    expect(within(painel).getByRole('button', { name: /Atualizar no Google/ })).toBeEnabled();
    expect(within(painel).getByRole('button', { name: /Reenviar/ })).toBeEnabled();
  });

  test('a linha do tempo diz quando o evento sumiu do Google depois de cancelado (resultado nao_achado)', async () => {
    getEventDetailMock.mockResolvedValue(
      detalhe({
        timeline: [
          {
            id: 9,
            action: 'CANCELAR_NA_AGENDA',
            usuario_nome: 'Sistema',
            created_at: '2026-11-24T12:00:00+00:00',
            details: { solicitacao_id: 7, resultado: 'nao_achado' },
          },
        ],
      }),
    );
    await abrirDetalhe();

    expect(screen.getByText('Cancelado na agenda (o evento não foi achado no Google)')).toBeInTheDocument();
    expect(screen.queryByText('Cancelado na agenda (título marcado)')).not.toBeInTheDocument();
  });
});
