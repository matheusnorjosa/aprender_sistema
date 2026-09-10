import { describe, it, expect } from 'vitest';
import { isValidElement, type ReactElement } from 'react';

import { getColumns } from '../columns';

/**
 * Regressão 2026-09-10: a listagem de DATRegistros virou POR ANO (split fan-out),
 * mas a tabela não tinha coluna "Ano" — linhas por-ano apareciam como duplicatas
 * indistinguíveis. A coluna Ano faz parte de DADOS BÁSICOS e mostra "Pendente"
 * para o bucket não classificado (ano nulo).
 */

const noop = (): void => {};

type RenderCol = {
  dataIndex?: string;
  render?: (v: unknown, r?: unknown) => unknown;
};

function findCol(title: string): RenderCol | undefined {
  const cols = getColumns({ onEdit: noop, onDelete: noop });
  return cols.find((c) => (c as { title?: string }).title === title) as RenderCol | undefined;
}

describe('DATRegistros — coluna Ano (listagem por-ano)', () => {
  it('a coluna "Ano" existe e lê o campo `ano`', () => {
    const ano = findCol('Ano');
    expect(ano).toBeTruthy();
    expect(ano?.dataIndex).toBe('ano');
  });

  it('mostra o ano quando presente', () => {
    const ano = findCol('Ano');
    const el = ano!.render!(2026, {}) as ReactElement<{ children?: unknown }>;
    expect(isValidElement(el)).toBe(true);
    expect(el.props.children).toBe(2026);
  });

  it('mostra "Pendente" quando o ano é nulo (bucket não classificado)', () => {
    const ano = findCol('Ano');
    const el = ano!.render!(undefined, {}) as ReactElement<{ children?: unknown }>;
    expect(isValidElement(el)).toBe(true);
    expect(el.props.children).toBe('Pendente');
  });
});
