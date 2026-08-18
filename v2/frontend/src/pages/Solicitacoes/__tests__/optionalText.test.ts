import { describe, it, expect } from 'vitest';

import { optionalText } from '../optionalText';

/**
 * #1739 (field-drift form<->serializer): campos de texto opcionais cujo model e'
 * `TextField(blank=True)` viram `allow_null=False` no serializer DRF. O front coagia
 * texto opcional vazio para `null` (`formData.observacoes || null`), tomando 400
 * "Este campo nao pode ser nulo". optionalText coage para '' (nunca null).
 */
describe('optionalText (#1739 field-drift)', () => {
  it('coage vazio/ausente para string vazia, nunca null', () => {
    expect(optionalText('')).toBe('');
    expect(optionalText(undefined)).toBe('');
    expect(optionalText(null)).toBe('');
  });

  it('preserva texto preenchido', () => {
    expect(optionalText('observação')).toBe('observação');
  });

  it('nunca retorna null e sempre retorna string (contrato allow_null=False)', () => {
    for (const v of ['', null, undefined, 'x'] as const) {
      expect(optionalText(v)).not.toBeNull();
      expect(typeof optionalText(v)).toBe('string');
    }
  });
});
