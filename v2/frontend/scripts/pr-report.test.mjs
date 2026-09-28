/**
 * Auto-teste do relatório do frontend no PR (pr-report.mjs).
 *
 * Roda o script de verdade (processo filho) com fixtures num diretório
 * temporário — o que se testa é o markdown que vai para o comentário.
 *
 * Uso: node --test scripts/pr-report.test.mjs
 */
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const SCRIPT = fileURLToPath(new URL('./pr-report.mjs', import.meta.url));

const SIZE = [
  { name: 'JS Bundle', passed: true, size: 727500, sizeLimit: 750000 },
  { name: 'CSS Bundle', passed: false, size: 55000, sizeLimit: 50000 },
];

const LIGHTHOUSE = {
  runs: 3,
  categories: { performance: 0.69, accessibility: 0.95, 'best-practices': 0.85, seo: 1 },
  metrics: {
    'largest-contentful-paint': 3006.4,
    'total-blocking-time': 120,
    'cumulative-layout-shift': 0.012,
  },
  checks: {
    errors: [
      { type: 'categoryMin', id: 'performance', min: 0.7, label: 'categories:performance >= 0.7' },
      { type: 'categoryMin', id: 'accessibility', min: 0.9, label: 'categories:accessibility >= 0.9' },
      { type: 'auditMax', id: 'largest-contentful-paint', max: 2500, label: 'largest-contentful-paint <= 2500ms' },
      { type: 'auditMax', id: 'cumulative-layout-shift', max: 0.1, label: 'cumulative-layout-shift <= 0.1' },
      { type: 'auditMax', id: 'total-blocking-time', max: 300, label: 'total-blocking-time <= 300ms' },
    ],
    warnings: [{ type: 'categoryMin', id: 'best-practices', min: 0.9, label: 'categories:best-practices >= 0.9' }],
  },
  failures: [
    { label: 'categories:performance >= 0.7', observed: '0.690 (target >= 0.7)' },
    { label: 'largest-contentful-paint <= 2500ms', observed: '3006.40 (target <= 2500)' },
  ],
  warnings: [{ label: 'categories:best-practices >= 0.9', observed: '0.850 (target >= 0.9)' }],
};

/**
 * Grava as fixtures (objeto → JSON; string → texto cru; undefined → não grava)
 * e roda o script com env de CI controlado.
 * @param {import('node:test').TestContext} t
 * @param {object | string | undefined} size
 * @param {object | string | undefined} lighthouse
 */
function roda(t, size, lighthouse) {
  const dir = mkdtempSync(join(tmpdir(), 'pr-report-'));
  t.after(() => rmSync(dir, { recursive: true, force: true }));
  const arquivos = [
    [join(dir, 'size-limit.json'), size],
    [join(dir, 'summary.json'), lighthouse],
  ];
  for (const [arquivo, conteudo] of arquivos) {
    if (conteudo !== undefined) {
      writeFileSync(arquivo, typeof conteudo === 'string' ? conteudo : JSON.stringify(conteudo));
    }
  }
  const r = spawnSync(process.execPath, [SCRIPT, ...arquivos.map(([arquivo]) => arquivo)], {
    encoding: 'utf8',
    env: {
      ...process.env,
      HEAD_SHA: '0123456789abcdef',
      GITHUB_SERVER_URL: 'https://github.com',
      GITHUB_REPOSITORY: 'org/repo',
      GITHUB_RUN_ID: '42',
    },
  });
  assert.equal(r.status, 0, r.stderr);
  return r.stdout;
}

test('com os dois arquivos: marcador, commit, run e as duas seções preenchidas', (t) => {
  const out = roda(t, SIZE, LIGHTHOUSE);
  assert.equal(out.split('\n')[0], '<!-- as-frontend-report -->');
  assert.match(out, /Commit `0123456` · \[run do CI\]\(https:\/\/github\.com\/org\/repo\/actions\/runs\/42\)/);

  assert.match(out, /\| JS Bundle \| 727,5 kB \| 750 kB \| 97% \| ok \|/);
  assert.match(out, /\*\*Resultado:\*\* reprovou — 2 falha\(s\), 1 aviso\(s\); média de 3 execução\(ões\)\./);
  assert.match(out, /\| performance \| 69 \| 70 \| reprovou \|/);
  assert.match(out, /\| accessibility \| 95 \| 90 \| ok \|/);
  assert.match(out, /\| best-practices \| 85 \| 90 \| aviso \|/);
  assert.match(out, /\| LCP \| 3\.006 ms \| 2\.500 ms \| estourou \|/);
  assert.match(out, /\| TBT \| 120 ms \| 300 ms \| ok \|/);
  assert.match(out, /\| CLS \| 0,012 \| 0,1 \| ok \|/);
  assert.match(out, /- `largest-contentful-paint <= 2500ms`: 3006\.40 \(target <= 2500\)/);
  assert.match(out, /Avisos:\n- `categories:best-practices >= 0\.9`/);
  assert.doesNotMatch(out, /Indisponível/);
});

test('limite estourado aparece como "estourou", com o uso acima de 100%', (t) => {
  const out = roda(t, SIZE, LIGHTHOUSE);
  assert.match(out, /\| CSS Bundle \| 55 kB \| 50 kB \| 110% \| estourou \|/);
});

test('os dois arquivos ausentes: as duas seções "Indisponível" com o motivo, e o marcador segue na 1ª linha', (t) => {
  const out = roda(t, undefined, undefined);
  assert.equal(out.split('\n')[0], '<!-- as-frontend-report -->');
  assert.match(out, /### Tamanho do bundle \(size-limit\)\n\n\*\*Indisponível:\*\* arquivo não encontrado \(`size-limit\.json`\)\./);
  assert.match(out, /### Lighthouse\n\n\*\*Indisponível:\*\* arquivo não encontrado \(`summary\.json`\)\./);
});

test('JSON ilegível ou de formato errado também vira "Indisponível", sem derrubar o script', (t) => {
  const out = roda(t, '{ quebrado', { error: 'Error: sem arquivos' });
  assert.match(out, /\*\*Indisponível:\*\* arquivo ilegível \(`size-limit\.json`\): /);
  assert.match(out, /\*\*Indisponível:\*\* formato inesperado/);
});
