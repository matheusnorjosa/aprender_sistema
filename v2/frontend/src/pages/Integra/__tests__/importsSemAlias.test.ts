/**
 * O build de produção (`vite.config.ts`) não tem o alias `@/`: só o Vitest e o tsc o conhecem.
 * Um `import ... from '@/...'` que fica no bundle passa nos testes e quebra o `vite build`.
 * Na Integra, todo import que vai para o bundle é relativo (`import type` some na compilação).
 */
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { dirname, join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, test } from 'vitest';

const INTEGRA = join(dirname(fileURLToPath(import.meta.url)), '..');

function arquivos(pasta: string): string[] {
  return readdirSync(pasta).flatMap((nome) => {
    const caminho = join(pasta, nome);
    if (statSync(caminho).isDirectory()) return nome === '__tests__' ? [] : arquivos(caminho);
    return /\.tsx?$/.test(nome) ? [caminho] : [];
  });
}

describe('Integra: imports que vão para o bundle', () => {
  test('nenhum usa o alias @/ (o build de produção não o resolve)', () => {
    const comAlias = arquivos(INTEGRA).flatMap((arquivo) =>
      readFileSync(arquivo, 'utf8')
        .split('\n')
        .filter((linha) => /^\s*import\s+(?!type\b).*from\s+['"]@\//.test(linha))
        .map((linha) => `${relative(INTEGRA, arquivo)}: ${linha.trim()}`),
    );
    expect(comAlias).toEqual([]);
  });
});
