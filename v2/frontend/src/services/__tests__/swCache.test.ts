/**
 * Limpeza do Cache Storage do Service Worker no logout (Issue #1461).
 *
 * Garante que os caches de API do SW (`aprender-v2-api-*`), que podem conter
 * `/api/me/*` de um usuário anterior, sejam removidos — sem tocar nos caches de
 * assets estáticos nem em caches de terceiros.
 */
import { describe, test, expect, vi, afterEach } from 'vitest';
import { clearApiCaches } from '../swCache';

type GlobalWithCaches = { caches?: CacheStorage };

afterEach(() => {
  delete (globalThis as GlobalWithCaches).caches;
  vi.restoreAllMocks();
});

describe('clearApiCaches (Issue #1461)', () => {
  test('remove os caches de API do SW e preserva os demais', async () => {
    const keys = [
      'aprender-v2-api-v4',
      'aprender-v2-api-v3',
      'aprender-v2-static-v4',
      'workbox-precache',
    ];
    const del = vi.fn().mockResolvedValue(true);
    (globalThis as GlobalWithCaches).caches = {
      keys: vi.fn().mockResolvedValue(keys),
      delete: del,
    } as unknown as CacheStorage;

    await clearApiCaches();

    expect(del).toHaveBeenCalledWith('aprender-v2-api-v4');
    expect(del).toHaveBeenCalledWith('aprender-v2-api-v3');
    expect(del).not.toHaveBeenCalledWith('aprender-v2-static-v4');
    expect(del).not.toHaveBeenCalledWith('workbox-precache');
    expect(del).toHaveBeenCalledTimes(2);
  });

  test('é no-op quando Cache Storage não existe (não lança)', async () => {
    delete (globalThis as GlobalWithCaches).caches;
    await expect(clearApiCaches()).resolves.toBeUndefined();
  });

  test('não lança se caches.keys() rejeitar', async () => {
    (globalThis as GlobalWithCaches).caches = {
      keys: vi.fn().mockRejectedValue(new Error('cache storage indisponível')),
      delete: vi.fn(),
    } as unknown as CacheStorage;

    await expect(clearApiCaches()).resolves.toBeUndefined();
  });
});
