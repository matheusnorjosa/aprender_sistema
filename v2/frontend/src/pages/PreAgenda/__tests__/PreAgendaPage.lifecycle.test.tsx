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
 *  5. 429 — o polling continuava martelando o throttle do operador: agora pausa pelo
 *     Retry-After (usePolling.pausar) e mostra um aviso só.
 *
 * O usePolling é mockado como CAPTOR: guarda o callback e as opções passadas,
 * para (a) asserir o wiring de `immediate` e (b) disparar "ticks" de polling
 * de forma determinística, sem depender de timers reais do intervalo.
 */
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { message } from 'antd';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';

import { TIMING } from '../../../constants/timing';

const { poll, getMeMock, listSolicitacoesMock, getStatusSummaryMock, fetchAPIMock, formadoresLabelMock } = vi.hoisted(() => ({
  formadoresLabelMock: vi.fn(),
  poll: {
    fn: null as null | (() => void | Promise<void>),
    opts: null as null | Record<string, unknown>,
    pausado: false,
    pausar: vi.fn(),
  },
  getMeMock: vi.fn(),
  listSolicitacoesMock: vi.fn(),
  getStatusSummaryMock: vi.fn(),
  fetchAPIMock: vi.fn(),
}));

vi.mock('../../../api/config', async (importOriginal) => {
  const actual = (await importOriginal());
  return { ...actual, fetchAPI: fetchAPIMock };
});
vi.mock('../../../api/availability', () => ({ getMe: getMeMock, getGerencias: vi.fn().mockResolvedValue([]) }));
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
  usePolling: (fn: () => void | Promise<void>, opts: Record<string, unknown>) => {
    poll.fn = fn;
    poll.opts = opts;
    return { pausado: poll.pausado, pausar: poll.pausar };
  },
}));
// Espião sobre a função real: conta quantas vezes a coluna "Formadores" é desenhada.
vi.mock('../../../utils/participants', async (importOriginal) => {
  const real = await importOriginal<typeof import('../../../utils/participants')>();
  formadoresLabelMock.mockImplementation(real.formadoresLabel);
  return { ...real, formadoresLabel: formadoresLabelMock };
});
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
  poll.pausado = false;
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
      void poll.fn?.(); // carga #1 (obsoleta)
    });
    act(() => {
      void poll.fn?.(); // carga #2 (mais recente)
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

  test('5. 429: pausa o polling pelo Retry-After (ou 60 s), sem mensagem de erro', async () => {
    const erro = vi.spyOn(message, 'error');
    listSolicitacoesMock.mockResolvedValue({ results: [row(1, 'Municipio Um')], count: 1 });
    render(<PreAgendaPage />);
    await screen.findAllByText('Municipio Um');

    listSolicitacoesMock.mockRejectedValue(
      Object.assign(new Error('Throttled'), { status: 429, retryAfter: 45 }),
    );
    await act(async () => { await poll.fn?.(); });
    expect(poll.pausar).toHaveBeenLastCalledWith(45_000);

    // Sem Retry-After (ex.: 429 do nginx): 60 s.
    listSolicitacoesMock.mockRejectedValue(Object.assign(new Error('Throttled'), { status: 429 }));
    await act(async () => { await poll.fn?.(); });
    expect(poll.pausar).toHaveBeenLastCalledWith(60_000);

    expect(erro).not.toHaveBeenCalled();
    expect(screen.getAllByText('Municipio Um').length).toBeGreaterThan(0);
    erro.mockRestore();
  });

  test('6. polling a cada 20 s', async () => {
    render(<PreAgendaPage />);
    await waitFor(() => expect(poll.opts).not.toBeNull());
    expect(poll.opts?.intervalMs).toBe(20_000);
  });

  test('7. atualização em segundo plano não mostra carregamento e mantém a lista', async () => {
    listSolicitacoesMock.mockResolvedValue({ results: [row(1, 'Municipio Um')], count: 1 });
    const { container } = render(<PreAgendaPage />);
    await screen.findAllByText('Municipio Um');
    await waitFor(() => expect(container.querySelector('.ant-spin-spinning')).toBeNull());

    listSolicitacoesMock.mockReturnValue(new Promise(() => undefined));
    await act(async () => { void poll.fn?.(); });
    // O Spin do antd liga com um setTimeout: dá tempo de ele aparecer antes de conferir.
    await act(async () => { await new Promise((resolve) => setTimeout(resolve, 50)); });

    expect(container.querySelector('.ant-spin-spinning')).toBeNull();
    expect(screen.getAllByText('Municipio Um').length).toBeGreaterThan(0);
  });

  test('8. atualização em segundo plano com os mesmos dados não redesenha a tabela', async () => {
    listSolicitacoesMock.mockImplementation((f: { flow: string }) =>
      Promise.resolve(f.flow === 'SUPER' ? { results: [row(1, 'Municipio Um')], count: 1 } : { results: [], count: 0 }),
    );
    getStatusSummaryMock.mockImplementation(() => Promise.resolve({ counts: { NONE: 1 }, total: 1 }));
    render(<PreAgendaPage />);
    await screen.findAllByText('Municipio Um');
    await act(async () => { await new Promise((resolve) => setTimeout(resolve, 50)); });
    const desenhosAntes = formadoresLabelMock.mock.calls.length;
    const cargasAntes = listSolicitacoesMock.mock.calls.length;

    await act(async () => { await poll.fn?.(); });

    expect(listSolicitacoesMock.mock.calls.length).toBe(cargasAntes + 2);
    expect(formadoresLabelMock.mock.calls.length).toBe(desenhosAntes);
  });

  test('9. polling pausado mostra UM aviso discreto (role=status)', async () => {
    poll.pausado = true;
    render(<PreAgendaPage />);

    const avisos = await screen.findAllByText('Atualização automática pausada por alguns instantes.');
    expect(avisos).toHaveLength(1);
    expect(avisos[0]?.closest('[role="status"]')).not.toBeNull();
  });

  test('10. 429 na carga pedida pela pessoa (primeira carga): diz que a lista não carregou; some quando carrega', async () => {
    const naoCarregou = /Não foi possível carregar agora/;
    listSolicitacoesMock.mockRejectedValue(Object.assign(new Error('Throttled'), { status: 429 }));
    render(<PreAgendaPage />);

    const aviso = await screen.findByText(naoCarregou);
    expect(aviso.closest('[role="alert"]')).not.toBeNull();
    expect(poll.pausar).toHaveBeenLastCalledWith(60_000);

    // Fim da pausa: o polling busca de novo e a lista chega.
    listSolicitacoesMock.mockResolvedValue({ results: [row(1, 'Municipio Um')], count: 1 });
    await act(async () => { await poll.fn?.(); });
    expect(screen.queryByText(naoCarregou)).not.toBeInTheDocument();
    expect(screen.getAllByText('Municipio Um').length).toBeGreaterThan(0);
  });

  test('11. 429 só na atualização em segundo plano não mostra o aviso de carga que falhou', async () => {
    listSolicitacoesMock.mockResolvedValue({ results: [row(1, 'Municipio Um')], count: 1 });
    render(<PreAgendaPage />);
    await screen.findAllByText('Municipio Um');

    listSolicitacoesMock.mockRejectedValue(Object.assign(new Error('Throttled'), { status: 429 }));
    await act(async () => { await poll.fn?.(); });

    expect(poll.pausar).toHaveBeenLastCalledWith(60_000);
    expect(screen.queryByText(/Não foi possível carregar agora/)).not.toBeInTheDocument();
  });
});
