import fs from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';
import { spawn } from 'node:child_process';

import { launch } from 'chrome-launcher';
import lighthouse from 'lighthouse';

const RUNS = Number(process.env.LIGHTHOUSE_RUNS ?? '3');
const URL = process.env.LIGHTHOUSE_URL ?? 'http://127.0.0.1:4173/';
const START_SERVER_COMMAND =
  process.env.LIGHTHOUSE_START_SERVER_COMMAND ?? 'npm run preview -- --host 127.0.0.1 --port 4173';
const CHROME_PATH = process.env.CHROME_PATH;
const READY_TIMEOUT_MS = Number(process.env.LIGHTHOUSE_READY_TIMEOUT_MS ?? '60000');
const POLL_INTERVAL_MS = 1000;

const OUTPUT_DIR = path.resolve(process.cwd(), '.lighthouseci');
const JSON_PREFIX = 'lhr';

const CHECKS = {
  errors: [
    { type: 'categoryMin', id: 'performance', min: 0.7, label: 'categories:performance >= 0.7' },
    { type: 'categoryMin', id: 'accessibility', min: 0.9, label: 'categories:accessibility >= 0.9' },
    { type: 'auditMax', id: 'largest-contentful-paint', max: 2500, label: 'largest-contentful-paint <= 2500ms' },
    { type: 'auditMax', id: 'cumulative-layout-shift', max: 0.1, label: 'cumulative-layout-shift <= 0.1' },
    { type: 'auditMax', id: 'total-blocking-time', max: 300, label: 'total-blocking-time <= 300ms' },
    { type: 'auditScore', id: 'color-contrast', min: 1, label: 'color-contrast == pass' },
    { type: 'auditScore', id: 'image-alt', min: 1, label: 'image-alt == pass' },
    { type: 'auditScore', id: 'label', min: 1, label: 'label == pass' },
    { type: 'auditScore', id: 'button-name', min: 1, label: 'button-name == pass' },
    { type: 'auditScore', id: 'link-name', min: 1, label: 'link-name == pass' },
    { type: 'auditScore', id: 'html-has-lang', min: 1, label: 'html-has-lang == pass' },
    { type: 'auditScore', id: 'document-title', min: 1, label: 'document-title == pass' },
    { type: 'auditScore', id: 'meta-viewport', min: 1, label: 'meta-viewport == pass' },
  ],
  warnings: [
    { type: 'categoryMin', id: 'best-practices', min: 0.9, label: 'categories:best-practices >= 0.9' },
    { type: 'categoryMin', id: 'seo', min: 0.9, label: 'categories:seo >= 0.9' },
    { type: 'auditScore', id: 'viewport', min: 1, label: 'viewport == pass' },
    { type: 'auditScore', id: 'charset', min: 1, label: 'charset == pass' },
    { type: 'auditScore', id: 'doctype', min: 1, label: 'doctype == pass' },
  ],
};

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForServer(url, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url, { redirect: 'manual' });
      if (response.ok || (response.status >= 300 && response.status < 400)) {
        return;
      }
    } catch {
      // Retry until timeout.
    }
    await sleep(POLL_INTERVAL_MS);
  }
  throw new Error(`Server did not become ready within ${timeoutMs}ms: ${url}`);
}

function formatScore(value) {
  if (typeof value !== 'number') {
    return 'n/a';
  }
  return value.toFixed(3);
}

function formatNumeric(value) {
  if (typeof value !== 'number') {
    return 'n/a';
  }
  return value.toFixed(2);
}

function average(values) {
  if (!values.length) {
    return null;
  }
  return values.reduce((total, value) => total + value, 0) / values.length;
}

function getCategoryScores(results, categoryId) {
  const values = results
    .map((result) => result.categories?.[categoryId]?.score)
    .filter((value) => typeof value === 'number');
  return values;
}

function getAuditScores(results, auditId) {
  const values = results
    .map((result) => result.audits?.[auditId]?.score)
    .filter((value) => typeof value === 'number');
  return values;
}

function getAuditNumericValues(results, auditId) {
  const values = results
    .map((result) => result.audits?.[auditId]?.numericValue)
    .filter((value) => typeof value === 'number');
  return values;
}

function evaluateCheck(results, check) {
  if (check.type === 'categoryMin') {
    const values = getCategoryScores(results, check.id);
    const avg = average(values);
    if (avg === null) {
      return { passed: true, observed: 'n/a (not reported)' };
    }
    return {
      passed: avg >= check.min,
      observed: `${formatScore(avg)} (target >= ${check.min})`,
    };
  }

  if (check.type === 'auditScore') {
    const values = getAuditScores(results, check.id);
    const avg = average(values);
    if (avg === null) {
      return { passed: true, observed: 'n/a (not applicable)' };
    }
    return {
      passed: avg >= check.min,
      observed: `${formatScore(avg)} (target >= ${check.min})`,
    };
  }

  if (check.type === 'auditMax') {
    const values = getAuditNumericValues(results, check.id);
    const avg = average(values);
    if (avg === null) {
      return { passed: true, observed: 'n/a (not reported)' };
    }
    return {
      passed: avg <= check.max,
      observed: `${formatNumeric(avg)} (target <= ${check.max})`,
    };
  }

  return { passed: true, observed: 'unsupported check type' };
}

