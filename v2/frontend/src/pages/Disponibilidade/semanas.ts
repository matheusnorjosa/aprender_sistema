/**
 * Semanas da Grade Mensal (C4, sem rolagem horizontal, decisão do dono).
 *
 * Abaixo de 1280 px a Grade mostra uma semana por vez, de segunda a domingo, cortada no mês
 * (o mês que começa num domingo abre com uma semana de um dia). As semanas guardam os índices
 * de `days`, não os dias: a chave `${rowIdx}:${dayIdx}` do `details_index` continua valendo.
 */
import dayjs from 'dayjs';

import { FORTALEZA_TZ } from '../../utils/datetime';

/** Índices de `days` agrupados por semana (segunda a domingo). */
export function semanasDoMes(ano: number, mes: number, days: readonly number[]): number[][] {
  const semanas: number[][] = [];
  days.forEach((dia, idx) => {
    // Data de calendário (sem hora): o fuso não muda o dia da semana.
    const segunda = new Date(ano, mes - 1, dia).getDay() === 1;
    const atual = semanas[semanas.length - 1];
    if (!atual || segunda) semanas.push([idx]);
    else atual.push(idx);
  });
  return semanas;
}

const doisDigitos = (n: number): string => String(n).padStart(2, '0');

/** "12 a 18/01", ou "01/11" na semana de um dia só. */
export function rotuloSemana(mes: number, dias: readonly number[]): string {
  const primeiro = dias[0];
  const ultimo = dias[dias.length - 1];
  if (primeiro === undefined || ultimo === undefined) return '';
  const fim = `${doisDigitos(ultimo)}/${doisDigitos(mes)}`;
  return primeiro === ultimo ? fim : `${doisDigitos(primeiro)} a ${fim}`;
}

/** No mês de hoje (em Fortaleza), a semana de hoje; nos outros meses, a primeira. */
export function semanaInicial(
  ano: number,
  mes: number,
  days: readonly number[],
  semanas: readonly (readonly number[])[]
): number {
  const hoje = dayjs().tz(FORTALEZA_TZ);
  if (hoje.year() !== ano || hoje.month() + 1 !== mes) return 0;
  return Math.max(0, semanas.findIndex((s) => s.some((idx) => days[idx] === hoje.date())));
}
