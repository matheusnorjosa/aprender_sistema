/**
 * useMonthlyQuery — atualização automática da Grade Mensal (liberação 2026-10).
 *
 * Antes: a cada tick (5 s) o hook ligava `loading`, a página desmontava as duas grades e
 * mostrava "Carregando..." (piscava), e o mount buscava duas vezes. Agora só a primeira
 * carga (ou troca de filtro) mostra carregamento; o tick (30 s) atualiza em segundo plano.
 *
 * O usePolling é o REAL, com relógio falso.
 */
import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';

const { getMonthlyAvailabilityMock } = vi.hoisted(() => ({ getMonthlyAvailabilityMock: vi.fn() }));

vi.mock('../../../api/availability', () => ({ getMonthlyAvailability: getMonthlyAvailabilityMock }));
vi.mock('../../../services/syncChannel', () => ({
  syncChannel: { subscribe: () => () => {}, publish: vi.fn() },
}));

import useMonthlyQuery from '../useMonthlyQuery';

const grade = (nome: string) => ({
  days: [1, 2],
  legend: {},
  people: [{ id: 1, name: nome }],
  cells: [[null, null]],
  details_index: {},
});

const PARAMS = { year: 2026, month: 10, role: 'FORMADOR' };
const TICK_MS = 30_000;

/** Renderiza o hook guardando o `loading` de cada render (para flagrar o pisca). */
function renderQuery(params = PARAMS) {
  const loadings: boolean[] = [];
  const hook = renderHook(
    (p: typeof PARAMS) => {
      const r = useMonthlyQuery(p);
      loadings.push(r.loading);
      return r;
    },
    { initialProps: params },
  );
  return { ...hook, loadings };
}

async function assentar(): Promise<void> {
  await act(async () => { await vi.advanceTimersByTimeAsync(0); });
}

beforeEach(() => {
  vi.useFakeTimers();
  getMonthlyAvailabilityMock.mockReset();
  getMonthlyAvailabilityMock.mockImplementation(() => Promise.resolve(grade('Pessoa Um')));
});

afterEach(() => {
  vi.useRealTimers();
});

