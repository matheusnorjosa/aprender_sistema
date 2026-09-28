/**
 * Auto-teste do ratchet de cast inseguro (check-unknown-casts.mjs).
 *
 * Roda o script de verdade (processo filho) contra uma árvore `src/` montada num
 * diretório temporário — o que se testa é o contrato de exit code e de saída.
 *
 * Uso: node --test scripts/check-unknown-casts.test.mjs
 */
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const SCRIPT = fileURLToPath(new URL('./check-unknown-casts.mjs', import.meta.url));

const LIMPO = 'export const a: number = 1;\n';
const DOIS_CASTS = 'const x = 1;\nconst y = x as unknown as string;\nconst z = x as unknown as boolean;\n';

/**
 * Monta `<tmp>/src` com os arquivos dados e grava o baseline (objeto → JSON;
 * string → texto cru; undefined → não grava).
 * @param {import('node:test').TestContext} t
 * @param {Record<string, string>} arquivos
 * @param {object | string | undefined} baseline
 */
function cenario(t, arquivos, baseline) {
  const raiz = mkdtempSync(join(tmpdir(), 'unknown-casts-'));
  t.after(() => rmSync(raiz, { recursive: true, force: true }));
  const src = join(raiz, 'src');
  mkdirSync(src);
  for (const [rel, conteudo] of Object.entries(arquivos)) {
    const abs = join(src, rel);
    mkdirSync(dirname(abs), { recursive: true });
    writeFileSync(abs, conteudo);
  }
  const base = join(raiz, 'baseline.json');
  if (baseline !== undefined) {
    writeFileSync(base, typeof baseline === 'string' ? baseline : JSON.stringify(baseline));
  }
  return { src, base };
}

/**
 * @param {{ src: string, base: string }} c
 * @param {string[]} extra
 */
function roda({ src, base }, ...extra) {
  const r = spawnSync(process.execPath, [SCRIPT, '--src', src, '--baseline', base, ...extra], {
    encoding: 'utf8',
  });
  return { code: r.status, out: `${r.stdout}${r.stderr}` };
}

test('árvore limpa com baseline vazio passa, e o arquivo foi de fato medido', (t) => {
  const r = roda(cenario(t, { 'a.ts': LIMPO }, {}));
  assert.equal(r.code, 0, r.out);
  assert.match(r.out, /1 arquivo\(s\) medido\(s\)/);
});

test('contagem igual ao teto passa', (t) => {
  const r = roda(cenario(t, { 'pages/a.tsx': DOIS_CASTS }, { 'src/pages/a.tsx': 2 }));
  assert.equal(r.code, 0, r.out);
  assert.doesNotMatch(r.out, /aperte/);
});

test('subir acima do teto reprova com arquivo:linha de cada ocorrência e o que fazer', (t) => {
  const r = roda(cenario(t, { 'pages/a.tsx': DOIS_CASTS }, { 'src/pages/a.tsx': 1 }));
  assert.equal(r.code, 1, r.out);
  assert.match(r.out, /src\/pages\/a\.tsx: 2 > teto 1/);
  assert.match(r.out, /src\/pages\/a\.tsx:2 {2}const y = x as unknown as string;/);
  assert.match(r.out, /src\/pages\/a\.tsx:3 {2}const z = x as unknown as boolean;/);
  assert.match(r.out, /O QUE FAZER/);
  assert.match(r.out, /Tipe a origem/);
  assert.match(r.out, /suba o teto DESTE arquivo/);
  assert.match(r.out, /renomeado/);
});

test('arquivo fora do baseline tem teto 0', (t) => {
  const r = roda(cenario(t, { 'a.ts': LIMPO, 'novo.ts': 'const v = 1 as unknown as string;\n' }, {}));
  assert.equal(r.code, 1, r.out);
  assert.match(r.out, /src\/novo\.ts: 1 > teto 0/);
});

test('cair abaixo do teto passa e imprime as linhas novas para apertar', (t) => {
  const c = cenario(
    t,
    { 'a.ts': DOIS_CASTS, 'b.ts': LIMPO },
    { 'src/a.ts': 3, 'src/b.ts': 1 },
  );
  const r = roda(c);
  assert.equal(r.code, 0, r.out);
  assert.match(r.out, /aperte/);
  assert.match(r.out, /"src\/a\.ts": 2,/);
  assert.match(r.out, /remova "src\/b\.ts"/);
  assert.match(r.out, /--write/);
});

