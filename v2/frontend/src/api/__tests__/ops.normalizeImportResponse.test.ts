/**
 * Tests for `normalizeImportResponse` in api/ops.ts.
 *
 * Backend importers return different shapes (stats/pendencias variants).
 * The adapter must reshape them into the canonical `ImportResult` so the
 * page-level helpers (`toValidationResult`, `toApplyResult`) keep working
 * without page-by-page changes.
 *
 * Reproduces the production crash:
 *   "Cannot read properties of undefined (reading 'map')"
 * which was triggered when the page did `result.errors.map(...)` on a raw
 * `{stats, pendencias, dry_run, file}` payload from the backend.
 */

import { describe, expect, test } from 'vitest';
import { __testing } from '../ops';

const { normalizeImportResponse } = __testing;

describe('normalizeImportResponse — bug fix #DAT-imports response shape', () => {
  test('handles bloqueios shape: stats.skipped object + pendencias categories', () => {
    const raw = {
      stats: {
        created: 66,
        updated: 0,
        unchanged: 2,
        skipped: { usuario: 0, dates: 0, other: 0 },
      },
      pendencias: { usuarios: [], dates: [], outros: [] },
      dry_run: true,
      file: '/tmp/x.xlsx',
    };
    const r = normalizeImportResponse(raw);
    expect(r.created).toBe(66);
    expect(r.updated).toBe(0);
    expect(r.skipped).toBe(2); // unchanged + sum(skipped categories)
    expect(r.errors).toEqual([]);
    expect(r.warnings).toEqual([]);
  });

  test('handles compras shape: stats.skipped number + pendencias categories', () => {
    const raw = {
      stats: { created: 1884, updated: 0, skipped: 105, errors: 0 },
      pendencias: { municipios: [], projetos: [], linhas_invalidas: [] },
      dry_run: true,
      file: '/tmp/c.csv',
    };
    const r = normalizeImportResponse(raw);
    expect(r.created).toBe(1884);
    expect(r.skipped).toBe(105);
    expect(r.errors).toEqual([]);
  });

  test('handles eventos shape: nested stats.solicitacoes', () => {
    const raw = {
      stats: {
        solicitacoes: { created: 2081, updated: 0, unchanged: 113 },
        participations: { created: 4996, updated: 29 },
        skipped: {
          municipio: 0,
          projeto: 0,
          tipo_evento: 0,
          coordenador: 212,
          dates: 17,
          other: 0,
        },
      },
      pendencias: {
        municipios: [],
        projetos: [],
        tipos_evento: [],
        usuarios: [],
        dates: [],
        outros: [],
      },
      dry_run: true,
      file: '/tmp/e.xlsx',
    };
    const r = normalizeImportResponse(raw);
    expect(r.created).toBe(2081); // from solicitacoes (not participations)
    expect(r.updated).toBe(0);
    expect(r.skipped).toBe(113 + 212 + 17); // unchanged + skipped categories
  });

  test('flattens pendencias dict-of-arrays into errors[]', () => {
    const raw = {
      stats: { created: 0, updated: 0, skipped: { usuario: 2 } },
      pendencias: {
        usuarios: [
          { linha: 5, nome: 'X', erro: 'usuario não encontrado' },
          { linha: 7, erro: 'cpf inválido' },
        ],
      },
    };
    const r = normalizeImportResponse(raw);
    expect(r.errors).toHaveLength(2);
    expect(r.errors[0]).toEqual({ row: 5, message: '[usuarios] usuario não encontrado — X' });
    expect(r.errors[1]).toEqual({ row: 7, message: '[usuarios] cpf inválido' });
  });

  test('accepts legacy/flat shape (pass-through)', () => {
    const raw = {
      created: 10,
      updated: 5,
      skipped: 2,
      errors: [{ row: 3, message: 'oops' }],
      warnings: ['be careful'],
    };
    const r = normalizeImportResponse(raw);
    expect(r.created).toBe(10);
    expect(r.skipped).toBe(2);
    expect(r.errors).toEqual([{ row: 3, message: 'oops' }]);
    expect(r.warnings).toEqual(['be careful']);
  });

  test('returns safe zeros for null/undefined/non-object input', () => {
    expect(normalizeImportResponse(null)).toEqual({
      created: 0,
      updated: 0,
      skipped: 0,
      errors: [],
      warnings: [],
    });
    expect(normalizeImportResponse(undefined)).toEqual({
      created: 0,
      updated: 0,
      skipped: 0,
      errors: [],
      warnings: [],
    });
    expect(normalizeImportResponse('not an object')).toMatchObject({
      created: 0,
      errors: [],
    });
  });

  test('regression: result.errors is always an array (defeats .map of undefined)', () => {
    // The original crash: `result.errors.map(...)` when backend returns
    // {stats, pendencias} without `errors`. The adapter must always set errors[].
    const minimal = { stats: { created: 1 } };
    const r = normalizeImportResponse(minimal);
    expect(Array.isArray(r.errors)).toBe(true);
    // .map must work
    expect(r.errors.map((e) => e.message)).toEqual([]);
  });

  test('handles row number from alternative key (linha_num for municipios)', () => {
    const raw = {
      stats: { created: 0, updated: 0, skipped: { municipios: 1 } },
      pendencias: {
        municipios: [{ linha_num: 12, erro: 'Nome ausente' }],
      },
    };
    const r = normalizeImportResponse(raw);
    expect(r.errors[0].row).toBe(12);
    expect(r.errors[0].message).toContain('Nome ausente');
  });
});
