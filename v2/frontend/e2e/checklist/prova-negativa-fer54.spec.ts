// PROVA NEGATIVA (FER-54): falha de propósito para provar que o agregador do checklist reprova. Sai no commit seguinte.
import { expect, test } from '@playwright/test';

test('prova negativa FER-54: uma parte do checklist falhando deixa o gate vermelho', () => {
  expect(1).toBe(2);
});
