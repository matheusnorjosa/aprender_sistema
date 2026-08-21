import { describe, it, expect } from 'vitest';
import { getErrorStatus, isAuthError } from '../errors';

describe('getErrorStatus', () => {
  it('lê `status` direto do erro', () => {
    expect(getErrorStatus({ status: 404 })).toBe(404);
  });

  it('lê `response.status` (erros no formato axios/fetch-wrapper)', () => {
    expect(getErrorStatus({ response: { status: 500 } })).toBe(500);
  });

  it('prioriza `status` de topo sobre `response.status`', () => {
    expect(getErrorStatus({ status: 403, response: { status: 500 } })).toBe(403);
  });

  it('retorna undefined quando não há status numérico', () => {
    expect(getErrorStatus({ message: 'boom' })).toBeUndefined();
    expect(getErrorStatus({ status: 'nope' })).toBeUndefined();
    expect(getErrorStatus({ response: { status: 'nope' } })).toBeUndefined();
  });

  it('retorna undefined para não-objetos e null', () => {
    expect(getErrorStatus(null)).toBeUndefined();
    expect(getErrorStatus(undefined)).toBeUndefined();
    expect(getErrorStatus('erro')).toBeUndefined();
    expect(getErrorStatus(42)).toBeUndefined();
  });

  it('retorna undefined quando response não é objeto', () => {
    expect(getErrorStatus({ response: 'oops' })).toBeUndefined();
    expect(getErrorStatus({ response: null })).toBeUndefined();
  });
});

describe('isAuthError', () => {
  it('true para 401 e 403', () => {
    expect(isAuthError({ status: 401 })).toBe(true);
    expect(isAuthError({ status: 403 })).toBe(true);
    expect(isAuthError({ response: { status: 401 } })).toBe(true);
  });

  it('false para outros status e erros sem status', () => {
    expect(isAuthError({ status: 404 })).toBe(false);
    expect(isAuthError({ status: 500 })).toBe(false);
    expect(isAuthError({ message: 'x' })).toBe(false);
    expect(isAuthError(null)).toBe(false);
  });
});
