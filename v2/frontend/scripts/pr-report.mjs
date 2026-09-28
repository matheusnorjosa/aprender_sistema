/**
 * Relatório do frontend comentado no PR (job `[info] frontend PR report` do
 * frontend-ci.yml) e, com `--mensal`, na issue de acompanhamento mensal
 * (frontend-metrics-monthly.yml). Sem dependências: roda num checkout esparso
 * de scripts/.
 *
 * Uso: node scripts/pr-report.mjs [--mensal [--anteriores <comentarios.jsonl>]]
 *        <size-limit.json> <lighthouse-summary.json>
 *   - size-limit.json: saída de `npx size-limit --json` (lista de
 *     { name, passed, size, sizeLimit }, tamanhos em bytes).
 *   - lighthouse-summary.json: `.lighthouseci/summary.json`, gravado por
 *     scripts/lighthouse-ci.mjs.
 *   - --mensal: título de acompanhamento mensal, linha de comparação com a
 *     medição anterior no topo e, no fim, os números num comentário HTML oculto
 *     (é dele que as medições seguintes leem a comparação).
 *   - --anteriores: os comentários mensais anteriores, um JSON
 *     `{ created_at, body }` por linha (o que o workflow tira da API). Por
 *     métrica, a base é o valor não nulo mais recente. Vazio, ausente ou sem
 *     nenhum bloco de números vira "sem medição anterior".
 *
 * Imprime markdown no stdout. Arquivo ausente ou ilegível vira a seção
 * "Indisponível" com o motivo — o relatório sai mesmo assim.
 *
 * A 1ª linha é o marcador com que o workflow acha o próprio comentário; se
 * mudar aqui, mude o `MARKER` do workflow junto (o auto-teste confere).
 *
 * Env (opcional): HEAD_SHA; GITHUB_SERVER_URL, GITHUB_REPOSITORY e
 * GITHUB_RUN_ID (link do run — o runner já define).
 */
import { readFileSync } from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { parseArgs } from 'node:util';

const MODOS = {
  pr: {
    marcador: '<!-- as-frontend-report -->',
    titulo: '## Relatório do frontend',
    nota: 'este comentário é atualizado a cada push.',
    origemSize: 'Vem do job `[required] build/lint do frontend`; falta quando o build não passou.',
    origemLighthouse: 'Vem do job `[info] lighthouse CI`; falta quando o job não rodou ou quebrou antes de medir.',
  },
  mensal: {
    marcador: '<!-- as-frontend-monthly -->',
    titulo: '## Acompanhamento mensal do frontend',
    nota: 'medição agendada da `main`; não bloqueia merge.',
    origemSize: 'Vem do passo de size-limit do workflow mensal; falta quando o build não passou.',
    origemLighthouse: 'Vem do passo de Lighthouse do workflow mensal; falta quando ele quebrou antes de medir.',
  },
};

// Números que o modo mensal grava e compara. `js` é a entrada do
// .size-limit.json cujo nome começa com JS_ENTRADA: soma gzip de todos os
// `dist/assets/*.js`, chunks lazy das páginas inclusive; só o GeoJSON
// `brazil-states-*` fica de fora. `valor` converte como as tabelas abaixo.
const DADOS = 'as-frontend-monthly-dados';
const JS_ENTRADA = 'JS Bundle';
const COMPARADOS = [
  { chave: 'performance', rotulo: 'performance', valor: (nota) => nota * 100, digitos: 1, unidade: '' },
  { chave: 'lcp', rotulo: 'LCP', valor: (ms) => ms, digitos: 0, unidade: ' ms' },
  { chave: 'js', rotulo: 'JS', valor: (bytes) => bytes / 1000, digitos: 1, unidade: ' kB' },
];

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

