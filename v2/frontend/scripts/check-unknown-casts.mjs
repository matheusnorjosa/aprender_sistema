#!/usr/bin/env node
/**
 * Ratchet de cast inseguro (`as unknown` e `as never`) no frontend de produção.
 *
 * `x as unknown as T` desliga o type-checker naquele ponto: o compilador aceita
 * qualquer T. Medido em 2026-09-28: 55 ocorrências em 21 arquivos de produção.
 * Zerar é trabalho de tipagem arquivo a arquivo, não de um PR — então o gate é
 * RATCHET: a contagem de cada arquivo não pode passar do teto registrado em
 * `unknown-casts-baseline.json`. Cair é livre, e o gate sugere apertar o teto.
 *
 * Teto POR ARQUIVO, e não total: com total, tipar um cast em A "paga" um cast
 * novo em B e o número fica igual — a dívida só muda de lugar.
 *
 * Conta QUALQUER `as unknown`, não só a sequência `as unknown as`: toda dupla
 * conversão passa por `as unknown`, e a sequência literal deixava escapar
 * `(x as unknown) as T` (ou um comentário entre `unknown` e `as`). Sem isso, a
 * burla faria a contagem CAIR e o gate sugeriria apertar o teto: premiaria quem
 * o contorna. Custo: `x as unknown` isolado (só alarga o tipo) também conta —
 * anote `const v: unknown = x` no lugar. Em 2026-09-28 havia 0 casos isolados.
 *
 * Conta `as never` pelo mesmo motivo: ele compila no lugar de `as unknown as T`
 * (never é atribuível a tudo).
 *
 * Escopo: .ts/.tsx em src/, fora testes (*.test.*, *.spec.*, __tests__/, src/test/)
 * — os mesmos predicados de check-brand-colors.mjs. O regex roda no conteúdo
 * inteiro, então quebra de linha (LF ou CRLF) entre `as` e `unknown` também conta.
 * Heurística textual: o padrão dentro de comentário ou string conta igual.
 * Limites conhecidos (não contados): cast em ângulo (`<unknown>x`, só em .ts) e
 * helper genérico do tipo `cast<T>(x: unknown): T`.
 *
 * Uso:
 *   node scripts/check-unknown-casts.mjs          # CI: npm run check:unknown-casts
 *   node scripts/check-unknown-casts.mjs --write  # regenera o baseline
 *   node scripts/check-unknown-casts.mjs --src DIR --baseline ARQ.json   # testes
 *
 * `--write` grava a contagem ATUAL de cada arquivo (inclusive uma subida): use-o
 * para apertar o teto depois de tipar casts. O diff do JSON no PR é o que se revisa.
 *
 * Exit 0 = nenhum arquivo acima do teto. 1 = algum arquivo passou do teto.
 * 2 = uso/configuração (argumento inválido, baseline ilegível, 0 arquivos medidos).
 *
 * Auto-teste: node --test scripts/check-unknown-casts.test.mjs
 */
import { readdirSync, statSync, readFileSync, writeFileSync } from 'node:fs';
import { join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseArgs } from 'node:util';

const CAST = /\bas\s+unknown\b|\bas\s+never\b/g;

/** @param {string} name */
const isTestFile = (name) => /\.(test|spec)\.[jt]sx?$/.test(name);
/** @param {string} rel */
const inTestInfra = (rel) => rel === 'test' || rel.startsWith('test/');

/** @param {string} msg @returns {never} */
function erroDeUso(msg) {
  console.error(`ERRO: ${msg}`);
  process.exit(2);
}

/** @type {{ src?: string, baseline?: string, write?: boolean }} */
let args = {};
try {
  args = parseArgs({
    options: {
      src: { type: 'string' },
      baseline: { type: 'string' },
      write: { type: 'boolean' },
    },
  }).values;
} catch (e) {
  erroDeUso(
    `${/** @type {Error} */ (e).message}\n` +
      'Uso: node scripts/check-unknown-casts.mjs [--write] [--src DIR] [--baseline ARQ.json]',
  );
}

const SRC = args.src ?? fileURLToPath(new URL('../src', import.meta.url));
const BASELINE = args.baseline ?? fileURLToPath(new URL('./unknown-casts-baseline.json', import.meta.url));
const BASELINE_ROTULO = args.baseline ?? 'scripts/unknown-casts-baseline.json';

/** @type {Map<string, { linha: number, trecho: string }[]>} arquivo → ocorrências */
const achados = new Map();
let medidos = 0;

