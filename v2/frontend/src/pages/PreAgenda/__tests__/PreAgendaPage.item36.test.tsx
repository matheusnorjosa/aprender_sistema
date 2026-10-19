/**
 * Pré-agenda — achados do item 36 (19/10/2026, telas de evento).
 *
 * - "Remover do Google" (antes "Cancelar evento", com "Sim, Cancelar Evento" e foco no OK) abre no
 *   Cancelar, cita o evento e diz que a solicitação continua aprovada.
 * - Status do Google em pt-BR (os rótulos de `gcalRowActions`) e, em ERROR, o motivo que o backend
 *   gravou (`gcal_last_error`): antes só a Tag com o código cru (ERROR/NONE/PENDING).
 *
 * Reusa o harness de mocks do PreAgendaPage.publish.test.tsx. Modal.confirm (estático) não monta
 * no jsdom deste projeto: o teste espia a chamada (padrão das telas AdminDAT).
 */
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { Modal } from 'antd';
import { beforeEach, describe, expect, test, vi } from 'vitest';

const { listSolicitacoesMock, getStatusSummaryMock } = vi.hoisted(() => ({
  listSolicitacoesMock: vi.fn(),
  getStatusSummaryMock: vi.fn(),
}));

vi.mock('../../../api/config', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../../api/config')>();
  return { ...actual, fetchAPI: vi.fn().mockResolvedValue({}) };
});
vi.mock('../../../api/availability', () => ({ getMe: vi.fn().mockResolvedValue(null), getGerencias: vi.fn().mockResolvedValue([]) }));
vi.mock('../../../api/solicitacoes', () => ({
  listSolicitacoes: listSolicitacoesMock,
  previewSolicitacao: vi.fn(),
  publishSolicitacao: vi.fn(),
  resyncSolicitacao: vi.fn(),
  cancelSolicitacao: vi.fn(),
}));
vi.mock('../../../api/gcal', () => ({
  getStatusSummary: getStatusSummaryMock,
  reapplyBatch: vi.fn(),
  resyncBatch: vi.fn(),
}));
vi.mock('../../../hooks/useGoogleIntegration', () => ({
  default: () => ({
    status: { connected: true, isExpired: false, googleEmail: 'x@y.br', tokenExpiry: null, expiresInDays: null },
    disconnect: vi.fn(),
    loading: false,
    error: null,
    fetchStatus: vi.fn(),
  }),
}));
vi.mock('../../../hooks/useGoogleGuard', () => ({
  default: () => ({ requireGoogleConnection: () => true, handleGoogleError: () => false, isConnected: true }),
}));
vi.mock('../../../hooks/usePolling', () => ({ usePolling: () => ({ pausado: false, pausar: () => {} }) }));
vi.mock('../../../services/syncChannel', () => ({
  syncChannel: { subscribe: () => () => {}, publish: vi.fn() },
}));
vi.mock('../../../components/google/GoogleIntegrationCard', () => ({
  default: () => <div data-testid="google-card" />,
}));

import PreAgendaPage from '../PreAgendaPage';

const FUTURO = { inicio: '2099-11-05T12:00:00Z', fim: '2099-11-05T15:00:00Z' };

const row = (overrides: Record<string, unknown> = {}) => ({
  id: 1,
  municipio_nome: 'Fortaleza',
  projeto_nome: 'Projeto Teste',
  tipo: 'Formação',
  gcal_status: 'NONE',
  external_event_id: null,
  meet_link: null,
  participations: [],
  ...FUTURO,
  ...overrides,
});

/** SUPER traz `superRows`, NAO_SUPER traz `naoRows` (uma tabela combinada). */
function mockRows(superRows: Array<Record<string, unknown>>, naoRows: Array<Record<string, unknown>> = []) {
  listSolicitacoesMock.mockImplementation((f: { flow: string }) =>
    Promise.resolve(
      f.flow === 'SUPER' ? { results: superRows, count: superRows.length } : { results: naoRows, count: naoRows.length },
    ),
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  listSolicitacoesMock.mockResolvedValue({ results: [], count: 0 });
  getStatusSummaryMock.mockResolvedValue({ counts: {}, total: 0 });
});

