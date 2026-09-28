/**
 * Relatório do frontend comentado no PR (job `[info] frontend PR report` do
 * frontend-ci.yml). Sem dependências: roda num checkout esparso de scripts/.
 *
 * Uso: node scripts/pr-report.mjs <size-limit.json> <lighthouse-summary.json>
 *   - size-limit.json: saída de `npx size-limit --json` (lista de
 *     { name, passed, size, sizeLimit }, tamanhos em bytes).
 *   - lighthouse-summary.json: `.lighthouseci/summary.json`, gravado por
 *     scripts/lighthouse-ci.mjs.
 *
 * Imprime markdown no stdout. Arquivo ausente ou ilegível vira a seção
 * "Indisponível" com o motivo — o relatório sai mesmo assim.
 *
 * A 1ª linha é o marcador com que o job acha o próprio comentário para
 * atualizá-lo; se mudar aqui, mude o `MARKER` do job junto.
 *
 * Env (opcional): HEAD_SHA; GITHUB_SERVER_URL, GITHUB_REPOSITORY e
 * GITHUB_RUN_ID (link do run — o runner já define).
 */
import { readFileSync } from 'node:fs';
import path from 'node:path';
import process from 'node:process';

const MARKER = '<!-- as-frontend-report -->';

const METRIC_LABELS = {
  'largest-contentful-paint': 'LCP',
  'total-blocking-time': 'TBT',
  'cumulative-layout-shift': 'CLS',
};

function fmt(value, maxDigits) {
  if (typeof value !== 'number') {
    return 'n/d';
  }
  return value.toLocaleString('pt-BR', { maximumFractionDigits: maxDigits });
}

function kb(bytes) {
  return typeof bytes === 'number' ? `${fmt(bytes / 1000, 1)} kB` : '—';
}

function readJson(file) {
  const name = path.basename(String(file));
  try {
    return { data: JSON.parse(readFileSync(file, 'utf8')) };
  } catch (error) {
    if (error?.code === 'ENOENT') {
      return { reason: `arquivo não encontrado (\`${name}\`)` };
    }
    return { reason: `arquivo ilegível (\`${name}\`): ${error?.message ?? error}` };
  }
}

function unavailable(title, reason, origin) {
  return [title, '', `**Indisponível:** ${reason}.`, '', origin];
}

function sizeSection(file) {
  const title = '### Tamanho do bundle (size-limit)';
  const { data, reason } = readJson(file);
  if (reason || !Array.isArray(data)) {
    return unavailable(
      title,
      reason ?? 'formato inesperado (esperava a lista do `size-limit --json`)',
      'Vem do job `[required] build/lint do frontend`; falta quando o build não passou.',
    );
  }

  const lines = [title, '', '| Entrada | Tamanho | Limite | Uso | Situação |', '| --- | ---: | ---: | ---: | --- |'];
  for (const entry of data) {
    const usage =
      typeof entry.size === 'number' && typeof entry.sizeLimit === 'number' && entry.sizeLimit > 0
        ? `${fmt((entry.size / entry.sizeLimit) * 100, 1)}%`
        : '—';
    const status = entry.passed === false ? 'estourou' : entry.passed === true ? 'ok' : 'sem limite';
    lines.push(`| ${entry.name} | ${kb(entry.size)} | ${kb(entry.sizeLimit)} | ${usage} | ${status} |`);
  }
  return lines;
}

function assertionList(title, items) {
  if (!items.length) {
    return [`${title}: nenhuma.`];
  }
  return [`${title}:`, ...items.map((item) => `- \`${item.label}\`: ${item.observed}`)];
}

function lighthouseSection(file) {
  const title = '### Lighthouse';
  const { data, reason } = readJson(file);
  if (reason || typeof data?.categories !== 'object' || typeof data?.checks !== 'object') {
    return unavailable(
      title,
      reason ?? 'formato inesperado (esperava o `summary.json` do lighthouse-ci.mjs)',
      'Vem do job `[info] lighthouse CI`; falta quando o job não rodou ou quebrou antes de medir.',
    );
  }

  const checks = [
    ...(data.checks.errors ?? []).map((check) => ({ ...check, blocking: true })),
    ...(data.checks.warnings ?? []).map((check) => ({ ...check, blocking: false })),
  ];
  const failures = data.failures ?? [];
  const warnings = data.warnings ?? [];
  const verdict = failures.length ? 'reprovou' : 'passou';

  const lines = [
    title,
    '',
    `**Resultado:** ${verdict} — ${failures.length} falha(s), ${warnings.length} aviso(s); média de ${data.runs ?? '?'} execução(ões).`,
    '',
    '| Categoria | Nota | Mínimo | Situação |',
    '| --- | ---: | ---: | --- |',
  ];
  for (const [id, score] of Object.entries(data.categories)) {
    const check = checks.find((c) => c.type === 'categoryMin' && c.id === id);
    let status = '—';
    if (typeof score === 'number' && check) {
      status = score >= check.min ? 'ok' : check.blocking ? 'reprovou' : 'aviso';
    }
    const min = check ? fmt(check.min * 100, 1) : '—';
    lines.push(`| ${id} | ${typeof score === 'number' ? fmt(score * 100, 1) : 'n/d'} | ${min} | ${status} |`);
  }

  lines.push('', '| Métrica | Valor | Limite | Situação |', '| --- | ---: | ---: | --- |');
  for (const [id, value] of Object.entries(data.metrics ?? {})) {
    const check = checks.find((c) => c.type === 'auditMax' && c.id === id);
    const unit = id === 'cumulative-layout-shift' ? '' : ' ms';
    const digits = id === 'cumulative-layout-shift' ? 3 : 0;
    let status = '—';
    if (typeof value === 'number' && check) {
      status = value <= check.max ? 'ok' : 'estourou';
    }
    const limit = check ? `${fmt(check.max, digits)}${unit}` : '—';
    const shown = typeof value === 'number' ? `${fmt(value, digits)}${unit}` : 'n/d';
    lines.push(`| ${METRIC_LABELS[id] ?? id} | ${shown} | ${limit} | ${status} |`);
  }

  lines.push('', ...assertionList('Falhas (reprovam o Lighthouse)', failures));
  lines.push('', ...assertionList('Avisos', warnings));
  return lines;
}

function header() {
  const sha = (process.env.HEAD_SHA ?? '').slice(0, 7) || 'n/d';
  const { GITHUB_SERVER_URL: server, GITHUB_REPOSITORY: repo, GITHUB_RUN_ID: runId } = process.env;
  const run = server && repo && runId ? `[run do CI](${server}/${repo}/actions/runs/${runId})` : 'run local';
  return [
    MARKER,
    '## Relatório do frontend',
    '',
    `Commit \`${sha}\` · ${run} · este comentário é atualizado a cada push.`,
  ];
}

const [sizeFile, lighthouseFile] = process.argv.slice(2);
const report = [...header(), '', ...sizeSection(sizeFile), '', ...lighthouseSection(lighthouseFile)];
process.stdout.write(`${report.join('\n')}\n`);
