import { describe, it, expect, vi } from 'vitest';
import { deduplicatedFetch, createAbortController } from '../request';

describe('deduplicatedFetch', () => {
  it('reaproveita a mesma promise para chamadas concorrentes com a mesma key', async () => {
    let resolveFn!: (v: number) => void;
    const fetchFn = vi.fn(
      () => new Promise<number>((resolve) => { resolveFn = resolve; }),
    );

    const p1 = deduplicatedFetch('key-a', fetchFn);
    const p2 = deduplicatedFetch('key-a', fetchFn);

    expect(p1).toBe(p2);
    expect(fetchFn).toHaveBeenCalledTimes(1);

    resolveFn(7);
    await expect(p1).resolves.toBe(7);
  });

  it('libera a key após concluir, permitindo novo fetch depois', async () => {
    const fetchFn = vi.fn(() => Promise.resolve('ok'));

    await deduplicatedFetch('key-b', fetchFn);
    await deduplicatedFetch('key-b', fetchFn);

    expect(fetchFn).toHaveBeenCalledTimes(2);
  });

  it('não deduplica keys diferentes', async () => {
    const fetchFn = vi.fn(() => Promise.resolve(1));

    await Promise.all([
      deduplicatedFetch('k1', fetchFn),
      deduplicatedFetch('k2', fetchFn),
    ]);

    expect(fetchFn).toHaveBeenCalledTimes(2);
  });

  it('propaga a rejeição e libera a key', async () => {
    const failing = vi.fn(() => Promise.reject(new Error('falhou')));

    await expect(deduplicatedFetch('key-err', failing)).rejects.toThrow('falhou');

    // key liberada: uma nova chamada dispara o fetch de novo
    const ok = vi.fn(() => Promise.resolve('recuperado'));
    await expect(deduplicatedFetch('key-err', ok)).resolves.toBe('recuperado');
    expect(ok).toHaveBeenCalledTimes(1);
  });
});

describe('createAbortController', () => {
  it('começa não-abortado e aborta ao chamar abort()', () => {
    const { signal, abort } = createAbortController();
    expect(signal.aborted).toBe(false);
    abort();
    expect(signal.aborted).toBe(true);
  });
});
