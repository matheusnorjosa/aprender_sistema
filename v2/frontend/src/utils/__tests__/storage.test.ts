import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { getStorageInt, setStorageInt, storageKeys } from '../storage';

describe('storageKeys', () => {
  it('expõe a key estática de erros do gcal', () => {
    expect(storageKeys.gcalErrors).toBe('gcalAlertsLastErrors');
  });

  it('gera key namespaced por usuário', () => {
    expect(storageKeys.notifUnread(42)).toBe('notifLastUnread:42');
    expect(storageKeys.notifUnread('abc')).toBe('notifLastUnread:abc');
  });
});

describe('getStorageInt / setStorageInt', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('round-trip: setStorageInt grava e getStorageInt lê o mesmo valor', () => {
    setStorageInt('n', 123);
    expect(getStorageInt('n', 0)).toBe(123);
  });

  it('retorna o fallback quando a key não existe', () => {
    expect(getStorageInt('inexistente', 99)).toBe(99);
  });

  it('retorna o fallback quando o valor guardado não é um inteiro', () => {
    localStorage.setItem('lixo', 'not-a-number');
    expect(getStorageInt('lixo', 7)).toBe(7);
  });

  it('parseInt tolera sufixo não-numérico (comportamento de parseInt)', () => {
    localStorage.setItem('misto', '12px');
    expect(getStorageInt('misto', 0)).toBe(12);
  });

  it('getStorageInt retorna fallback se localStorage.getItem lançar', () => {
    const spy = vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('acesso negado');
    });
    expect(getStorageInt('qualquer', 5)).toBe(5);
    spy.mockRestore();
  });

  it('setStorageInt engole erro de quota/private-mode sem lançar', () => {
    const spy = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('QuotaExceeded');
    });
    expect(() => setStorageInt('q', 1)).not.toThrow();
    spy.mockRestore();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });
});
