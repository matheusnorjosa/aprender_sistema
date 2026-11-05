/**
 * GCalDashboardPage — textos para quem opera, sem dado técnico na tela (B#18).
 *
 * A linha do tempo diz o que aconteceu em frase (não o código da ação nem o JSON do registro,
 * que leva ip_address e task_id de quem operou); o papel do participante sai em português; os
 * rótulos técnicos (Reapply, Resync, Event ID, Top 5, Payload Hash) saem; e o aviso de erro de
 * carga traz a mensagem do servidor.
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { message } from 'antd';
import { beforeEach, describe, expect, test, vi } from 'vitest';

const { getEventDetailMock, getMetricsMock } = vi.hoisted(() => ({
  getEventDetailMock: vi.fn(),
  getMetricsMock: vi.fn(),
}));

vi.mock('../../../api/gcal', () => ({
  getDashboardMetrics: getMetricsMock,
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

const log = (over: Record<string, unknown>) => ({
  id: 1,
  usuario_nome: 'Operadora',
  created_at: '2026-11-03T12:00:00+00:00',
  ...over,
});

beforeEach(() => {
  getMetricsMock.mockReset().mockResolvedValue({ counts: {}, recent_errors: [] });
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
    external_event_id: 'abc123',
    gcal_last_sync_at: null,
    meet_link: null,
    gcal_last_error: null,
    updated_at: null,
    participations: [
      participacao({ usuario: { id: 11, first_name: 'Rita', last_name: 'Souza' }, role: 'FORMADOR' }),
      participacao({ usuario: { id: 12, first_name: 'Caio', last_name: 'Lima' }, role: 'COORD_ACOMPANHA' }),
    ],
    timeline: [
      log({
        id: 2,
        action: 'PUBLISH_GCAL_REQUESTED',
        details: { solicitacao_id: 7, ip_address: '10.0.0.9', task_id: 'tarefa-xyz' },
      }),
      log({ id: 3, action: 'RESYNC_GCAL_REQUESTED', details: { solicitacao_id: 7 } }),
    ],
  });
});

async function abrirDetalhe(): Promise<void> {
  render(<GCalDashboardPage />);
  fireEvent.click(await screen.findByText('Formação em Sobral'));
  await screen.findByText('Participações');
}

describe('GCalDashboardPage — textos sem dado técnico', { timeout: 20000 }, () => {
  test('a linha do tempo diz o que aconteceu, sem o código da ação nem o JSON do registro', async () => {
    await abrirDetalhe();

    expect(screen.getByText('Publicação pedida')).toBeInTheDocument();
    expect(screen.getByText('Reenvio pedido')).toBeInTheDocument();
    expect(screen.queryByText('PUBLISH_GCAL_REQUESTED')).not.toBeInTheDocument();
    expect(screen.queryByText('RESYNC_GCAL_REQUESTED')).not.toBeInTheDocument();
    expect(screen.queryByText(/10\.0\.0\.9/)).not.toBeInTheDocument();
    expect(screen.queryByText(/tarefa-xyz/)).not.toBeInTheDocument();
  });

  test('o papel do participante sai em português', async () => {
    await abrirDetalhe();

    expect(screen.getByText('Formador')).toBeInTheDocument();
    expect(screen.getByText('Coordenador extra')).toBeInTheDocument();
    expect(screen.queryByText('COORD_ACOMPANHA')).not.toBeInTheDocument();
    expect(screen.queryByText('FORMADOR')).not.toBeInTheDocument();
  });

  test('sem rótulos técnicos: Reapply, Resync, Event ID, Top 5 e Payload Hash', async () => {
    await abrirDetalhe();

    expect(screen.getByText('Os 5 municípios com mais eventos')).toBeInTheDocument();
    expect(screen.queryByText(/Top 5/)).not.toBeInTheDocument();
    expect(screen.getByText('Código no Google')).toBeInTheDocument();
    expect(screen.queryByText('Event ID')).not.toBeInTheDocument();
    expect(screen.queryByText('Payload Hash')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Atualizar no Google/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Reenviar/ })).toBeInTheDocument();
    expect(screen.queryByText('Reapply')).not.toBeInTheDocument();
    expect(screen.queryByText('Resync')).not.toBeInTheDocument();
  });

  test('o aviso de erro de carga traz a mensagem do servidor', async () => {
    // O message estático do antd não chega ao DOM do jsdom: o aviso é conferido pela chamada.
    const erro = vi.spyOn(message, 'error').mockImplementation(() => (() => undefined) as never);
    getMetricsMock.mockReset().mockRejectedValue(new Error('Você não tem permissão para ver este painel.'));
    render(<GCalDashboardPage />);

    await waitFor(() =>
      expect(erro).toHaveBeenCalledWith(
        'Erro ao carregar métricas do painel: Você não tem permissão para ver este painel.',
      ),
    );
    erro.mockRestore();
  });
});