function sizeSection(file, origin) {
  const title = '### Tamanho do bundle (size-limit)';
  const { data, reason } = readJson(file);
  if (reason || !Array.isArray(data)) {
    return unavailable(
      title,
      reason ?? 'formato inesperado (esperava a lista do `size-limit --json`)',
      origin,
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

function assertionList(title, items, none) {
  if (!items.length) {
    return [`${title}: ${none}.`];
  }
  return [`${title}:`, ...items.map((item) => `- \`${item.label}\`: ${item.observed}`)];
}

function lighthouseSection(file, origin) {
  const title = '### Lighthouse';
  const { data, reason } = readJson(file);
  if (reason || typeof data?.categories !== 'object' || typeof data?.checks !== 'object') {
    return unavailable(
      title,
      reason ?? 'formato inesperado (esperava o `summary.json` do lighthouse-ci.mjs)',
      origin,
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

  lines.push('', ...assertionList('Falhas (reprovam o Lighthouse)', failures, 'nenhuma'));
  lines.push('', ...assertionList('Avisos', warnings, 'nenhum'));
  return lines;
}

function header(modo) {
  const sha = (process.env.HEAD_SHA ?? '').slice(0, 7) || 'n/d';
  const { GITHUB_SERVER_URL: server, GITHUB_REPOSITORY: repo, GITHUB_RUN_ID: runId } = process.env;
  const run = server && repo && runId ? `[run do CI](${server}/${repo}/actions/runs/${runId})` : 'run local';
  return [modo.marcador, modo.titulo, '', `Commit \`${sha}\` · ${run} · ${modo.nota}`];
}

/** Números desta medição; `null` no que faltou (build ou Lighthouse quebrado). */
function numeros(sizeFile, lighthouseFile) {
  const size = readJson(sizeFile).data;
  const lighthouse = readJson(lighthouseFile).data;
  const js = Array.isArray(size) ? size.find((entry) => String(entry?.name).startsWith(JS_ENTRADA)) : undefined;
  const numero = (value) => (typeof value === 'number' ? value : null);
  return {
    performance: numero(lighthouse?.categories?.performance),
    lcp: numero(lighthouse?.metrics?.['largest-contentful-paint']),
    js: numero(js?.size),
  };
}

/**
 * Medições gravadas nos comentários mensais anteriores, da mais recente para a
 * mais antiga: `{ em, numeros }`. Linha ilegível, sem data ou sem o bloco de
 * números fica de fora.
 */
function medicoesAnteriores(file) {
  let texto = '';
  try {
    texto = file ? readFileSync(file, 'utf8') : '';
  } catch {
    // Sem o arquivo, sem base: o relatório sai com "sem medição anterior".
  }
  const medicoes = [];
  for (const linha of texto.split('\n')) {
    try {
      const { created_at: criado, body } = JSON.parse(linha);
      const em = Date.parse(criado);
      const achado = String(body).match(new RegExp(`<!-- ${DADOS} (\\{.*?\\}) -->`));
      if (achado && !Number.isNaN(em)) {
        medicoes.push({ em, numeros: JSON.parse(achado[1]) });
      }
    } catch {
      // Linha vazia, JSON quebrado ou bloco editado à mão: não serve de base.
    }
  }
  return medicoes.sort((a, b) => b.em - a.em);
}

function dia(em) {
  return new Date(em).toLocaleDateString('pt-BR', { timeZone: 'America/Fortaleza' });
}

/**
 * A variação sai dos valores já arredondados que a linha mostra, para ela
 * nunca se contradizer. A data do título é a da medição anterior; métrica que
 * faltou nela compara com a última medição que a tem, e leva a própria data.
 */
function comparacao(atual, anteriores) {
  if (!anteriores.length) {
    return '**Contra a medição anterior:** sem medição anterior.';
  }
  const partes = COMPARADOS.map(({ chave, rotulo, valor, digitos, unidade }) => {
    const base = anteriores.find((medicao) => typeof medicao.numeros[chave] === 'number');
    if (!base || typeof atual[chave] !== 'number') {
      return `${rotulo} n/d`;
    }
    const arredonda = (numero) => Number(numero.toFixed(digitos));
    const antes = arredonda(valor(base.numeros[chave]));
    const agora = arredonda(valor(atual[chave]));
    const delta = arredonda(agora - antes).toLocaleString('pt-BR', {
      maximumFractionDigits: digitos,
      signDisplay: 'exceptZero',
    });
    const de = base === anteriores[0] ? '' : ` (${dia(base.em)})`;
    return `${rotulo} ${fmt(antes, digitos)}${de} → ${fmt(agora, digitos)}${unidade} (${delta}${unidade})`;
  });
  return `**Contra a medição anterior (${dia(anteriores[0].em)}):** ${partes.join(' · ')}.`;
}

const { values: opcoes, positionals } = parseArgs({
  allowPositionals: true,
  options: { mensal: { type: 'boolean' }, anteriores: { type: 'string' } },
});
const [sizeFile, lighthouseFile] = positionals;
const modo = opcoes.mensal ? MODOS.mensal : MODOS.pr;

const topo = header(modo);
const atual = opcoes.mensal ? numeros(sizeFile, lighthouseFile) : null;
if (atual) {
  topo.push('', comparacao(atual, medicoesAnteriores(opcoes.anteriores)));
}
const report = [
  ...topo,
  '',
  ...sizeSection(sizeFile, modo.origemSize),
  '',
  ...lighthouseSection(lighthouseFile, modo.origemLighthouse),
];
if (atual) {
  report.push('', `<!-- ${DADOS} ${JSON.stringify(atual)} -->`);
}
process.stdout.write(`${report.join('\n')}\n`);
