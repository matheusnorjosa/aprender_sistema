import { describe, it, expect } from 'vitest';
import dayjs from 'dayjs';

import { formatFortaleza, fortalezaWallClockToISO } from '../datetime';

/**
 * RD-06 / CP-03: eventos são armazenados em UTC e DEVEM ser exibidos em
 * America/Fortaleza (UTC−3, sem DST). O teste é independente do fuso do
 * runner justamente porque o util fixa o fuso — é essa a garantia.
 */
describe('formatFortaleza (RD-06: exibe em America/Fortaleza)', () => {
  it('converte um instante UTC para o horário de Fortaleza (UTC−3)', () => {
    // 12:00Z = 09:00 em Fortaleza
    expect(formatFortaleza('2026-09-15T12:00:00Z')).toBe('15/09/2026 09:00');
  });

  it('aceita formato customizado', () => {
    expect(formatFortaleza('2026-09-15T12:00:00Z', 'HH:mm')).toBe('09:00');
  });

  it('vira o dia corretamente perto da meia-noite UTC', () => {
    // 01:00Z do dia 16 = 22:00 do dia 15 em Fortaleza
    expect(formatFortaleza('2026-09-16T01:00:00Z', 'DD/MM/YYYY HH:mm')).toBe('15/09/2026 22:00');
  });

  it('preserva o instante quando a origem já traz offset −03:00', () => {
    expect(formatFortaleza('2026-09-15T09:00:00-03:00', 'HH:mm')).toBe('09:00');
  });

  it('não quebra com valor nulo/vazio', () => {
    expect(formatFortaleza(null)).toBe('');
    expect(formatFortaleza(undefined)).toBe('');
    expect(formatFortaleza('')).toBe('');
  });
});

describe('fortalezaWallClockToISO (RD-06: escreve interpretando o wall-clock como Fortaleza)', () => {
  it('trata o horário escolhido como America/Fortaleza (UTC−3) e serializa em UTC', () => {
    // usuário escolhe 08:00 (pensando em Fortaleza) → 11:00Z, independente do fuso do runner
    expect(fortalezaWallClockToISO(dayjs('2026-05-10 08:00'))).toBe('2026-05-10T11:00:00.000Z');
  });

  it('meia-noite em Fortaleza vira 03:00Z do mesmo dia', () => {
    expect(fortalezaWallClockToISO(dayjs('2026-05-10 00:00'))).toBe('2026-05-10T03:00:00.000Z');
  });

  it('não quebra com valor nulo/inválido', () => {
    expect(fortalezaWallClockToISO(null)).toBe('');
    expect(fortalezaWallClockToISO('')).toBe('');
  });
});
