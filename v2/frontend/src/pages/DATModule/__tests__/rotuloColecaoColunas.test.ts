/**
 * A família do projeto (`projeto_geral_nome`) aparece como "Coleção" nas grades de Cadastros e
 * Registros DAT (decisão do dono, 06/10/2026: coleção é a família). Só o rótulo muda: o campo da
 * API continua `projeto_geral`.
 */
import { describe, expect, test, vi } from 'vitest';

import { getColumnsAvaliar, getColumnsFormar } from '../Cadastros/columns';
import { getColumns as getColumnsRegistros } from '../DATRegistros/columns';

type Coluna = { title?: unknown; dataIndex?: unknown; children?: Coluna[] };

/** Todas as colunas, inclusive as de grupos (children). */
function achatar(colunas: readonly Coluna[]): Coluna[] {
  return colunas.flatMap((c) => [c, ...achatar(c.children ?? [])]);
}

function tituloDaFamilia(colunas: readonly Coluna[]): unknown {
  return achatar(colunas).find((c) => c.dataIndex === 'projeto_geral_nome')?.title;
}

const HANDLERS = { onQuickStatusUpdate: vi.fn(), onEdit: vi.fn(), onDelete: vi.fn() };

describe('rótulo Coleção nas grades DAT', () => {
  test.each([
    ['Cadastros FORMAR', getColumnsFormar(HANDLERS)],
    ['Cadastros AVALIAR', getColumnsAvaliar(HANDLERS)],
    ['Registros DAT', getColumnsRegistros(HANDLERS)],
  ])('%s: a coluna da família se chama Coleção', (_tela, colunas) => {
    expect(tituloDaFamilia(colunas as readonly Coluna[])).toBe('Coleção');
  });
});