describe('useMonthlyQuery — atualização automática', () => {
  test('primeira carga: mostra carregamento, busca UMA vez no mount', async () => {
    const { result } = renderQuery();
    expect(result.current.loading).toBe(true);

    await assentar();

    expect(result.current.loading).toBe(false);
    expect(result.current.data?.people[0]?.name).toBe('Pessoa Um');
    expect(getMonthlyAvailabilityMock).toHaveBeenCalledTimes(1);
  });

  test('atualiza a cada 30 s, não a cada 5 s', async () => {
    renderQuery();
    await assentar();

    await act(async () => { await vi.advanceTimersByTimeAsync(TICK_MS - 1); });
    expect(getMonthlyAvailabilityMock).toHaveBeenCalledTimes(1);
    await act(async () => { await vi.advanceTimersByTimeAsync(1); });
    expect(getMonthlyAvailabilityMock).toHaveBeenCalledTimes(2);
  });

  test('o tick não liga o carregamento nem tira os dados da tela', async () => {
    const { result, loadings } = renderQuery();
    await assentar();
    loadings.length = 0;

    getMonthlyAvailabilityMock.mockImplementation(() => new Promise(() => undefined)); // em voo
    await act(async () => { await vi.advanceTimersByTimeAsync(TICK_MS); });

    expect(loadings).not.toContain(true);
    expect(result.current.data?.people[0]?.name).toBe('Pessoa Um');
  });

  test('resposta igual mantém a mesma referência; resposta diferente troca os dados', async () => {
    const { result } = renderQuery();
    await assentar();
    const antes = result.current.data;

    await act(async () => { await vi.advanceTimersByTimeAsync(TICK_MS); });
    expect(getMonthlyAvailabilityMock).toHaveBeenCalledTimes(2);
    expect(result.current.data).toBe(antes);

    getMonthlyAvailabilityMock.mockImplementation(() => Promise.resolve(grade('Pessoa Dois')));
    await act(async () => { await vi.advanceTimersByTimeAsync(TICK_MS); });
    expect(result.current.data?.people[0]?.name).toBe('Pessoa Dois');
  });

  test('falha na atualização em segundo plano mantém a grade e avisa que ela pode estar velha', async () => {
    const { result } = renderQuery();
    await assentar();

    getMonthlyAvailabilityMock.mockImplementation(() => Promise.reject(new Error('Sem conexão com o servidor.')));
    await act(async () => { await vi.advanceTimersByTimeAsync(TICK_MS); });

    // `error` (que troca a grade pela caixa de erro) continua vazio; o aviso é à parte.
    expect(result.current.error).toBeNull();
    expect(result.current.data?.people[0]?.name).toBe('Pessoa Um');
    expect(result.current.erroAtualizacao).toBe('Sem conexão com o servidor.');

    // A atualização seguinte que dá certo tira o aviso.
    getMonthlyAvailabilityMock.mockImplementation(() => Promise.resolve(grade('Pessoa Um')));
    await act(async () => { await vi.advanceTimersByTimeAsync(TICK_MS); });
    expect(result.current.erroAtualizacao).toBeNull();
  });

  test('botão de atualizar: mostra andamento sem desmontar a grade', async () => {
    const { result, loadings } = renderQuery();
    await assentar();
    expect(result.current.atualizando).toBe(false);
    loadings.length = 0;

    let responder: (g: unknown) => void = () => undefined;
    getMonthlyAvailabilityMock.mockImplementation(() => new Promise((resolve) => { responder = resolve; }));
    act(() => { void result.current.refetch(); });

    expect(result.current.atualizando).toBe(true);
    expect(loadings).not.toContain(true);
    expect(result.current.data?.people[0]?.name).toBe('Pessoa Um');

    await act(async () => { responder(grade('Pessoa Dois')); });
    expect(result.current.atualizando).toBe(false);
    expect(result.current.data?.people[0]?.name).toBe('Pessoa Dois');
  });

  test('botão de atualizar que falha: a pessoa fica sabendo e a grade continua', async () => {
    const { result } = renderQuery();
    await assentar();

    getMonthlyAvailabilityMock.mockImplementation(() => Promise.reject(new Error('Sem conexão com o servidor.')));
    await act(async () => { await result.current.refetch(); });

    expect(result.current.erroAtualizacao).toBe('Sem conexão com o servidor.');
    expect(result.current.atualizando).toBe(false);
    expect(result.current.error).toBeNull();
    expect(result.current.data?.people[0]?.name).toBe('Pessoa Um');
  });

  test('botão de atualizar com 429: avisa a falha (não só a pausa do polling)', async () => {
    const { result } = renderQuery();
    await assentar();

    getMonthlyAvailabilityMock.mockImplementation(() =>
      Promise.reject(Object.assign(new Error('Limite excedido.'), { status: 429, retryAfter: 90 })),
    );
    await act(async () => { await result.current.refetch(); });

    expect(result.current.pollingPausado).toBe(true);
    expect(result.current.erroAtualizacao).toBe('Limite excedido.');
  });

  test('falha na primeira carga mostra o erro', async () => {
    getMonthlyAvailabilityMock.mockImplementation(() => Promise.reject(new Error('Sem conexão com o servidor.')));
    const { result } = renderQuery();
    await assentar();

    expect(result.current.error).toBe('Sem conexão com o servidor.');
    expect(result.current.data).toBeNull();
    expect(result.current.loading).toBe(false);
  });

  test('429: pausa o polling pelo Retry-After, avisa e retoma sozinho', async () => {
    const { result } = renderQuery();
    await assentar();
    expect(result.current.pollingPausado).toBe(false);

    getMonthlyAvailabilityMock.mockImplementation(() =>
      Promise.reject(Object.assign(new Error('Limite excedido.'), { status: 429, retryAfter: 90 })),
    );
    await act(async () => { await vi.advanceTimersByTimeAsync(TICK_MS); });
    expect(result.current.pollingPausado).toBe(true);
    expect(result.current.error).toBeNull();
    // No tick, o aviso de pausa já explica: sem segundo aviso.
    expect(result.current.erroAtualizacao).toBeNull();
    expect(result.current.data?.people[0]?.name).toBe('Pessoa Um');
    const chamadas = getMonthlyAvailabilityMock.mock.calls.length;

    // Durante a pausa (90 s) passam dois ticks de 30 s: nenhum pedido.
    getMonthlyAvailabilityMock.mockImplementation(() => Promise.resolve(grade('Pessoa Dois')));
    await act(async () => { await vi.advanceTimersByTimeAsync(89_000); });
    expect(getMonthlyAvailabilityMock.mock.calls.length).toBe(chamadas);

    await act(async () => { await vi.advanceTimersByTimeAsync(1_000); });
    expect(result.current.pollingPausado).toBe(false);
    expect(result.current.data?.people[0]?.name).toBe('Pessoa Dois');
  });

  test('trocar o filtro (outro mês) mostra carregamento de novo', async () => {
    const { result, rerender } = renderQuery();
    await assentar();

    getMonthlyAvailabilityMock.mockImplementation(() => new Promise(() => undefined));
    rerender({ ...PARAMS, month: 11 });
    await assentar();

    expect(result.current.loading).toBe(true);
  });

  test('resposta atrasada do mês anterior não sobrescreve a do mês atual', async () => {
    let responderOutubro: (g: unknown) => void = () => undefined;
    getMonthlyAvailabilityMock.mockImplementationOnce(() => new Promise((resolve) => { responderOutubro = resolve; }));
    const { result, rerender } = renderQuery();

    getMonthlyAvailabilityMock.mockImplementation(() => Promise.resolve(grade('Pessoa de Novembro')));
    rerender({ ...PARAMS, month: 11 });
    await assentar();
    expect(result.current.data?.people[0]?.name).toBe('Pessoa de Novembro');

    await act(async () => { responderOutubro(grade('Pessoa de Outubro')); });
    expect(result.current.data?.people[0]?.name).toBe('Pessoa de Novembro');
  });
});
