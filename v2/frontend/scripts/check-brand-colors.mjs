#!/usr/bin/env node
/**
 * Guard de SSOT de cor de marca (Fase 2 — Robustez do Frontend).
 *
 * As cores de MARCA distintas moram em `BRAND_COLORS` (src/contexts/ThemeContext.tsx)
 * e são aplicadas via `ConfigProvider` do AntD + import direto do token. Este guard
 * TRAVA a regressão: falha o CI se algum componente hardcodar um dos verdes de marca
 * em vez de usar `BRAND_COLORS.*`. Assim a cor da marca tem uma fonte única — trocar
 * o verde no SSOT propaga para todo lugar.
 *
 * Escopo: só os 3 verdes DISTINTOS da marca (primary/primaryDark/primaryLight). Não
 * mexe em paletas de chart/mapa/status nem em cores genéricas (#fff, status AntD) —
 * essas são legítimas hardcoded.
 *
 * Uso: node scripts/check-brand-colors.mjs   (exit 1 se achar hardcode)
 */
import { readdirSync, statSync, readFileSync } from 'node:fs';
import { join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const SRC = fileURLToPath(new URL('../src', import.meta.url));

// Verdes de marca (= BRAND_COLORS.primary / primaryDark / primaryLight / sidebarBackground).
const BRAND_GREENS = /#(006B52|004B3D|E5EDE5)\b/i;

// O SSOT é o único lugar onde esses literais podem existir.
const SSOT = 'contexts/ThemeContext.tsx';

/** @param {string} name */
const isTestFile = (name) => /\.(test|spec)\.[jt]sx?$/.test(name);
/** @param {string} rel */
const inTestInfra = (rel) => rel === 'test' || rel.startsWith('test/');

/** @type {{ file: string, line: number, text: string }[]} */
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
    if (!/\.(ts|tsx)$/.test(name)) continue;
    if (isTestFile(name) || inTestInfra(rel) || rel === SSOT) continue;

    const lines = readFileSync(abs, 'utf8').split('\n');
    lines.forEach((text, i) => {
      if (BRAND_GREENS.test(text)) {
        offenders.push({ file: 'src/' + rel, line: i + 1, text: text.trim() });
      }
    });
  }
}

walk(SRC);

if (offenders.length > 0) {
  console.error('\u274c SSOT de cor de marca: verde de marca hardcodado (use BRAND_COLORS.*):');
  for (const o of offenders) {
    console.error(`   ${o.file}:${o.line}  ${o.text}`);
  }
  console.error(
    '\nImporte de `contexts/ThemeContext`: BRAND_COLORS.primary / .primaryDark / .primaryLight.',
  );
  process.exit(1);
}

console.log('\u2705 Nenhum verde de marca hardcodado fora do SSOT (BRAND_COLORS trancado).');
