#!/usr/bin/env node
/**
 * Guard de migração TypeScript (#477).
 *
 * A migração está concluída — código de produção em src/ é 100% .ts/.tsx.
 * Este guard TRAVA a regressão: falha o CI se aparecer QUALQUER .js/.jsx de
 * produção em src/. Testes e infra de teste ficam na allowlist até serem
 * convertidos (arquivos *.test.* / *.spec.*, diretórios __tests__/, e src/test/).
 *
 * Uso: node scripts/check-no-legacy-js.mjs   (exit 1 se achar legado)
 */
import { readdirSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const SRC = fileURLToPath(new URL('../src', import.meta.url));

/** @param {string} name */
const isTestFile = (name) => /\.(test|spec)\.[jt]sx?$/.test(name);
/** @param {string} rel */
const inTestInfra = (rel) => rel === 'test' || rel.startsWith('test/');

/** @type {string[]} */
const offenders = [];

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
    if (isTestFile(name) || inTestInfra(rel)) continue;
    if (/\.(js|jsx)$/.test(name)) offenders.push('src/' + rel);
  }
}

walk(SRC);

if (offenders.length > 0) {
  console.error('\u274c Migracao TS (#477): .js/.jsx de PRODUCAO encontrados em src/:');
  for (const f of offenders.sort()) console.error('   ' + f);
  console.error('\nProducao deve ser 100% TypeScript. Renomeie para .ts/.tsx.');
  process.exit(1);
}

console.log('\u2705 Nenhum .js/.jsx de producao em src/ (migracao TS trancada).');
