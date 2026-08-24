/**
 * #1668 [M12-19] Pré-agenda: ciclo de requisições.
 *
 * Bugs cobertos (todos confirmados no código atual):
 *  1. Carga inicial DUPLA — o efeito de filtro dispara loadData no mount E o
 *     usePolling busca na hora → usePolling deve receber `immediate: false`.
 *  2. Tempestade por tecla — searchTerm/sectorFilter nas deps de loadData +
 *     efeito re-disparando a cada tecla, SEM debounce.
 *  3. Sem latest-wins — setRows grava incondicionalmente; resposta obsoleta
 *     sobrescreve a atual.
 *  4. Contador incoerente — total exibido = count do servidor sobre uma lista
 *     de 1 página (inalcançável). Deve refletir o carregado.
 *  5. Sem backoff em 429 — o polling continua martelando o throttle do operador.
 *
 * O usePolling é mockado como CAPTOR: guarda o callback e as opções passadas,
 * para (a) asserir o wiring de `immediate` e (b) disparar "ticks" de polling
 * de forma determinística, sem depender de timers reais do intervalo.
 */
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';

import { TIMING } from '../../../constants/timing';

const { poll, getMeMock, listSolicitacoesMock, getStatusSummaryMock, fetchAPIMock } = vi.hoisted(() => ({
  poll: { fn: null as null | (() => void), opts: null as null | Record<string, unknown> },
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
// Captor: guarda callback + opções, não executa nada sozinho.
vi.mock('../../../hooks/usePolling', () => ({
  usePolling: (fn: () => void, opts: Record<string, unknown>) => {
    poll.fn = fn;
    poll.opts = opts;
  },
}));
vi.mock('../../../services/syncChannel', () => ({
  syncChannel: { subscribe: () => () => {}, publish: vi.fn() },
}));
vi.mock('../../../components/google/GoogleIntegrationCard', () => ({
  default: () => <div data-testid="google-card" />,
}));

import PreAgendaPage from '../PreAgendaPage';

const row = (id: number, municipio: string) => ({
  id,
  municipio_nome: municipio,
  projeto_nome: 'Projeto',
  tipo: 'Formação',
  gcal_status: 'NONE',
  inicio: '2026-08-10T09:00:00',
  external_event_id: null,
  meet_link: null,
});

beforeEach(() => {
  vi.clearAllMocks();
  poll.fn = null;
  poll.opts = null;
  getMeMock.mockResolvedValue({ setores: ['Controle'], funcoes: [], is_superuser: false });
  listSolicitacoesMock.mockResolvedValue({ results: [], count: 0 });
  getStatusSummaryMock.mockResolvedValue({ counts: {}, total: 0 });
  fetchAPIMock.mockResolvedValue({});
});

afterEach(() => {
  vi.useRealTimers();
});

describe('PreAgendaPage — ciclo de requisições (#1668 / M12-19)', () => {
  test('1. configura usePolling com immediate:false (sem carga inicial dupla)', async () => {
    render(<PreAgendaPage />);
    await waitFor(() => expect(poll.opts).not.toBeNull());
    expect(poll.opts?.immediate).toBe(false);
  });

  test('2. digitar no filtro faz UMA recarga debounced, não uma por tecla', async () => {
    vi.useFakeTimers();
    render(<PreAgendaPage />);
    await vi.advanceTimersByTimeAsync(0); // flush mount (getMe + load inicial)

    const before = listSolicitacoesMock.mock.calls.length;

    const busca = screen.getByPlaceholderText('Buscar por município, projeto...');
    fireEvent.change(busca, { target: { value: 'a' } });
    fireEvent.change(busca, { target: { value: 'ab' } });
    fireEvent.change(busca, { target: { value: 'abc' } });

    await vi.advanceTimersByTimeAsync(TIMING.DEBOUNCE_SEARCH_MS + 10);

    // Uma única recarga = 2 chamadas (fluxo SUPER + NAO_SUPER).
    expect(listSolicitacoesMock.mock.calls.length - before).toBe(2);
  });

  test('3. latest-wins: resposta obsoleta não sobrescreve a mais recente', async () => {
    type Deferred = { resolve: (v: unknown) => void; flow: string };
    const deferreds: Deferred[] = [];
    listSolicitacoesMock.mockImplementation(
      (f: { flow: string }) => new Promise((resolve) => deferreds.push({ resolve, flow: f.flow })),
    );

    render(<PreAgendaPage />);
    // Carga do mount: 2 chamadas (SUPER + NAO_SUPER).
    await waitFor(() => expect(deferreds.length).toBe(2));
    await act(async () => {
      deferreds.forEach((d) => d.resolve({ results: [], count: 0 }));
    });
    deferreds.length = 0;

    // Dois ticks de polling em sequência → duas cargas concorrentes.
    act(() => {
      poll.fn?.(); // carga #1 (obsoleta)
    });
    act(() => {
      poll.fn?.(); // carga #2 (mais recente)
    });
    await waitFor(() => expect(deferreds.length).toBe(4));

    // Resolve a MAIS RECENTE (#2, índices 2 e 3) primeiro.
    await act(async () => {
      deferreds[2].resolve({ results: [row(99, 'FRESH')], count: 1 });
      deferreds[3].resolve({ results: [], count: 0 });
    });
    await screen.findByText('FRESH');

    // A OBSOLETA (#1) chega DEPOIS (fora de ordem) — não pode sobrescrever.
    await act(async () => {
      deferreds[0].resolve({ results: [row(11, 'STALE')], count: 1 });
      deferreds[1].resolve({ results: [], count: 0 });
    });
    await new Promise((r) => setTimeout(r, 30));

    expect(screen.getByText('FRESH')).toBeInTheDocument();
    expect(screen.queryByText('STALE')).not.toBeInTheDocument();
  });

  test('4. contador reflete o carregado, não o count do servidor', async () => {
    listSolicitacoesMock.mockImplementation((f: { flow: string }) =>
      Promise.resolve(
        f.flow === 'SUPER'
          ? { results: [row(1, 'A'), row(2, 'B')], count: 100 }
          : { results: [row(3, 'C')], count: 50 },
      ),
    );

    render(<PreAgendaPage />);

    // 3 linhas carregadas (2 SUPER + 1 NAO_SUPER); o total NÃO pode ser 150.
    await screen.findByText('A');
    await waitFor(() => expect(screen.getByText(/Total: 3\b/)).toBeInTheDocument());
    expect(screen.queryByText(/Total: 150\b/)).not.toBeInTheDocument();
  });

  test('5. backoff em 429: após um 429 o polling pula ticks antes de voltar', async () => {
    render(<PreAgendaPage />);
    await waitFor(() => expect(poll.fn).not.toBeNull());
    // Deixa a carga do mount assentar.
    await waitFor(() => expect(listSolicitacoesMock.mock.calls.length).toBeGreaterThanOrEqual(2));

    // Próxima carga (tick) devolve 429.
    const err = Object.assign(new Error('Throttled'), { status: 429 });
    listSolicitacoesMock.mockRejectedValue(err);
    const afterMount = listSolicitacoesMock.mock.calls.length;

    await act(async () => {
      poll.fn?.(); // tick que recebe 429 → aciona backoff
    });
    await waitFor(() => expect(listSolicitacoesMock.mock.calls.length).toBe(afterMount + 2));
    const after429 = listSolicitacoesMock.mock.calls.length;

    // Volta a responder OK, mas os próximos ticks devem ser PULADOS (backoff).
    listSolicitacoesMock.mockResolvedValue({ results: [], count: 0 });
    act(() => {
      poll.fn?.();
    });
    act(() => {
      poll.fn?.();
    });
    await new Promise((r) => setTimeout(r, 20));
    expect(listSolicitacoesMock.mock.calls.length).toBe(after429); // nenhum request novo

    // Depois de esgotar o backoff, volta a buscar.
    act(() => {
      poll.fn?.();
    });
    act(() => {
      poll.fn?.();
    });
    await waitFor(() => expect(listSolicitacoesMock.mock.calls.length).toBeGreaterThan(after429));
  });
});
