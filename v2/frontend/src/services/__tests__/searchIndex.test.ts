/**
 * Tests for SearchIndex service.
 *
 * @see searchIndex.ts
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { searchIndex } from '../searchIndex';

describe('SearchIndex', () => {
  beforeEach(() => {
    searchIndex.clear();
  });

  it('indexes and searches data', async () => {
    const data = [
      { id: 1, nome: 'Fortaleza', uf: 'CE' },
      { id: 2, nome: 'Sao Paulo', uf: 'SP' },
      { id: 3, nome: 'Fortal', uf: 'CE' },
    ];

    await searchIndex.index('cities', data, { keys: ['nome', 'uf'] });

    const results = searchIndex.search('cities', 'Fort');

    expect(results.length).toBe(2);
    expect(results[0].nome).toBe('Fortaleza');
  });

  it('returns empty for short queries', async () => {
    const data = [{ id: 1, nome: 'Fortaleza' }];
    await searchIndex.index('cities', data, { keys: ['nome'] });

    const results = searchIndex.search('cities', 'F');

    expect(results).toEqual([]);
  });

  it('returns empty for non-existent index', () => {
    const results = searchIndex.search('nonexistent', 'test');
    expect(results).toEqual([]);
  });

  it('checks if index exists', async () => {
    expect(searchIndex.hasIndex('test')).toBe(false);

    await searchIndex.index('test', [{ id: 1, nome: 'Test' }], { keys: ['nome'] });

    expect(searchIndex.hasIndex('test')).toBe(true);
  });

  it('gets count of indexed items', async () => {
    const data = [
      { id: 1, nome: 'A' },
      { id: 2, nome: 'B' },
      { id: 3, nome: 'C' },
    ];

    await searchIndex.index('items', data, { keys: ['nome'] });

    expect(searchIndex.getCount('items')).toBe(3);
    expect(searchIndex.getCount('nonexistent')).toBe(0);
  });

  it('clears specific index', async () => {
    await searchIndex.index('a', [{ id: 1, nome: 'A' }], { keys: ['nome'] });
    await searchIndex.index('b', [{ id: 2, nome: 'B' }], { keys: ['nome'] });

    searchIndex.clear('a');

    expect(searchIndex.hasIndex('a')).toBe(false);
    expect(searchIndex.hasIndex('b')).toBe(true);
  });

  it('clears all indices', async () => {
    await searchIndex.index('a', [{ id: 1, nome: 'A' }], { keys: ['nome'] });
    await searchIndex.index('b', [{ id: 2, nome: 'B' }], { keys: ['nome'] });

    searchIndex.clear();

    expect(searchIndex.hasIndex('a')).toBe(false);
    expect(searchIndex.hasIndex('b')).toBe(false);
  });

  it('searches across all indices', async () => {
    await searchIndex.index('municipios', [{ id: 1, nome: 'Fortaleza' }], { keys: ['nome'] });
    await searchIndex.index('projetos', [{ id: 2, nome: 'Fortalecer' }], { keys: ['nome'] });

    const results = searchIndex.searchAll('Fort', 5);

    expect(Object.keys(results)).toContain('municipios');
    expect(Object.keys(results)).toContain('projetos');
    expect(results.municipios.length).toBe(1);
    expect(results.projetos.length).toBe(1);
  });

  it('includes score and matches in results', async () => {
    const data = [{ id: 1, nome: 'Fortaleza' }];
    await searchIndex.index('cities', data, { keys: ['nome'] });

    const results = searchIndex.search('cities', 'Fortaleza');

    expect(results[0]._score).toBeDefined();
    expect(results[0]._matches).toBeDefined();
  });
});
