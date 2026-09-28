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
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const SCRIPT = fileURLToPath(new URL('./pr-report.mjs', import.meta.url));
// Raiz do repo a partir deste arquivo (v2/frontend/scripts), não do cwd: o job
// pr-report roda o teste da raiz, e o `npm`/dev, de v2/frontend.
const WORKFLOWS = new URL('../../../.github/workflows/', import.meta.url);

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
 * @param {{ mensal?: boolean, anteriores?: Array<object | string> }} [opcoes]
 *   `anteriores`: comentários mensais anteriores (`{ created_at, body }`, ou
 *   uma linha crua), gravados em JSON Lines e passados em `--anteriores`.
 */
function roda(t, size, lighthouse, { mensal = false, anteriores } = {}) {
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
  const flags = mensal ? ['--mensal'] : [];
  if (anteriores !== undefined) {
    const linhas = anteriores.map((c) => (typeof c === 'string' ? c : JSON.stringify(c)));
    writeFileSync(join(dir, 'anteriores.jsonl'), linhas.map((linha) => `${linha}\n`).join(''));
    flags.push('--anteriores', join(dir, 'anteriores.jsonl'));
  }
  const r = spawnSync(process.execPath, [SCRIPT, ...flags, ...arquivos.map(([arquivo]) => arquivo)], {
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

test('Lighthouse sem falhas nem avisos: "passou", com a concordância certa', (t) => {
  const out = roda(t, SIZE, { ...LIGHTHOUSE, failures: [], warnings: [] });
  assert.match(out, /\*\*Resultado:\*\* passou — 0 falha\(s\), 0 aviso\(s\)/);
  assert.match(out, /Falhas \(reprovam o Lighthouse\): nenhuma\./);
  assert.match(out, /Avisos: nenhum\./);
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

test('modo PR não ganha comparação nem bloco de números', (t) => {
  const out = roda(t, SIZE, LIGHTHOUSE);
  assert.doesNotMatch(out, /medição anterior|as-frontend-monthly/);
});

// Mês seguinte: performance e JS sobem, LCP cai.
const SIZE_OUTUBRO = [{ ...SIZE[0], size: 740000 }, SIZE[1]];
const LIGHTHOUSE_OUTUBRO = {
  ...LIGHTHOUSE,
  categories: { ...LIGHTHOUSE.categories, performance: 0.72 },
  metrics: { ...LIGHTHOUSE.metrics, 'largest-contentful-paint': 2800 },
};

/** Comentário mensal anterior como a API devolve, só com o bloco de números. */
function comentario(createdAt, numeros) {
  return {
    created_at: createdAt,
    body: `<!-- as-frontend-monthly -->\n## Acompanhamento mensal do frontend\n\n<!-- as-frontend-monthly-dados ${JSON.stringify(numeros)} -->\n`,
  };
}

test('mensal, 1ª execução (sem anteriores): marcador e título próprios, "sem medição anterior" e o bloco de números', (t) => {
  const out = roda(t, SIZE, LIGHTHOUSE, { mensal: true, anteriores: [] });
  const linhas = out.split('\n');
  assert.equal(linhas[0], '<!-- as-frontend-monthly -->');
  assert.equal(linhas[1], '## Acompanhamento mensal do frontend');
  assert.match(out, /Commit `0123456` · \[run do CI\]\(.+\) · medição agendada da `main`; não bloqueia merge\./);
  assert.match(out, /\n\n\*\*Contra a medição anterior:\*\* sem medição anterior\.\n\n### Tamanho do bundle/);
  assert.equal(
    linhas.at(-2),
    '<!-- as-frontend-monthly-dados {"performance":0.69,"lcp":3006.4,"js":727500} -->',
  );
  assert.doesNotMatch(out, /as-frontend-report|atualizado a cada push/);
});

test('mensal: compara com os números que o próprio relatório anterior gravou, com a data dele', (t) => {
  const setembro = roda(t, SIZE, LIGHTHOUSE, { mensal: true, anteriores: [] });
  const out = roda(t, SIZE_OUTUBRO, LIGHTHOUSE_OUTUBRO, {
    mensal: true,
    anteriores: [{ created_at: '2026-09-01T12:17:40Z', body: setembro }],
  });
  assert.match(
    out,
    /\*\*Contra a medição anterior \(01\/09\/2026\):\*\* performance 69 → 72 \(\+3\) · LCP 3\.006 → 2\.800 ms \(-206 ms\) · JS 727,5 → 740 kB \(\+12,5 kB\)\./,
  );
});

test('mensal: execução manual não passa por "mês anterior" — a data é a do comentário, em Fortaleza', (t) => {
  // 02:00 UTC de 01/10 = 23:00 de 30/09 em Fortaleza.
  const manual = comentario('2026-10-01T02:00:00Z', { performance: 0.69, lcp: 3006.4, js: 727500 });
  const out = roda(t, SIZE_OUTUBRO, LIGHTHOUSE_OUTUBRO, { mensal: true, anteriores: [manual] });
  assert.match(out, /\*\*Contra a medição anterior \(30\/09\/2026\):\*\* performance 69 → 72/);
  assert.doesNotMatch(out, /mês anterior/);
});

test('mensal: métrica que faltou na medição anterior compara com a última que a tem, e leva a data dela', (t) => {
  const agosto = comentario('2026-08-01T12:17:00Z', { performance: 0.66, lcp: 3211, js: 725000 });
  const setembroQuebrado = comentario('2026-09-01T12:17:00Z', { performance: null, lcp: null, js: 727500 });
  // A ordem do arquivo não importa: vale a created_at.
  for (const anteriores of [[agosto, setembroQuebrado], [setembroQuebrado, agosto]]) {
    const out = roda(t, SIZE_OUTUBRO, LIGHTHOUSE_OUTUBRO, { mensal: true, anteriores });
    assert.match(
      out,
      /\*\*Contra a medição anterior \(01\/09\/2026\):\*\* performance 66 \(01\/08\/2026\) → 72 \(\+6\) · LCP 3\.211 \(01\/08\/2026\) → 2\.800 ms \(-411 ms\) · JS 727,5 → 740 kB \(\+12,5 kB\)\./,
    );
  }
});

test('mensal: número sem base em medição nenhuma, ou que falta agora, vira "n/d" só nele', (t) => {
  const semLighthouse = roda(t, SIZE, undefined, { mensal: true, anteriores: [] });
  assert.match(semLighthouse, /as-frontend-monthly-dados \{"performance":null,"lcp":null,"js":727500\}/);
  const anteriores = [{ created_at: '2026-09-01T12:17:40Z', body: semLighthouse }];
  const out = roda(t, SIZE_OUTUBRO, LIGHTHOUSE_OUTUBRO, { mensal: true, anteriores });
  assert.match(out, /\*\*Contra a medição anterior \(01\/09\/2026\):\*\* performance n\/d · LCP n\/d · JS 727,5 → 740 kB \(\+12,5 kB\)\./);

  const semLighthouseAgora = roda(t, SIZE_OUTUBRO, undefined, { mensal: true, anteriores });
  assert.match(semLighthouseAgora, /performance n\/d · LCP n\/d · JS 727,5 → 740 kB/);
});

test('mensal: a variação sai dos valores arredondados que a linha mostra (68,7 → 69,3 é +0,6)', (t) => {
  const anterior = comentario('2026-09-01T12:17:00Z', { performance: 0.68666, lcp: 3006.4, js: 727500 });
  const lighthouse = { ...LIGHTHOUSE, categories: { ...LIGHTHOUSE.categories, performance: 0.69333 } };
  const out = roda(t, SIZE, lighthouse, { mensal: true, anteriores: [anterior] });
  assert.match(out, /performance 68,7 → 69,3 \(\+0,6\) · LCP 3\.006 → 3\.006 ms \(0 ms\)/);
});

test('mensal: anteriores sem bloco de números, quebrados ou sem data viram "sem medição anterior"', (t) => {
  const anteriores = [
    { created_at: '2026-09-01T12:17:00Z', body: '<!-- as-frontend-monthly -->\nqualquer texto' },
    { created_at: '2026-09-02T12:17:00Z', body: '<!-- as-frontend-monthly-dados {quebrado} -->' },
    { body: comentario('', { performance: 0.7 }).body },
    'linha que não é JSON',
    '',
  ];
  const out = roda(t, SIZE, LIGHTHOUSE, { mensal: true, anteriores });
  assert.match(out, /\*\*Contra a medição anterior:\*\* sem medição anterior\./);
});

// O workflow acha o próprio comentário pelo MARKER do `env:`; se ele e a 1ª
// linha do script divergirem, cada execução vira um comentário "sem anterior"
// (mensal) ou um comentário novo por push (PR), sem erro nenhum.
function marcadorDoWorkflow(arquivo) {
  const yml = readFileSync(new URL(arquivo, WORKFLOWS), 'utf8');
  const marcadores = [...yml.matchAll(/^\s*MARKER:\s*'([^']*)'\s*$/gm)].map((achado) => achado[1]);
  assert.equal(marcadores.length, 1, `esperava um MARKER em ${arquivo}`);
  return marcadores[0];
}

test('o MARKER de cada workflow é a 1ª linha que o script imprime no modo dele', (t) => {
  assert.equal(marcadorDoWorkflow('frontend-ci.yml'), roda(t, SIZE, LIGHTHOUSE).split('\n')[0]);
  assert.equal(
    marcadorDoWorkflow('frontend-metrics-monthly.yml'),
    roda(t, SIZE, LIGHTHOUSE, { mensal: true }).split('\n')[0],
  );
});