function evaluateAssertions(results) {
  const failures = [];
  const warnings = [];

  for (const check of CHECKS.errors) {
    const outcome = evaluateCheck(results, check);
    if (!outcome.passed) {
      failures.push({ label: check.label, observed: outcome.observed });
    }
  }

  for (const check of CHECKS.warnings) {
    const outcome = evaluateCheck(results, check);
    if (!outcome.passed) {
      warnings.push({ label: check.label, observed: outcome.observed });
    }
  }

  return { failures, warnings };
}

async function runSingleLighthouse(url, runIndex) {
  let lastError = null;

  for (let attempt = 1; attempt <= 3; attempt += 1) {
    let chrome;
    try {
      chrome = await launch({
        chromeFlags: ['--headless', '--no-sandbox', '--disable-dev-shm-usage'],
        logLevel: 'error',
        chromePath: CHROME_PATH || undefined,
      });

      const runnerResult = await lighthouse(
        url,
        {
          port: chrome.port,
          output: 'json',
          logLevel: 'error',
          onlyCategories: ['performance', 'accessibility', 'best-practices', 'seo'],
          formFactor: 'desktop',
          screenEmulation: {
            mobile: false,
            width: 1350,
            height: 940,
            deviceScaleFactor: 1,
            disabled: false,
          },
          throttling: {
            cpuSlowdownMultiplier: 2,
          },
        },
        null,
      );

      const lhr = runnerResult?.lhr;
      if (!lhr) {
        throw new Error(`Run ${runIndex}: lighthouse returned empty LHR`);
      }

      await fs.writeFile(path.join(OUTPUT_DIR, `${JSON_PREFIX}-${runIndex}.json`), JSON.stringify(lhr, null, 2), 'utf8');
      return lhr;
    } catch (error) {
      lastError = error;
      const message = error instanceof Error ? error.message : String(error);
      console.warn(`Run ${runIndex} attempt ${attempt} failed: ${message}`);
      await sleep(1000 * attempt);
    } finally {
      if (chrome) {
        try {
          await chrome.kill();
        } catch {
          // Best effort shutdown.
        }
      }
    }
  }

  const reason = lastError instanceof Error ? lastError.message : String(lastError);
  throw new Error(
    `Run ${runIndex} failed after retries. Check Chrome availability in runner (reason: ${reason}).`,
  );
}

async function stopServer(serverProcess) {
  if (!serverProcess || serverProcess.killed) {
    return;
  }

  serverProcess.kill('SIGTERM');
  await new Promise((resolve) => setTimeout(resolve, 2000));

  if (!serverProcess.killed) {
    serverProcess.kill('SIGKILL');
  }
}

function printCategorySummary(results) {
  const categoryIds = ['performance', 'accessibility', 'best-practices', 'seo'];
  console.log('\nLighthouse category averages:');
  for (const categoryId of categoryIds) {
    const avg = average(getCategoryScores(results, categoryId));
    console.log(`- ${categoryId}: ${formatScore(avg)}`);
  }
}

async function main() {
  await fs.rm(OUTPUT_DIR, { recursive: true, force: true });
  await fs.mkdir(OUTPUT_DIR, { recursive: true });

  const serverProcess = spawn(START_SERVER_COMMAND, {
    cwd: process.cwd(),
    env: process.env,
    stdio: 'inherit',
    shell: true,
  });

  try {
    await waitForServer(URL, READY_TIMEOUT_MS);
    console.log(`\nLighthouse target ready: ${URL}`);

    const results = [];
    for (let run = 1; run <= RUNS; run += 1) {
      console.log(`\nRunning Lighthouse (${run}/${RUNS})...`);
      const lhr = await runSingleLighthouse(URL, run);
      results.push(lhr);
    }

    printCategorySummary(results);

    const assertions = evaluateAssertions(results);
    if (assertions.warnings.length) {
      console.log('\nWarning assertions:');
      for (const warning of assertions.warnings) {
        console.log(`- ${warning.label}: ${warning.observed}`);
      }
    }

    if (assertions.failures.length) {
      console.error('\nFailing assertions:');
      for (const failure of assertions.failures) {
        console.error(`- ${failure.label}: ${failure.observed}`);
      }
      process.exitCode = 1;
      return;
    }

    console.log('\nLighthouse assertions passed.');
  } finally {
    await stopServer(serverProcess);
  }
}

await main();