/** @param {string} dir */
function walk(dir) {
  for (const name of readdirSync(dir)) {
    const abs = join(dir, name);
    const rel = relative(SRC, abs).split('\\').join('/');
    if (statSync(abs).isDirectory()) {
      if (name === '__tests__' || name === 'node_modules') continue;
      walk(abs);
      continue;
    }
    if (!/\.(ts|tsx)$/.test(name)) continue;
    if (isTestFile(name) || inTestInfra(rel)) continue;

    medidos++;
    const texto = readFileSync(abs, 'utf8');
    const linhas = texto.split('\n');
    const ocorrencias = [...texto.matchAll(CAST)].map((m) => {
      const linha = texto.slice(0, m.index).split('\n').length;
      return { linha, trecho: linhas[linha - 1].trim() };
    });
    if (ocorrencias.length > 0) achados.set('src/' + rel, ocorrencias);
  }
}

try {
  walk(SRC);
} catch (e) {
  erroDeUso(`não consegui ler ${SRC}: ${/** @type {Error} */ (e).message}`);
}

// Nada medido não é aprovação: `--src` errado ou árvore vazia deixaria o gate
// verde por vacuidade.
if (medidos === 0) {
  erroDeUso(`0 arquivos .ts/.tsx de produção medidos em ${SRC}. Sem medida não há aprovação.`);
}

const arquivos = [...achados.keys()].sort();
const total = arquivos.reduce((soma, f) => soma + (achados.get(f)?.length ?? 0), 0);

if (args.write) {
  /** @type {Record<string, number>} */
  const novo = {};
  for (const f of arquivos) novo[f] = achados.get(f)?.length ?? 0;
  writeFileSync(BASELINE, JSON.stringify(novo, null, 2) + '\n');
  console.log(
    `Baseline gravado em ${BASELINE_ROTULO}: ${total} cast(s) em ${arquivos.length} arquivo(s) ` +
      `(${medidos} arquivo(s) medido(s)).`,
  );
  process.exit(0);
}

// Baseline ausente lido como vazio reprovaria tudo no dia 1; lido como "sem
// teto" aprovaria tudo. Nenhum dos dois: é erro de configuração.
/** @type {Record<string, number>} */
let teto = {};
try {
  const lido = JSON.parse(readFileSync(BASELINE, 'utf8'));
  if (lido === null || typeof lido !== 'object' || Array.isArray(lido)) {
    throw new Error('precisa ser um objeto {"src/arquivo.tsx": teto}');
  }
  for (const [f, t] of Object.entries(lido)) {
    if (!Number.isInteger(t) || t < 0) throw new Error(`teto inválido para ${f}: ${JSON.stringify(t)}`);
  }
  teto = lido;
} catch (e) {
  erroDeUso(`baseline ilegível em ${BASELINE_ROTULO}: ${/** @type {Error} */ (e).message}`);
}

/** @param {string} f */
const tetoDe = (f) => (Object.hasOwn(teto, f) ? teto[f] : 0);
/** @param {string} f */
const contagemDe = (f) => achados.get(f)?.length ?? 0;

const acima = arquivos.filter((f) => contagemDe(f) > tetoDe(f));
const caiu = Object.keys(teto)
  .sort()
  .filter((f) => contagemDe(f) < tetoDe(f));

if (caiu.length > 0) {
  console.log(`Caiu abaixo do teto — aperte ${BASELINE_ROTULO} para travar o ganho:`);
  for (const f of caiu) {
    const agora = contagemDe(f);
    if (agora === 0) console.log(`  remova "${f}"   (era ${tetoDe(f)}, zerou)`);
    else console.log(`  "${f}": ${agora},   (era ${tetoDe(f)})`);
  }
  // Com arquivo acima do teto, `--write` também gravaria a subida: só sugere
  // regenerar quando regenerar é apertar.
  if (acima.length === 0) console.log('  (ou regenere: node scripts/check-unknown-casts.mjs --write)');
  console.log('');
}

if (acima.length > 0) {
  console.error(`\u274c Cast inseguro acima do teto de ${BASELINE_ROTULO}`);
  console.error('   (conta `as unknown` e `as never` — toda dupla conversão passa por um deles):\n');
  for (const f of acima) {
    console.error(`  ${f}: ${contagemDe(f)} > teto ${tetoDe(f)}`);
    for (const o of achados.get(f) ?? []) console.error(`    ${f}:${o.linha}  ${o.trecho}`);
  }
  console.error(
    '\nO QUE FAZER:' +
      '\n  1. Tipe a origem: corrija o tipo na fonte (cliente de API, interface, genérico)' +
      '\n     em vez de forçar com cast. Trocar por `as never` não resolve — conta igual.' +
      `\n  2. Cast inevitável (lib sem tipo, fronteira externa): suba o teto DESTE arquivo` +
      `\n     em ${BASELINE_ROTULO} no mesmo PR e justifique no corpo do PR.` +
      '\n  3. Arquivo renomeado/movido: mova a entrada do caminho antigo para o novo no baseline.',
  );
  process.exit(1);
}

console.log(
  `\u2705 ${total} cast(s) inseguro(s) em ${arquivos.length} arquivo(s); ` +
    `${medidos} arquivo(s) medido(s), nenhum acima do teto.`,
);
