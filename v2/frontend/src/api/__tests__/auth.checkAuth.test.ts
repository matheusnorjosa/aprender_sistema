/**
 * #1741 (F2): checkAuth usava `catch {}` nu → retornava {authenticated:false} em
 * QUALQUER erro (500, blip de rede), disfarçando um erro transitório de "sessão
 * ausente". Só 401/403 significam "não autenticado"; o resto deve RELANÇAR para o
 * caller distinguir (os callers — GruposPage/UsuariosPage — tratam o throw).
 *
 * RED no código antigo: um 500 resolvia como {authenticated:false} em vez de lançar.
 */
import { describe, test, expect, vi, beforeEach } from 'vitest';

vi.mock('../config', () => ({ fetchAPI: vi.fn(), clearCsrfCache: vi.fn() }));
vi.mock('../../types', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../types')>();
  return { ...actual, assertCurrentUserPayload: vi.fn((p: unknown) => p) };
});

import { fetchAPI } from '../config';
import { checkAuth } from '../auth';

describe('#1741 checkAuth: distingue 401/403 de erro transitório', () => {
  beforeEach(() => vi.clearAllMocks());

  test('sucesso → authenticated:true + user', async () => {
    vi.mocked(fetchAPI).mockResolvedValue({ id: 1, is_superuser: true });
    await expect(checkAuth()).resolves.toEqual({
      authenticated: true,
      user: { id: 1, is_superuser: true },
    });
  });

  test('401 → authenticated:false (sem lançar)', async () => {
    vi.mocked(fetchAPI).mockRejectedValue(Object.assign(new Error('unauth'), { status: 401 }));
    await expect(checkAuth()).resolves.toEqual({ authenticated: false, user: null });
  });

  test('403 → authenticated:false (sem lançar)', async () => {
    vi.mocked(fetchAPI).mockRejectedValue(Object.assign(new Error('forbidden'), { status: 403 }));
    await expect(checkAuth()).resolves.toEqual({ authenticated: false, user: null });
  });

  test('500 transitório → RELANÇA (não se disfarça de deslogado)', async () => {
    vi.mocked(fetchAPI).mockRejectedValue(Object.assign(new Error('boom'), { status: 500 }));
    await expect(checkAuth()).rejects.toThrow('boom');
  });

  test('erro de rede (sem status) → RELANÇA', async () => {
    vi.mocked(fetchAPI).mockRejectedValue(new TypeError('Failed to fetch'));
    await expect(checkAuth()).rejects.toThrow('Failed to fetch');
  });
});
