import { describe, expect, test } from 'vitest';

import { TIMING } from '../../constants/timing';
import { pausaDo429Ms } from '../retryAfter';

describe('pausaDo429Ms', () => {
  test('erro que não é 429 não pede pausa', () => {
    expect(pausaDo429Ms(new Error('x'))).toBeNull();
    expect(pausaDo429Ms(Object.assign(new Error('x'), { status: 500 }))).toBeNull();
    expect(pausaDo429Ms(null)).toBeNull();
  });

  test('429 com Retry-After usa o tempo do cabeçalho', () => {
    expect(pausaDo429Ms(Object.assign(new Error('x'), { status: 429, retryAfter: 17 }))).toBe(17_000);
  });

  test('429 sem Retry-After (ex.: resposta do nginx) usa o padrão de 60 s', () => {
    expect(TIMING.POLL_PAUSA_429_PADRAO_MS).toBe(60_000);
    expect(pausaDo429Ms(Object.assign(new Error('x'), { status: 429 }))).toBe(60_000);
    expect(pausaDo429Ms(Object.assign(new Error('x'), { status: 429, retryAfter: 0 }))).toBe(60_000);
  });
});
