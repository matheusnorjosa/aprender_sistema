import { describe, it, expect } from 'vitest';

import { sanitizeCsvCell, buildCsvRow } from '../csvSanitize';

describe('sanitizeCsvCell', () => {
  it('prefixa aspa simples nos 7 gatilhos de fórmula (= + - @ TAB CR LF)', () => {
    expect(sanitizeCsvCell('=cmd')).toBe("'=cmd");
    expect(sanitizeCsvCell('+1')).toBe("'+1");
    expect(sanitizeCsvCell('-1')).toBe("'-1");
    expect(sanitizeCsvCell('@x')).toBe("'@x");
    expect(sanitizeCsvCell('\tfoo')).toBe("'\tfoo");
    expect(sanitizeCsvCell('\rfoo')).toBe("'\rfoo");
    expect(sanitizeCsvCell('\nfoo')).toBe("'\nfoo");
  });

  it('não altera texto benigno', () => {
    expect(sanitizeCsvCell('Fulano de Tal')).toBe('Fulano de Tal');
    // '=' no meio (não ancorado no início) não é gatilho
    expect(sanitizeCsvCell('a=b')).toBe('a=b');
  });

  it('converte número sem prefixar (benigno)', () => {
    expect(sanitizeCsvCell(42)).toBe('42');
    expect(sanitizeCsvCell(0)).toBe('0');
  });

  it('trata null/undefined como string vazia', () => {
    expect(sanitizeCsvCell(null)).toBe('');
    expect(sanitizeCsvCell(undefined)).toBe('');
  });
});

describe('buildCsvRow', () => {
  it('sanitiza cada célula e junta com o separador informado', () => {
    expect(buildCsvRow(['=cmd', 'ok'], ',')).toBe("'=cmd,ok");
  });

  it('usa ; como separador padrão', () => {
    expect(buildCsvRow(['x', 'y'])).toBe('x;y');
  });

  it('quota célula que contém o separador', () => {
    expect(buildCsvRow(['a;b'], ';')).toBe('"a;b"');
  });

  it('quota e dobra aspas duplas internas', () => {
    expect(buildCsvRow(['a"b'], ';')).toBe('"a""b"');
  });

  it('quota célula com quebra de linha', () => {
    expect(buildCsvRow(['a\nb'], ';')).toBe('"a\nb"');
  });

  it('sanitiza (prefixo \') ANTES de quotar quando há fórmula + separador', () => {
    // '=a;b' -> prefixa ' -> "'=a;b" contém ';' -> quota
    expect(buildCsvRow(['=a;b'], ';')).toBe('"\'=a;b"');
  });
});
