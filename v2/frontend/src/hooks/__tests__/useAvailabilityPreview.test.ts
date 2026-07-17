import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';

const { checkAvailabilityManyMock } = vi.hoisted(() => ({
  checkAvailabilityManyMock: vi.fn(),
}));

vi.mock('../../api/availability', () => ({
  checkAvailabilityMany: checkAvailabilityManyMock,
}));

import { useAvailabilityPreview, type AvailabilityPreviewInput } from '../useAvailabilityPreview';

const DEBOUNCE = 400;

function baseInput(over: Partial<AvailabilityPreviewInput> = {}): AvailabilityPreviewInput {
  return {
    inicio: '2026-08-01T12:00:00Z',
    fim: '2026-08-01T14:00:00Z',
    municipioId: 456,
    participantes: [
      { id: 1, nome: 'Ana Criadora', criador: true },
      { id: 99, nome: 'Bruno Formador', criador: false },
    ],
    enabled: true,
    ...over,
  };
}

describe('useAvailabilityPreview', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  test('não dispara sem participante além do criador (idle)', () => {
    const { result } = renderHook(() =>
      useAvailabilityPreview(baseInput({ participantes: [{ id: 1, nome: 'Ana', criador: true }] }))
    );
    expect(result.current).toEqual({ status: 'idle' });
    expect(checkAvailabilityManyMock).not.toHaveBeenCalled();
  });

  test('não dispara com intervalo/município incompletos', () => {
    const { result } = renderHook(() => useAvailabilityPreview(baseInput({ municipioId: null })));
    expect(result.current).toEqual({ status: 'idle' });
    expect(checkAvailabilityManyMock).not.toHaveBeenCalled();
  });

  test('enabled=false não dispara', () => {
    renderHook(() => useAvailabilityPreview(baseInput({ enabled: false })));
    vi.advanceTimersByTime(DEBOUNCE);
    expect(checkAvailabilityManyMock).not.toHaveBeenCalled();
  });

  test('debounce: várias mudanças em rajada coalescem em 1 request', async () => {
    checkAvailabilityManyMock.mockResolvedValue({ ok: true, results: [] });
    const { rerender } = renderHook(({ p }) => useAvailabilityPreview(p), {
      initialProps: { p: baseInput() },
    });
    // 3 mudanças de intervalo dentro da janela de debounce
    rerender({ p: baseInput({ fim: '2026-08-01T14:30:00Z' }) });
    rerender({ p: baseInput({ fim: '2026-08-01T15:00:00Z' }) });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(DEBOUNCE);
    });
    expect(checkAvailabilityManyMock).toHaveBeenCalledTimes(1);
  });

  test('payload inclui o criador e deduplica ids', async () => {
    checkAvailabilityManyMock.mockResolvedValue({ ok: true, results: [] });
    renderHook(() =>
      useAvailabilityPreview(
        baseInput({
          // criador também aparece como coordenador -> só 1 vez
          participantes: [
            { id: 1, nome: 'Ana', criador: true },
            { id: 99, nome: 'Bruno', criador: false },
            { id: 1, nome: 'Ana', criador: false },
          ],
        })
      )
    );
    await act(async () => {
      await vi.advanceTimersByTimeAsync(DEBOUNCE);
    });
    const arg = checkAvailabilityManyMock.mock.calls[0][0];
    expect(arg.usuarios_ids).toEqual([1, 99]);
  });

  test('conflito: mapeia os bloqueados com nome do participante', async () => {
    checkAvailabilityManyMock.mockResolvedValue({
      ok: false,
      results: [
        { usuario_id: 1, ok: true, conflicts: [] },
        {
          usuario_id: 99,
          ok: false,
          conflicts: [{ code: 'X', title: 'Sobreposição', detail: 'evento #5', ref_id: 5 }],
        },
      ],
    });
    const { result } = renderHook(() => useAvailabilityPreview(baseInput()));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(DEBOUNCE);
    });
    if (result.current.status !== 'conflito') throw new Error(`esperava conflito, veio ${result.current.status}`);
    expect(result.current.bloqueados).toHaveLength(1);
    expect(result.current.bloqueados[0]).toMatchObject({ usuario_id: 99, usuario_nome: 'Bruno Formador' });
  });

  test('429 -> indisponivel throttled (fail-open, não bloqueia)', async () => {
    checkAvailabilityManyMock.mockRejectedValue(Object.assign(new Error('rate'), { status: 429 }));
    const { result } = renderHook(() => useAvailabilityPreview(baseInput()));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(DEBOUNCE);
    });
    if (result.current.status !== 'indisponivel') throw new Error(`esperava indisponivel, veio ${result.current.status}`);
    expect(result.current.motivo).toBe('throttled');
  });

  test('500 -> indisponivel erro (fail-open)', async () => {
    checkAvailabilityManyMock.mockRejectedValue(Object.assign(new Error('boom'), { status: 500 }));
    const { result } = renderHook(() => useAvailabilityPreview(baseInput()));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(DEBOUNCE);
    });
    if (result.current.status !== 'indisponivel') throw new Error(`esperava indisponivel, veio ${result.current.status}`);
    expect(result.current.motivo).toBe('erro');
  });

  test('resposta obsoleta é descartada: a última entrada vence', async () => {
    // 1ª chamada (input A) resolve DEPOIS da 2ª (input B). O guard de sequência
    // precisa manter o resultado de B.
    let resolveA!: (v: unknown) => void;
    checkAvailabilityManyMock
      .mockImplementationOnce(() => new Promise((res) => { resolveA = res; }))
      .mockResolvedValueOnce({ ok: true, results: [] }); // B: livre

    const { result, rerender } = renderHook(({ p }) => useAvailabilityPreview(p), {
      initialProps: { p: baseInput() }, // A: com formador 99
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(DEBOUNCE); // dispara A (fica pendente)
    });

    // muda o input -> nova key -> dispara B
    rerender({ p: baseInput({ participantes: [{ id: 1, nome: 'Ana', criador: true }, { id: 77, nome: 'Carla', criador: false }] }) });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(DEBOUNCE); // dispara B (resolve livre)
    });
    expect(result.current.status).toBe('ok');

    // agora A resolve tarde, com conflito — deve ser IGNORADO
    await act(async () => {
      resolveA({
        ok: false,
        results: [{ usuario_id: 99, ok: false, conflicts: [{ code: 'X', title: 't', detail: 'd' }] }],
      });
      await Promise.resolve();
    });
    expect(result.current.status).toBe('ok');
  });
});
