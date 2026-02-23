#!/usr/bin/env node

import { appendFileSync } from "node:fs";
import { spawnSync } from "node:child_process";

const targetDir = process.argv[2] ?? ".";
const minScore = Number.parseInt(process.env.REACT_DOCTOR_MIN_SCORE ?? "75", 10);

if (!Number.isFinite(minScore)) {
  console.error("REACT_DOCTOR_MIN_SCORE must be a valid integer.");
  process.exit(2);
}

const doctorArgs = ["-y", "react-doctor@latest", targetDir, "--score", "--yes"];
const run =
  process.platform === "win32"
    ? spawnSync("cmd.exe", ["/d", "/s", "/c", "npx", ...doctorArgs], {
        encoding: "utf8",
        stdio: ["inherit", "pipe", "pipe"],
      })
    : spawnSync("npx", doctorArgs, {
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
