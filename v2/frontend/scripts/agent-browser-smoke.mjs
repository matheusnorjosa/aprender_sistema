import { spawnSync } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';

const baseUrl = (process.env.AGENT_BROWSER_BASE_URL || 'http://127.0.0.1:4173').replace(/\/$/, '');
const targetPath = process.env.AGENT_BROWSER_TARGET_PATH || '/login';
const outputDir = resolve(process.env.AGENT_BROWSER_OUTPUT_DIR || 'test-results/agent-browser');
const smokeUrl = `${baseUrl}${targetPath.startsWith('/') ? targetPath : `/${targetPath}`}`;
const agentBrowserPackage = process.env.AGENT_BROWSER_NPX_PACKAGE || 'agent-browser@0.15.3';

mkdirSync(outputDir, { recursive: true });

function runAgentBrowser(args, { capture = false, allowFailure = false } = {}) {
  const result = spawnSync(
    'npx',
    ['--yes', agentBrowserPackage, ...args],
    {
      encoding: 'utf-8',
      stdio: capture ? 'pipe' : 'inherit',
      env: process.env,
    }
  );

  if (result.error) {
    throw result.error;
  }

  if (result.status !== 0 && !allowFailure) {
    throw new Error(`agent-browser ${args.join(' ')} failed with exit code ${result.status}`);
  }

  return result;
}

try {
  if (process.env.AGENT_BROWSER_INSTALL === '1') {
    runAgentBrowser(['install', '--with-deps']);
  }

  runAgentBrowser(['open', smokeUrl]);
  runAgentBrowser(['wait', '--load', 'domcontentloaded']);

  const titleResult = runAgentBrowser(['get', 'title'], { capture: true });
  const titleText = titleResult.stdout?.trim() || '';
  writeFileSync(join(outputDir, 'title.txt'), `${titleText}\n`, 'utf-8');

  const snapshotResult = runAgentBrowser(['snapshot'], { capture: true });
  writeFileSync(join(outputDir, 'snapshot.txt'), snapshotResult.stdout || '', 'utf-8');

  runAgentBrowser(['screenshot', join(outputDir, 'smoke-login.png')]);

  console.log(`[agent-browser-smoke] success url=${smokeUrl}`);
} finally {
  runAgentBrowser(['close'], { allowFailure: true });
}
