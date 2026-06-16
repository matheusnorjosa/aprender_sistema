#!/usr/bin/env node

import { appendFileSync, readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { resolve as resolvePath, join as joinPath } from "node:path";

const targetDir = process.argv[2] ?? ".";
const minScore = Number.parseInt(process.env.REACT_DOCTOR_MIN_SCORE ?? "75", 10);

if (!Number.isFinite(minScore)) {
  console.error("REACT_DOCTOR_MIN_SCORE must be a valid integer.");
  process.exit(2);
}

// react-doctor é pinado como devDependency EXATA (package.json) e travado em package-lock.json,
// incluindo TODA a árvore transitiva. Rodamos o binário LOCAL (não `npx react-doctor@x`, que
// re-resolve os transitivos a cada run e causou drift de score — 0.0.42 marcou 80 em 2026-05-21 e
// 65 em 2026-06-05 com o MESMO código). Invocar via process.execPath + cli.js resolvido do
// node_modules travado = determinístico e cross-platform (sem shell, sem .cmd, sem branch win32).
// Resolve o cli.js a partir do bin do package.json travado (o campo `exports` do react-doctor
// bloqueia subpath deep via require.resolve, então lemos o manifest direto). react-doctor é devDep
// direta → fica no node_modules de topo de <targetDir>.
//
// `--offline` é OBRIGATÓRIO para o determinismo: sem ele, o react-doctor consulta um serviço de
// telemetria remoto que ENTRA no cálculo do score (`--help`: "skip telemetry ... only used to
// calculate score"). Online, o mesmo código pontua 64 (com rede, ex: CI) ou 86 (offline); o número
// remoto driftou 80→65 ao longo de semanas sem mudança de código. `--offline` força a análise
// estática 100% local (árvore travada no lockfile) → score reproduzível e independente de rede.
const pkgDir = joinPath(resolvePath(targetDir), "node_modules", "react-doctor");
const binField = JSON.parse(readFileSync(joinPath(pkgDir, "package.json"), "utf8")).bin;
const binRel = typeof binField === "string" ? binField : binField["react-doctor"];
const cliPath = joinPath(pkgDir, binRel);
const run = spawnSync(process.execPath, [cliPath, targetDir, "--score", "--yes", "--offline"], {
  encoding: "utf8",
  stdio: ["inherit", "pipe", "pipe"],
});

const output = `${run.stdout ?? ""}${run.stderr ?? ""}`;
process.stdout.write(output);

if (run.error) {
  console.error(`Failed to run React Doctor: ${run.error.message}`);
  process.exit(1);
}

if (run.status !== 0) {
  console.error(`React Doctor exited with status ${run.status}.`);
  process.exit(run.status ?? 1);
}

const stripAnsi = (text) => text.replace(/\u001b\[[0-9;]*m/g, "");
const normalized = stripAnsi(output);
const lines = normalized
  .split(/\r?\n/)
  .map((line) => line.trim())
  .filter(Boolean);
const scoreText = [...lines].reverse().find((line) => /^\d{1,3}$/.test(line));

if (!scoreText) {
  console.error("Could not parse React Doctor score from output.");
  process.exit(1);
}

const score = Number.parseInt(scoreText, 10);

if (process.env.GITHUB_OUTPUT) {
  appendFileSync(process.env.GITHUB_OUTPUT, `react_doctor_score=${score}\n`);
}

console.log(`React Doctor score parsed: ${score}`);
console.log(`React Doctor minimum required: ${minScore}`);

if (score < minScore) {
  console.error(`React Doctor score ${score} is below required minimum ${minScore}.`);
  process.exit(1);
}

console.log("React Doctor quality gate passed.");
