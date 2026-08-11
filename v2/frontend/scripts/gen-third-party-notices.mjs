#!/usr/bin/env node
/**
 * Gera THIRD-PARTY-NOTICES.txt com a atribuição de licenças das dependências de
 * PRODUÇÃO do bundle do frontend (o artefato distribuído aos navegadores).
 *
 * LGPD/compliance de licenças: MIT/BSD/Apache/ISC exigem preservar copyright + texto
 * da licença no que se distribui. Este arquivo cumpre essa atribuição. Dev-only deps
 * (vitest, eslint, etc.) NÃO são distribuídas → ficam de fora (`npm ls --omit=dev`).
 *
 * Regenerar:  npm run notices  (rodar sobre uma árvore `npm ci`, ex.: dentro do
 * container do frontend — um `node_modules` com dedupe divergente do lockfile pode
 * omitir deps hoisted como tslib. Determinístico: ordena por nome@versão, sem timestamps.)
 */

import { execSync } from 'node:child_process';
import { existsSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

// Raiz do frontend: por padrão, o diretório-pai deste script; sobrescrevível por
// NOTICES_DIR (usado ao rodar dentro do container, onde node_modules é o autoritativo
// de `npm ci` — o que de fato vai pro bundle).
const FRONTEND_DIR = process.env.NOTICES_DIR || join(dirname(fileURLToPath(import.meta.url)), '..');
// Em public/ para o Vite servir o aviso JUNTO com o bundle distribuído (a atribuição
// viaja com o artefato entregue ao navegador — /THIRD-PARTY-NOTICES.txt). `NOTICES_OUT`
// permite redirecionar o destino (ex.: gerar dentro do container, cujo public/ é ro).
const OUT_FILE = process.env.NOTICES_OUT || join(FRONTEND_DIR, 'public', 'THIRD-PARTY-NOTICES.txt');

/** Caminhos de cada dep de produção (transitivo), via npm. */
function prodDepPaths() {
  // `npm ls` sai com código != 0 em qualquer warning (peer dep, dedupe) mas ainda
  // imprime a árvore no stdout — capturamos o stdout mesmo quando execSync lança.
  let raw = '';
  try {
    raw = execSync('npm ls --omit=dev --all --parseable', {
      cwd: FRONTEND_DIR,
      encoding: 'utf8',
      maxBuffer: 64 * 1024 * 1024,
    });
  } catch (e) {
    raw = (e && e.stdout) || '';
  }
  return [...new Set(raw.split('\n').map((l) => l.trim()))]
    .filter(Boolean)
    .filter((p) => p.includes(`node_modules`));
}

function normalizeLicense(pkg) {
  if (typeof pkg.license === 'string') return pkg.license;
  if (pkg.license && typeof pkg.license === 'object' && pkg.license.type) return pkg.license.type;
  if (Array.isArray(pkg.licenses)) return pkg.licenses.map((l) => l.type || l).join(' OR ');
  return 'UNKNOWN';
}

function licenseText(dir) {
  let file;
  try {
    file = readdirSync(dir).find((f) => /^(licen[cs]e|copying|notice)/i.test(f));
  } catch {
    return '';
  }
  if (!file) return '';
  try {
    return readFileSync(join(dir, file), 'utf8').trim();
  } catch {
    return '';
  }
}

function authorOf(pkg) {
  if (typeof pkg.author === 'string') return pkg.author;
  if (pkg.author && typeof pkg.author === 'object') return pkg.author.name || '';
  return '';
}

const seen = new Map();
for (const dir of prodDepPaths()) {
  const pkgPath = join(dir, 'package.json');
  if (!existsSync(pkgPath)) continue;
  let pkg;
  try {
    pkg = JSON.parse(readFileSync(pkgPath, 'utf8'));
  } catch {
    continue;
  }
  if (!pkg.name || !pkg.version) continue;
  const key = `${pkg.name}@${pkg.version}`;
  if (seen.has(key)) continue;
  seen.set(key, {
    name: pkg.name,
    version: pkg.version,
    license: normalizeLicense(pkg),
    author: authorOf(pkg),
    homepage: pkg.homepage || (pkg.repository && (pkg.repository.url || pkg.repository)) || '',
    text: licenseText(dir),
  });
}

const entries = [...seen.values()].sort((a, b) => a.name.localeCompare(b.name) || a.version.localeCompare(b.version));

// Resumo por licença (determinístico).
const counts = {};
for (const e of entries) counts[e.license] = (counts[e.license] || 0) + 1;
const summary = Object.entries(counts)
  .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
  .map(([lic, n]) => `  ${String(n).padStart(4)}  ${lic}`)
  .join('\n');

const lines = [];
lines.push('THIRD-PARTY NOTICES — Aprender Sistema v2 (frontend)');
lines.push('='.repeat(72));
lines.push('');
lines.push('Este produto inclui software de terceiros. Abaixo, cada dependência de');
lines.push('PRODUÇÃO do bundle distribuído, com sua licença e aviso de copyright.');
lines.push('Dependências de desenvolvimento (testes, lint, build) não são distribuídas');
lines.push('e não constam aqui. Regenerar com: npm run notices');
lines.push('');
lines.push(`Total de componentes: ${entries.length}`);
lines.push('Licenças:');
lines.push(summary);
lines.push('');
lines.push('='.repeat(72));
lines.push('');

for (const e of entries) {
  lines.push(`${e.name}@${e.version}`);
  lines.push(`  Licença: ${e.license}`);
  if (e.author) lines.push(`  Autor: ${e.author}`);
  if (e.homepage) lines.push(`  Origem: ${String(e.homepage).replace(/^git\+/, '')}`);
  lines.push('');
  if (e.text) {
    lines.push(e.text);
  } else {
    lines.push(`(Sem arquivo de licença embutido; identificador SPDX: ${e.license})`);
  }
  lines.push('');
  lines.push('-'.repeat(72));
  lines.push('');
}

writeFileSync(OUT_FILE, lines.join('\n'), 'utf8');
process.stdout.write(`THIRD-PARTY-NOTICES.txt gerado: ${entries.length} componentes de produção.\n`);
