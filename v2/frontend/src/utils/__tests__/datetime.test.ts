import { describe, it, expect } from 'vitest';

import { formatFortaleza } from '../datetime';

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
