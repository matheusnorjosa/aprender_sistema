/**
 * #1629 [M12-19] Pré-agenda — publicação: resíduos do fix da #1750.
 *
 *  a) 202-como-sucesso: o backend SEMPRE enfileira (202 Accepted) e sincroniza
 *     com o Google Calendar de forma assíncrona. A UI não pode anunciar
 *     "publicado com sucesso" — deve sinalizar o enfileiramento.
 *  b) PENDING-republish: com a publicação já em voo (PENDING), o botão de
 *     publicar deve ficar disabled para não reenfileirar por cima.
 *
 * Reusa o harness de mocks do PreAgendaPage.lifecycle.test.tsx; aqui o
 * usePolling é um no-op (não precisamos de ticks) e o publishSolicitacao é um
 * mock nomeado para controlar o retorno 202.
 */
// antd v5 static APIs (Modal.confirm/message) usam o render legado, removido no
// React 19. O app aplica este patch oficial no entry (main.tsx); o setup do
// vitest não — sem ele o Modal.confirm não monta no ambiente de teste.
import '@ant-design/v5-patch-for-react-19';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { message } from 'antd';

const { getMeMock, listSolicitacoesMock, getStatusSummaryMock, fetchAPIMock, publishSolicitacaoMock } =
  vi.hoisted(() => ({
    getMeMock: vi.fn(),
    listSolicitacoesMock: vi.fn(),
    getStatusSummaryMock: vi.fn(),
    fetchAPIMock: vi.fn(),
    publishSolicitacaoMock: vi.fn(),
  }));

vi.mock('../../../api/config', async (importOriginal) => {
  const actual = (await importOriginal()) as Record<string, unknown>;
  return { ...actual, fetchAPI: fetchAPIMock };
});
vi.mock('../../../api/availability', () => ({ getMe: getMeMock }));
vi.mock('../../../api/solicitacoes', () => ({
  listSolicitacoes: listSolicitacoesMock,
  previewSolicitacao: vi.fn(),
  publishSolicitacao: publishSolicitacaoMock,
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
vi.mock('../../../hooks/usePolling', () => ({ usePolling: () => {} }));
vi.mock('../../../services/syncChannel', () => ({
  syncChannel: { subscribe: () => () => {}, publish: vi.fn() },
}));
vi.mock('../../../components/google/GoogleIntegrationCard', () => ({
  default: () => <div data-testid="google-card" />,
}));

import PreAgendaPage from '../PreAgendaPage';

const row = (overrides: Record<string, unknown> = {}) => ({
  id: 1,
  municipio_nome: 'Fortaleza',
  projeto_nome: 'Projeto',
  tipo: 'Formação',
  gcal_status: 'NONE',
  inicio: '2026-08-10T09:00:00',
  external_event_id: null,
  meet_link: null,
  ...overrides,
});

// SUPER traz as linhas; NAO_SUPER vazio (uma tabela combinada).
function mockRows(rows: Array<Record<string, unknown>>) {
  listSolicitacoesMock.mockImplementation((f: { flow: string }) =>
    Promise.resolve(f.flow === 'SUPER' ? { results: rows, count: rows.length } : { results: [], count: 0 }),
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  getMeMock.mockResolvedValue({ setores: ['Controle'], funcoes: [], is_superuser: false });
  listSolicitacoesMock.mockResolvedValue({ results: [], count: 0 });
  getStatusSummaryMock.mockResolvedValue({ counts: {}, total: 0 });
  fetchAPIMock.mockResolvedValue({});
});

describe('PreAgendaPage — publicação (M12-19 / #1629)', () => {
  test('publicar NÃO anuncia sucesso definitivo (backend enfileira, 202)', async () => {
    mockRows([row({ id: 10, municipio_nome: 'Sobral', gcal_status: 'NONE' })]);
    publishSolicitacaoMock.mockResolvedValue({ detail: 'enfileirada', task_id: 't1', solicitacao_id: 10 });
    const successSpy = vi.spyOn(message, 'success');
    const infoSpy = vi.spyOn(message, 'info');

    render(<PreAgendaPage />);
    const publishBtn = await screen.findByLabelText('Publicar evento no Google Calendar');
    fireEvent.click(publishBtn);

    // Modal.confirm → confirmar em "Publicar" (mount assíncrono do portal antd).
    const okBtn = await screen.findByRole('button', { name: 'Publicar' }, { timeout: 3000 });
    fireEvent.click(okBtn);

    await waitFor(() => expect(publishSolicitacaoMock).toHaveBeenCalledWith(10, { dry_run: false }));
    // Sinaliza enfileiramento (info), nunca "publicado com sucesso".
    await waitFor(() => expect(infoSpy).toHaveBeenCalled());
    expect(successSpy).not.toHaveBeenCalledWith('Evento publicado com sucesso!');
  });

  test('botão publicar fica disabled quando gcal_status é PENDING', async () => {
    mockRows([row({ id: 20, municipio_nome: 'Sobral', gcal_status: 'PENDING' })]);
    render(<PreAgendaPage />);
    await screen.findByText('Sobral');
    expect(screen.getByLabelText('Publicar evento no Google Calendar')).toBeDisabled();
  });

  test('botão publicar fica habilitado quando gcal_status é NONE', async () => {
    mockRows([row({ id: 30, municipio_nome: 'Caucaia', gcal_status: 'NONE' })]);
    render(<PreAgendaPage />);
    await screen.findByText('Caucaia');
    expect(screen.getByLabelText('Publicar evento no Google Calendar')).not.toBeDisabled();
  });
});
