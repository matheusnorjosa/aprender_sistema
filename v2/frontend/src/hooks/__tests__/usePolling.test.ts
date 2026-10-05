/**
 * usePolling — opção `immediate` (#1668 / M12-19).
 *
 * O caminho de polling da Pré-agenda fazia carga inicial DUPLA: o efeito de
 * filtro da página dispara loadData no mount E o usePolling também busca na hora.
 * A opção `immediate: false` deixa o mount-load ser dono do efeito de filtro,
 * mantendo o intervalo e o fetch-ao-voltar-para-a-aba (visibilitychange).
 */
import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { usePolling } from '../usePolling';

describe('usePolling', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  test('por padrão busca imediatamente no mount', () => {
    const fn = vi.fn();
    renderHook(() => usePolling(fn, { enabled: true, intervalMs: 5000 }));
    expect(fn).toHaveBeenCalledTimes(1);
  });

  test('immediate:false pula o fetch no mount mas mantém o polling por intervalo', () => {
    const fn = vi.fn();
    renderHook(() => usePolling(fn, { enabled: true, intervalMs: 5000, immediate: false }));

    // NÃO busca no mount (evita a carga inicial dupla).
    expect(fn).not.toHaveBeenCalled();

    // O intervalo continua ativo.
    vi.advanceTimersByTime(5000);
    expect(fn).toHaveBeenCalledTimes(1);
    vi.advanceTimersByTime(5000);
    expect(fn).toHaveBeenCalledTimes(2);
  });

  test('enabled:false não busca nem agenda intervalo', () => {
    const fn = vi.fn();
    renderHook(() => usePolling(fn, { enabled: false, intervalMs: 5000 }));
    vi.advanceTimersByTime(20000);
    expect(fn).not.toHaveBeenCalled();
  });

  // ---------------------------------------------------------------------------
  // Liberação 2026-10: carga em voo, aba oculta e pausa por 429.
  // ---------------------------------------------------------------------------

  function setHidden(hidden: boolean): void {
    Object.defineProperty(document, 'hidden', { configurable: true, get: () => hidden });
    document.dispatchEvent(new Event('visibilitychange'));
  }

  test('não abre carga nova enquanto a anterior está em voo', async () => {
    let terminar: () => void = () => undefined;
    const fn = vi.fn(() => new Promise<void>((resolve) => { terminar = resolve; }));
    renderHook(() => usePolling(fn, { enabled: true, intervalMs: 5000, immediate: false }));

    vi.advanceTimersByTime(5000);
    expect(fn).toHaveBeenCalledTimes(1);

    // Rede lenta: a resposta ainda não chegou e vieram mais dois ticks.
    vi.advanceTimersByTime(10000);
    expect(fn).toHaveBeenCalledTimes(1);

    await act(async () => { terminar(); });
    vi.advanceTimersByTime(5000);
    expect(fn).toHaveBeenCalledTimes(2);
  });

  test('carga que falha libera a guarda (o próximo tick busca de novo)', async () => {
    const fn = vi.fn(() => Promise.reject(new Error('falhou')));
    renderHook(() => usePolling(fn, { enabled: true, intervalMs: 5000, immediate: false }));

    vi.advanceTimersByTime(5000);
    await act(async () => { await Promise.resolve(); });
    vi.advanceTimersByTime(5000);
    expect(fn).toHaveBeenCalledTimes(2);
  });

  test('evento que chega com carga em voo refaz a busca UMA vez quando ela termina', async () => {
    let terminar: () => void = () => undefined;
    const fn = vi.fn(() => new Promise<void>((resolve) => { terminar = resolve; }));
    renderHook(() =>
      usePolling(fn, { enabled: true, intervalMs: 5000, immediate: false, events: ['teste:refresh'] }),
    );

    vi.advanceTimersByTime(5000);
    window.dispatchEvent(new Event('teste:refresh'));
    window.dispatchEvent(new Event('teste:refresh'));
    expect(fn).toHaveBeenCalledTimes(1);

    await act(async () => { terminar(); });
    expect(fn).toHaveBeenCalledTimes(2);
  });

  test('aba oculta pausa o polling e faz UMA atualização ao voltar', () => {
    const fn = vi.fn();
    renderHook(() => usePolling(fn, { enabled: true, intervalMs: 5000, immediate: false }));
    try {
      setHidden(true);
      vi.advanceTimersByTime(60000);
      expect(fn).not.toHaveBeenCalled();

      setHidden(false);
      expect(fn).toHaveBeenCalledTimes(1);
      vi.advanceTimersByTime(5000);
      expect(fn).toHaveBeenCalledTimes(2);
    } finally {
      setHidden(false);
    }
  });

  test('pausar(ms) suspende ticks e eventos, avisa pelo estado e retoma sozinho com uma busca', () => {
    const fn = vi.fn();
    const { result } = renderHook(() =>
      usePolling(fn, { enabled: true, intervalMs: 5000, immediate: false, events: ['teste:refresh'] }),
    );
    expect(result.current.pausado).toBe(false);

    act(() => { result.current.pausar(30000); });
    expect(result.current.pausado).toBe(true);

    act(() => { vi.advanceTimersByTime(29000); });
    window.dispatchEvent(new Event('teste:refresh'));
    expect(fn).not.toHaveBeenCalled();
    expect(result.current.pausado).toBe(true);

    act(() => { vi.advanceTimersByTime(1000); });
    expect(result.current.pausado).toBe(false);
    expect(fn).toHaveBeenCalledTimes(1);

    act(() => { vi.advanceTimersByTime(5000); });
    expect(fn).toHaveBeenCalledTimes(2);
  });

  test('desmontar durante a pausa não busca nem atualiza estado depois', () => {
    const fn = vi.fn();
    const { result, unmount } = renderHook(() =>
      usePolling(fn, { enabled: true, intervalMs: 5000, immediate: false }),
    );
    act(() => { result.current.pausar(10000); });
    unmount();
    vi.advanceTimersByTime(60000);
    expect(fn).not.toHaveBeenCalled();
  });
});
