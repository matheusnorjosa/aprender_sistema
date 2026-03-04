import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const repoRoot = resolve(__dirname, '..', '..');
const composeFile = resolve(repoRoot, 'infra', 'docker-compose.yml');
const composePrefix = ['compose', '-p', 'aprender_v2', '-f', composeFile];

const testArgs = process.argv.slice(2);
const finalTestArgs = testArgs.length > 0 ? testArgs : ['--project=chromium', '--reporter=line'];

function sleep(ms) {
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);
}

function shellEscape(value) {
  return `'${String(value).replace(/'/g, `'\"'\"'`)}'`;
}

function runCommand(command, args, { allowFailure = false, quiet = false } = {}) {
  const result = spawnSync(command, args, {
    stdio: quiet ? 'pipe' : 'inherit',
    encoding: 'utf-8',
    env: process.env,
  });

  if (result.error) {
    throw result.error;
  }

  if (result.status !== 0 && !allowFailure) {
    throw new Error(`${command} ${args.join(' ')} failed with exit code ${result.status}`);
  }

  return result;
}

function runCompose(args, options) {
  return runCommand('docker', [...composePrefix, ...args], options);
}

function waitForDbReady(maxAttempts = 40, delayMs = 2000) {
  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    const probe = runCompose(
      ['exec', '-T', 'db', 'sh', '-lc', 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'],
      { allowFailure: true, quiet: true }
    );
    if (probe.status === 0) {
      return;
    }
    sleep(delayMs);
  }
  throw new Error('PostgreSQL did not become ready in time.');
}

try {
  console.log('[e2e-docker] starting required services (db, redis, web)...');
  runCompose(['up', '-d', 'db', 'redis', 'web']);

  console.log('[e2e-docker] waiting for database readiness...');
  waitForDbReady();

  console.log('[e2e-docker] applying migrations...');
  runCompose(['exec', '-T', 'web', 'python', 'manage.py', 'migrate', '--noinput']);

  console.log('[e2e-docker] seeding E2E users...');
  runCompose(['exec', '-T', 'web', 'python', 'manage.py', 'seed_e2e_users']);

  const playwrightArgString = finalTestArgs.map(shellEscape).join(' ');
  const runnerCmd = [
    'npm ci',
    `npm run test:e2e -- ${playwrightArgString}`,
  ].join(' && ');

  console.log('[e2e-docker] running Playwright in canonical runner (frontend-e2e)...');
  runCompose(['run', '--rm', 'frontend-e2e', 'bash', '-lc', runnerCmd]);

  console.log('[e2e-docker] success.');
} catch (error) {
  console.error(`[e2e-docker] failed: ${error.message}`);
  process.exit(1);
}
