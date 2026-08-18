/**
 * usePolling — opção `immediate` (#1668 / M12-19).
 *
 * O caminho de polling da Pré-agenda fazia carga inicial DUPLA: o efeito de
 * filtro da página dispara loadData no mount E o usePolling também busca na hora.
 * A opção `immediate: false` deixa o mount-load ser dono do efeito de filtro,
 * mantendo o intervalo e o fetch-ao-voltar-para-a-aba (visibilitychange).
 */
import { renderHook } from '@testing-library/react';
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
});
