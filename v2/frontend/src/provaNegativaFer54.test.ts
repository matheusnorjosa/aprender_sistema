// PROVA NEGATIVA (FER-54): falha de propósito para provar que o agregador reprova. Sai no commit seguinte.
import { expect, test } from 'vitest';

test('prova negativa FER-54: uma parte com teste falhando deixa o gate vermelho', () => {
  expect(1).toBe(2);
});
