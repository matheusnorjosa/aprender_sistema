import { describe, it, expect } from 'vitest';
import { unwrapList } from '../unwrapList';

describe('unwrapList', () => {
  it('retorna o próprio array quando a resposta já é uma lista', () => {
    const arr = [{ id: 1 }, { id: 2 }];
    expect(unwrapList(arr)).toBe(arr);
  });

  it('extrai `results` de uma PaginatedResponse', () => {
    const results = [{ id: 1 }];
    const paginated = { count: 1, next: null, previous: null, results };
    expect(unwrapList(paginated)).toBe(results);
  });

  it('retorna [] para PaginatedResponse com results vazio', () => {
    expect(unwrapList({ count: 0, next: null, previous: null, results: [] })).toEqual([]);
  });

  it('retorna [] para null', () => {
    expect(unwrapList(null)).toEqual([]);
  });

  it('retorna [] para undefined', () => {
    expect(unwrapList(undefined)).toEqual([]);
  });

  it('retorna [] quando `results` não é um array (resposta malformada)', () => {
    // Simula um payload que não bate com o contrato — o helper degrada para [].
    const malformed = { results: 'oops' } as unknown as { results: never[] };
    expect(unwrapList(malformed)).toEqual([]);
  });

  it('preserva a ordem e os itens de uma lista paginada', () => {
    const results = [{ id: 3 }, { id: 1 }, { id: 2 }];
    expect(unwrapList({ count: 3, next: null, previous: null, results })).toEqual([
      { id: 3 },
      { id: 1 },
      { id: 2 },
    ]);
  });
});
