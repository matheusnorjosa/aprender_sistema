/**
 * Sentinela: páginas não chamam `fetch` cru — usam os clients de `src/api/`.
 *
 * Issue #1453: `DeslocamentosPage` chamava `fetch()` direto em POST/PUT/DELETE,
 * sem o header `X-CSRFToken`. Com `SessionAuthentication` do DRF, toda mutação
 * retornava 403 em produção (Criar/Editar/Excluir quebrados).
 *
 * O helper canônico `fetchAPI` (`src/api/config.ts`) injeta CSRF nos métodos
 * mutantes, faz retry em 403 de CSRF e respeita `VITE_API_URL`. `fetch` cru numa
 * página bypassa tudo isso — é a classe de bug que este teste trava.
 *
 * Escopo: `src/pages/`. Clients em `src/api/` podem usar `fetch` (é onde
 * `fetchAPI` é implementado).
 */

import { readdirSync, readFileSync } from 'node:fs';
import { dirname, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { describe, expect, test } from 'vitest';

const HERE = dirname(fileURLToPath(import.meta.url));
const PAGES_DIR = resolve(HERE, '..');
const SRC_DIR = resolve(HERE, '../..');

/** Chamada a `fetch` que não seja `fetchAPI`/`ensureCsrfToken` etc. */
const RAW_FETCH = /(?<![.\w])fetch\s*\(/;

/** Comentário/JSDoc — evita falso positivo em prosa que cita `fetch(`. */
const COMMENT_LINE = /^\s*(\/\/|\*|\/\*)/;

function collectSourceFiles(dir: string): string[] {
  const out: string[] = [];

  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);

    if (entry.isDirectory()) {
      if (entry.name === '__tests__') continue;
      out.push(...collectSourceFiles(full));
      continue;
    }

    if (/\.(ts|tsx)$/.test(entry.name) && !/\.(test|spec)\.tsx?$/.test(entry.name)) {
      out.push(full);
    }
  }

  return out;
}

function findRawFetchCalls(file: string): string[] {
  const hits: string[] = [];

  readFileSync(file, 'utf8')
    .split('\n')
    .forEach((line, index) => {
      if (COMMENT_LINE.test(line)) return;
      if (!RAW_FETCH.test(line)) return;

      hits.push(`${relative(SRC_DIR, file)}:${index + 1} → ${line.trim()}`);
    });

  return hits;
}

describe('Sentinela #1453 — páginas usam clients de api/, não `fetch` cru', () => {
  test('nenhuma página chama `fetch` diretamente', () => {
    const offenders = collectSourceFiles(PAGES_DIR).flatMap(findRawFetchCalls);

    expect(
      offenders,
      [
        'Chamada a `fetch` cru encontrada em src/pages/.',
        '',
        'Mutações (POST/PUT/PATCH/DELETE) com `fetch` cru NÃO enviam o header',
        '`X-CSRFToken` → o DRF responde 403 em produção (issue #1453).',
        '',
        'Use um client de `src/api/` (que chama `fetchAPI` de `src/api/config.ts`).',
        'Se a página precisa de um endpoint novo, crie/estenda o client do domínio.',
        '',
        'Ocorrências:',
        ...offenders.map((o) => `  - ${o}`),
      ].join('\n')
    ).toEqual([]);
  });

  test('o sentinela enxerga os arquivos de página (guarda contra glob vazio)', () => {
    // Se o walk quebrar (refactor de pastas), o teste acima passaria vazio e
    // daria falso-verde. Este guard garante que estamos realmente varrendo.
    expect(collectSourceFiles(PAGES_DIR).length).toBeGreaterThan(20);
  });
});
