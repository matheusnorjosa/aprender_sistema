/**
 * #1629 [M12-19] Pré-agenda — publicação: botão bloqueado em PENDING.
 *
 * (b) PENDING-republish: com a publicação já em voo (PENDING), o botão de
 *     publicar deve ficar disabled para não reenfileirar por cima. Antes só
 *     bloqueava em PUBLISHED.
 *
 * O resíduo (a) — não anunciar "publicado com sucesso" num retorno 202
 * (enfileiramento assíncrono) — é uma troca de copy no handler (message.info
 * em vez de message.success). Não há teste de UI para ele porque o fluxo passa
 * por Modal.confirm (API estática do antd v5), que não monta de forma confiável
 * no ambiente de teste sob React 19 (nenhum teste do projeto dirige modais).
 *
 * Reusa o harness de mocks do PreAgendaPage.lifecycle.test.tsx.
 */
import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';

const { getMeMock, listSolicitacoesMock, getStatusSummaryMock, fetchAPIMock } = vi.hoisted(() => ({
  getMeMock: vi.fn(),
  listSolicitacoesMock: vi.fn(),
  getStatusSummaryMock: vi.fn(),
  fetchAPIMock: vi.fn(),
}));

vi.mock('../../../api/config', async (importOriginal) => {
  const actual = (await importOriginal());
  return { ...actual, fetchAPI: fetchAPIMock };
});
vi.mock('../../../api/availability', () => ({ getMe: getMeMock }));
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
