/**
 * Semanas da Grade Mensal (C4, sem rolagem horizontal): abaixo de 1280 px a Grade mostra uma
 * semana por vez, de segunda a domingo, cortada no mês. Os índices são os de `days`, para a
 * célula clicada continuar apontando para o `details_index` certo.
 */
import { afterEach, describe, expect, test, vi } from 'vitest';

import { rotuloSemana, semanaInicial, semanasDoMes } from '../semanas';

const diasAte = (n: number): number[] => Array.from({ length: n }, (_, i) => i + 1);
const rotulos = (ano: number, mes: number, n: number): string[] => {
  const days = diasAte(n);
  return semanasDoMes(ano, mes, days).map((s) => rotuloSemana(mes, s.map((i) => days[i] ?? 0)));
};

describe('semanasDoMes e rotuloSemana', () => {
  test('janeiro de 2026 (dia 1 é quinta): 5 semanas de segunda a domingo, cortadas no mês', () => {
    expect(rotulos(2026, 1, 31)).toEqual(['01 a 04/01', '05 a 11/01', '12 a 18/01', '19 a 25/01', '26 a 31/01']);
  });

  test('devolve os índices de days, não os dias', () => {
    expect(semanasDoMes(2026, 1, diasAte(31))[0]).toEqual([0, 1, 2, 3]);
  });

  test('novembro de 2026 começa num domingo: a 1ª semana tem um dia só', () => {
    expect(rotulos(2026, 11, 30)).toEqual(['01/11', '02 a 08/11', '09 a 15/11', '16 a 22/11', '23 a 29/11', '30/11']);
  });

  test('fevereiro de 2026 tem 28 dias e acaba num sábado', () => {
    expect(rotulos(2026, 2, 28)).toEqual(['01/02', '02 a 08/02', '09 a 15/02', '16 a 22/02', '23 a 28/02']);
  });

  test('sem dias, nenhuma semana', () => {
    expect(semanasDoMes(2026, 1, [])).toEqual([]);
  });
});

describe('semanaInicial', () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  test('no mês de hoje (Fortaleza), abre na semana de hoje', () => {
    vi.useFakeTimers({ toFake: ['Date'] });
    vi.setSystemTime(new Date('2026-01-15T12:00:00-03:00'));
    const days = diasAte(31);
    expect(semanaInicial(2026, 1, days, semanasDoMes(2026, 1, days))).toBe(2);
  });

  test('o dia de hoje é o de Fortaleza: 31/01 às 22h em Fortaleza já é 01/02 em UTC', () => {
    vi.useFakeTimers({ toFake: ['Date'] });
    vi.setSystemTime(new Date('2026-02-01T01:00:00Z'));
    const days = diasAte(31);
    expect(semanaInicial(2026, 1, days, semanasDoMes(2026, 1, days))).toBe(4);
  });

  test('em outro mês, abre na primeira semana', () => {
    vi.useFakeTimers({ toFake: ['Date'] });
    vi.setSystemTime(new Date('2026-01-15T12:00:00-03:00'));
    const days = diasAte(28);
    expect(semanaInicial(2026, 2, days, semanasDoMes(2026, 2, days))).toBe(0);
  });
});