test('arquivo renomeado: reprova no caminho novo, aponta o antigo, e não sugere --write', (t) => {
  const r = roda(cenario(t, { 'novo.ts': DOIS_CASTS }, { 'src/velho.ts': 2 }));
  assert.equal(r.code, 1, r.out);
  assert.match(r.out, /src\/novo\.ts: 2 > teto 0/);
  assert.match(r.out, /remova "src\/velho\.ts"/);
  assert.match(r.out, /mova a entrada/);
  // Com arquivo acima do teto, --write gravaria a subida junto: não é conselho aqui.
  assert.doesNotMatch(r.out, /--write/);
});

test('quebra de linha entre `as` e `unknown` conta (LF e CRLF), na linha onde começa', (t) => {
  const r = roda(
    cenario(
      t,
      {
        'lf.ts': 'const a = 1;\nconst b = a as\n  unknown as string;\n',
        'crlf.ts': 'const a = 1;\r\nconst b = a as\r\n  unknown as string;\r\n',
      },
      {},
    ),
  );
  assert.equal(r.code, 1, r.out);
  assert.match(r.out, /src\/lf\.ts: 1 > teto 0/);
  assert.match(r.out, /src\/lf\.ts:2 /);
  assert.match(r.out, /src\/crlf\.ts: 1 > teto 0/);
  assert.match(r.out, /src\/crlf\.ts:2 /);
});

test('`(x as unknown) as T` conta — parêntese não tira o cast duplo da contagem', (t) => {
  const r = roda(
    cenario(t, { 'a.ts': 'const x = 1;\nconst y = (x as unknown) as string;\n' }, { 'src/a.ts': 0 }),
  );
  assert.equal(r.code, 1, r.out);
  assert.match(r.out, /src\/a\.ts: 1 > teto 0/);
  assert.match(r.out, /src\/a\.ts:2 {2}const y = \(x as unknown\) as string;/);
});

test('`x as unknown` isolado conta', (t) => {
  const r = roda(cenario(t, { 'a.ts': 'const x = 1;\nconst y = x as unknown;\n' }, { 'src/a.ts': 0 }));
  assert.equal(r.code, 1, r.out);
  assert.match(r.out, /src\/a\.ts: 1 > teto 0/);
  assert.match(r.out, /src\/a\.ts:2 {2}const y = x as unknown;/);
});

test('`as never` conta — trocar o cast duplo por ele não derruba a contagem', (t) => {
  const r = roda(
    cenario(t, { 'a.ts': 'const x = 1;\nconst y: string = x as never;\n' }, { 'src/a.ts': 0 }),
  );
  assert.equal(r.code, 1, r.out);
  assert.match(r.out, /src\/a\.ts:2 {2}const y: string = x as never;/);
});

test('arquivos de teste são ignorados (*.test.*, *.spec.*, __tests__/, src/test/)', (t) => {
  const cast = 'const v = 1 as unknown as string;\n';
  const r = roda(
    cenario(
      t,
      {
        'a.ts': LIMPO,
        'a.test.ts': cast,
        'b.spec.tsx': cast,
        'pages/__tests__/c.tsx': cast,
        'test/setup.ts': cast,
      },
      {},
    ),
  );
  assert.equal(r.code, 0, r.out);
  assert.match(r.out, /1 arquivo\(s\) medido\(s\)/);
});

test('baseline ilegível sai 2', async (t) => {
  for (const [nome, baseline] of /** @type {const} */ ([
    ['ausente', undefined],
    ['JSON inválido', '{ "src/a.ts": '],
    ['lista em vez de objeto', '[]'],
    ['teto negativo', '{ "src/a.ts": -1 }'],
    ['teto não inteiro', '{ "src/a.ts": "2" }'],
  ])) {
    await t.test(nome, (tt) => {
      const r = roda(cenario(tt, { 'a.ts': LIMPO }, baseline));
      assert.equal(r.code, 2, r.out);
      assert.match(r.out, /baseline ilegível/);
    });
  }
});

test('src sem arquivo medido ou inexistente sai 2', (t) => {
  const vazio = cenario(t, { 'a.test.ts': 'const v = 1 as never;\n', 'estilo.css': '' }, {});
  const r = roda(vazio);
  assert.equal(r.code, 2, r.out);
  assert.match(r.out, /0 arquivos/);

  const r2 = roda({ src: join(vazio.src, 'nao-existe'), base: vazio.base });
  assert.equal(r2.code, 2, r2.out);
});

test('--write grava a contagem atual, e o check passa em seguida', (t) => {
  const c = cenario(t, { 'a.ts': DOIS_CASTS, 'b.ts': LIMPO }, undefined);
  const w = roda(c, '--write');
  assert.equal(w.code, 0, w.out);
  assert.deepEqual(JSON.parse(readFileSync(c.base, 'utf8')), { 'src/a.ts': 2 });
  assert.equal(roda(c).code, 0);
});
