/** A guarda local contra nomes reais lê a lista de fora do repositório e devolve só a contagem. */
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterAll, describe, expect, it } from 'vitest';

import { contarNomesReais, lerNomesReais } from './nomesReais';

const pasta = mkdtempSync(join(tmpdir(), 'integra-nomes-'));
afterAll(() => rmSync(pasta, { recursive: true, force: true }));

describe('guarda de nomes reais (lista fora do git)', () => {
  it('sem caminho ou sem arquivo, não há lista (o teste que a usa é pulado)', () => {
    expect(lerNomesReais(undefined)).toBeNull();
    expect(lerNomesReais(join(pasta, 'nao-existe.txt'))).toBeNull();
  });

  it('um nome por linha, comparado sem acento e sem maiúscula, em palavra solta ou par', () => {
    const arquivo = join(pasta, 'nomes.txt');
    writeFileSync(arquivo, 'Zélio\r\n\r\nPessoa Teste\n', 'utf-8');
    const nomes = lerNomesReais(arquivo);
    expect(contarNomesReais('Hoje o zelio falou com a pessoa teste.', nomes)).toBe(2);
    // A pontuação não separa o par: "pessoa, teste" ainda conta (melhor sobrar do que faltar).
    expect(contarNomesReais('Com vírgula no meio: pessoa, teste', nomes)).toBe(1);
    expect(contarNomesReais('Ninguém da lista.', nomes)).toBe(0);
  });
});