describe('PreAgendaPage — status do Google em pt-BR, com o motivo do erro', () => {
  test('ERROR mostra "Erro" e o motivo gravado pelo backend; NONE/PUBLISHED com rótulo, sem o código cru', async () => {
    const motivo = 'Sua conta Google não tem acesso ao calendário da organização. Peça ao Controle o compartilhamento.';
    mockRows([
      row({ id: 1, municipio_nome: 'Crato', gcal_status: 'ERROR', gcal_last_error: motivo }),
      row({ id: 2, municipio_nome: 'Sobral', gcal_status: 'NONE' }),
      row({ id: 3, municipio_nome: 'Iguatu', gcal_status: 'PUBLISHED', external_event_id: 'asv3' }),
    ]);
    render(<PreAgendaPage />);

    const erro = (await screen.findByText('Crato')).closest('tr') as HTMLElement;
    expect(within(erro).getByText('Erro')).toBeInTheDocument();
    expect(within(erro).getByText(motivo)).toBeInTheDocument();
    expect(within(screen.getByText('Sobral').closest('tr') as HTMLElement).getByText('Não publicado')).toBeInTheDocument();
    expect(within(screen.getByText('Iguatu').closest('tr') as HTMLElement).getByText('Publicado')).toBeInTheDocument();
    for (const codigo of ['ERROR', 'NONE', 'PUBLISHED']) {
      expect(screen.queryByText(codigo)).not.toBeInTheDocument();
    }
  });
});

describe('PreAgendaPage — remover do Google começa no Cancelar e cita o evento', () => {
  const semModal = (): { destroy: () => void; update: () => void } => ({ destroy: vi.fn(), update: vi.fn() });
  const EVENTO = '05/11/2099 09:00 · Juazeiro · Projeto Teste';

  test('a confirmação abre no Cancelar, cita o evento e diz que a solicitação continua aprovada', async () => {
    mockRows([row({ id: 9, municipio_nome: 'Juazeiro', gcal_status: 'PUBLISHED', external_event_id: 'asv9' })]);
    render(<PreAgendaPage />);
    await screen.findByText('Juazeiro');
    const confirmacao = vi.spyOn(Modal, 'confirm').mockImplementation(semModal);

    fireEvent.click(screen.getByRole('button', { name: `Remover do Google Agenda: ${EVENTO}` }));

    await waitFor(() => expect(confirmacao).toHaveBeenCalledTimes(1));
    const config = confirmacao.mock.calls[0]?.[0];
    expect(config).toMatchObject({
      autoFocusButton: 'cancel',
      title: `Remover do Google Agenda: ${EVENTO}?`,
      okText: 'Remover do Google',
      cancelText: 'Cancelar',
    });
    const { container } = render(<>{config?.content}</>);
    expect(container.textContent).toMatch(/continua aprovada/);
    expect(container.textContent).not.toMatch(/event_id|meet_link/);
    await act(async () => {});
  });
});

// A lista lê no máximo 100 aprovados por fluxo. Pedia sem ordem (o padrão do servidor é -inicio):
// vinham os 100 mais distantes no futuro e os desta semana sumiam, sem aviso.
describe('PreAgendaPage — os mais próximos primeiro, e aviso quando a lista é cortada', () => {
  const dataDaLinha = (tr: Element): string => tr.querySelector('td:nth-child(2)')?.textContent ?? '';

  test('pede os dois fluxos do mais próximo ao mais distante e intercala as duas listas', async () => {
    mockRows(
      [row({ id: 1, municipio_nome: 'SuperLonge', inicio: '2099-12-20T12:00:00Z', fim: '2099-12-20T15:00:00Z' })],
      [row({ id: 2, municipio_nome: 'NaoSuperPerto', inicio: '2099-01-10T12:00:00Z', fim: '2099-01-10T15:00:00Z' })],
    );
    render(<PreAgendaPage />);
    await screen.findByText('SuperLonge');

    for (const flow of ['SUPER', 'NAO_SUPER']) {
      expect(listSolicitacoesMock).toHaveBeenCalledWith(expect.objectContaining({ flow, ordering: 'proximidade' }));
    }
    const linhas = Array.from(document.querySelectorAll('tr.ant-table-row'));
    expect(linhas.map((tr) => tr.textContent?.includes('NaoSuperPerto'))).toEqual([true, false]);
    expect(dataDaLinha(linhas[0] as Element)).toContain('10/01/2099');
  });

  test('servidor tem mais do que veio: avisa quantos estão na tela e como achar o resto', async () => {
    listSolicitacoesMock.mockImplementation((f: { flow: string }) =>
      Promise.resolve(f.flow === 'SUPER' ? { results: [row({ id: 1, municipio_nome: 'Crato' })], count: 140 } : { results: [], count: 0 }),
    );
    render(<PreAgendaPage />);
    await screen.findByText('Crato');

    const aviso = screen.getByText(/Mostrando 1 de 140 eventos aprovados/);
    expect(aviso.closest('[role="status"]')).not.toBeNull();
    expect(aviso.textContent).toMatch(/filtre por data, gerência ou busca/i);
  });

  test('sem corte, sem aviso', async () => {
    mockRows([row({ id: 1, municipio_nome: 'Crato' })]);
    render(<PreAgendaPage />);
    await screen.findByText('Crato');

    expect(screen.queryByText(/Mostrando \d+ de/)).not.toBeInTheDocument();
  });
});
