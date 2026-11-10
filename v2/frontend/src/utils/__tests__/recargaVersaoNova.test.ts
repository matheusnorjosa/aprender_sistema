/**
 * A página aberta é de uma versão que saiu do ar: o pedaço da tela (chunk) que ela pede não existe mais
 * no servidor depois de uma promoção. Recarregar uma vez busca a versão nova; uma 2ª falha em menos
 * de 30 s não recarrega de novo (não entra em laço se o servidor estiver de fato fora).
 */
import { describe, expect, test, vi, beforeEach } from 'vitest';
import { ehVersaoAntiga, recarregarSeVersaoAntiga } from '../recargaVersaoNova';

const ERRO_CHUNK = new TypeError(
  'Failed to fetch dynamically imported module: https://aprendersistema.com.br/assets/HomePage-BKUHwhJH.js',
);

describe('recarga quando a página é de uma versão antiga', () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  test('reconhece o erro de pedaço que sumiu (Chrome, Safari e Firefox), e não outro erro', () => {
    expect(ehVersaoAntiga(ERRO_CHUNK)).toBe(true);
    expect(ehVersaoAntiga(new TypeError('Importing a module script failed.'))).toBe(true);
    expect(ehVersaoAntiga(new Error('error loading dynamically imported module: /assets/x.js'))).toBe(true);
    expect(ehVersaoAntiga(new Error('Unable to preload CSS for /assets/x.css'))).toBe(true);
    expect(ehVersaoAntiga(new Error('boom'))).toBe(false);
    expect(ehVersaoAntiga(undefined)).toBe(false);
  });

  test('recarrega uma vez', () => {
    const recarregar = vi.fn();
    expect(recarregarSeVersaoAntiga(ERRO_CHUNK, { agora: 1_000_000, recarregar })).toBe(true);
    expect(recarregar).toHaveBeenCalledTimes(1);
  });

  test('erro comum não recarrega', () => {
    const recarregar = vi.fn();
    expect(recarregarSeVersaoAntiga(new Error('boom'), { agora: 1_000_000, recarregar })).toBe(false);
    expect(recarregar).not.toHaveBeenCalled();
  });

  test('não recarrega de novo em menos de 30 s; depois disso, pode', () => {
    const recarregar = vi.fn();
    recarregarSeVersaoAntiga(ERRO_CHUNK, { agora: 1_000_000, recarregar });
    expect(recarregarSeVersaoAntiga(ERRO_CHUNK, { agora: 1_029_000, recarregar })).toBe(false);
    expect(recarregarSeVersaoAntiga(ERRO_CHUNK, { agora: 1_031_000, recarregar })).toBe(true);
    expect(recarregar).toHaveBeenCalledTimes(2);
  });

  test('sem sessionStorage não recarrega (não arrisca laço)', () => {
    const recarregar = vi.fn();
    const spy = vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('bloqueado');
    });
    expect(recarregarSeVersaoAntiga(ERRO_CHUNK, { agora: 1_000_000, recarregar })).toBe(false);
    expect(recarregar).not.toHaveBeenCalled();
    spy.mockRestore();
  });
});
