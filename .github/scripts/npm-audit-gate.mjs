// Gate de dependencias de producao do frontend (`[required] Frontend Dependencies`).
//
// Por que existe em vez do `node -e` de uma linha que havia antes:
// o `npm audit` conta PACOTES vulneraveis, nao ADVISORIES. Corrigir uma
// vulnerabilidade real pode AUMENTAR o contador — foi o que aconteceu ao subir
// react-router 7.17.0 -> 7.18.2: as advisories chx6 (DoS) e wrjc (open redirect)
// foram corrigidas, mas `high` foi de 1 para 2, porque `react-router-dom` passou
// a ser contado junto com `react-router` pela mesma advisory remanescente.
// Um gate que le so `metadata.vulnerabilities.high` nao consegue distinguir
// "corrigiram algo" de "piorou", nem conceder excecao a uma advisory especifica.
//
// Este script resolve as advisories transitivas (o campo `via` pode conter o NOME
// de outro pacote vulneravel em vez do objeto da advisory) e so bloqueia quando
// sobra ao menos uma advisory HIGH/CRITICAL fora da allowlist.
//
// Codigos de saida (contrato preservado do parser anterior):
//   0  = gate passou
//   10 = HIGH/CRITICAL bloqueante encontrada
//   2  = relatorio ausente/ilegivel
//   3  = npm audit devolveu erro de API

import { readFileSync } from "node:fs";

// ---------------------------------------------------------------------------
// Advisories aceitas conscientemente (TTL — revisar trimestralmente,
// proxima revisao 2026-10-30). Mesmo padrao ja usado no gate Python
// (`pip-audit --ignore-vuln`, security-scan.yml).
//
// Cada entrada precisa de: por que nao se aplica AQUI e qual o plano de saida.
// ---------------------------------------------------------------------------
const ADVISORIES_ACEITAS = new Map([
  [
    "GHSA-qwww-vcr4-c8h2",
    {
      pacote: "react-router",
      motivo:
        "CSRF bypass no RSC Mode (React Server Components). Este frontend e' " +
        "SPA cliente puro: build `tsc --noEmit && vite build`, roteamento por " +
        "<BrowserRouter>, sem @react-router/*, sem entrypoint SSR e a imagem de " +
        "producao so serve /dist por nginx. Nao existe RSC em execucao, entao o " +
        "vetor nao e' alcancavel.",
      saida:
        "sem correcao no pacote em uso: react-router-dom nao tem linha 8.x " +
        "publicada (ultima e' 7.18.2, ja adotada). O patch so existe em " +
        "react-router 8.3.0, que exige React >= 19.2.7 — o projeto esta no " +
        "React 18.3.1. Remover esta excecao ao concluir o upgrade para " +
        "React 19 (issue #1675).",
    },
  ],
]);

const CAMINHO = process.argv[2] ?? "npm-audit-report.json";
const BLOQUEANTES = new Set(["high", "critical"]);

let relatorio;
try {
  relatorio = JSON.parse(readFileSync(CAMINHO, "utf8"));
} catch {
  process.exit(2);
}

if (relatorio?.error) {
  const detalhe =
    relatorio.error.summary || relatorio.error.message || "desconhecido";
  console.log(`npm audit reportou erro de API: ${detalhe}`);
  process.exit(3);
}

const vulnerabilidades = relatorio?.vulnerabilities;
if (!vulnerabilidades || typeof vulnerabilidades !== "object") {
  // Sem o mapa detalhado nao da' para raciocinar por advisory. Fail-closed:
  // se o metadata acusa HIGH/CRITICAL, bloqueia; senao trata como ausente.
  const meta = relatorio?.metadata?.vulnerabilities;
  if (!meta) process.exit(2);
  const total = Number(meta.high || 0) + Number(meta.critical || 0);
  console.log(`npm audit (prod) sem detalhamento; metadata high+critical=${total}`);
  process.exit(total > 0 ? 10 : 0);
}

/**
 * Coleta as advisories HIGH/CRITICAL de um pacote, seguindo `via` transitivo.
 * `via` traz ora o objeto da advisory, ora o NOME de outro pacote vulneravel.
 */
function coletarAdvisories(nomePacote, vistos = new Set()) {
  if (vistos.has(nomePacote)) return [];
  vistos.add(nomePacote);

  const entrada = vulnerabilidades[nomePacote];
  if (!entrada) return [];

  const encontradas = [];
  for (const via of entrada.via ?? []) {
    if (typeof via === "string") {
      encontradas.push(...coletarAdvisories(via, vistos));
      continue;
    }
    if (!BLOQUEANTES.has(via?.severity)) continue;
    const id = String(via.url ?? "").split("/").pop() || via.source || "?";
    encontradas.push({ id, titulo: via.title ?? "", severidade: via.severity });
  }
  return encontradas;
}

const bloqueiam = [];
const dispensadas = [];

for (const [nome, entrada] of Object.entries(vulnerabilidades)) {
  if (!BLOQUEANTES.has(entrada?.severity)) continue;

  const advisories = coletarAdvisories(nome);
  // Sem advisory identificavel nao ha como conceder excecao: bloqueia.
  if (advisories.length === 0) {
    bloqueiam.push({ pacote: nome, id: "(advisory nao identificada)", titulo: "" });
    continue;
  }

  for (const adv of advisories) {
    const alvo = ADVISORIES_ACEITAS.has(adv.id) ? dispensadas : bloqueiam;
    alvo.push({ pacote: nome, ...adv });
  }
}

const meta = relatorio?.metadata?.vulnerabilities ?? {};
console.log(
  `npm audit (prod) pacotes: high=${Number(meta.high || 0)} ` +
    `critical=${Number(meta.critical || 0)}`,
);

if (dispensadas.length > 0) {
  console.log("\nAdvisories aceitas conscientemente (TTL 2026-10-30):");
  for (const d of new Map(dispensadas.map((x) => [x.id, x])).values()) {
    const ctx = ADVISORIES_ACEITAS.get(d.id);
    console.log(`  - ${d.id} (${ctx.pacote}): ${d.titulo}`);
    console.log(`    motivo: ${ctx.motivo}`);
    console.log(`    saida : ${ctx.saida}`);
  }
}

if (bloqueiam.length > 0) {
  console.error("\nGate de dependencias de producao REPROVADO:");
  for (const b of bloqueiam) {
    console.error(`  - [${b.severidade ?? "?"}] ${b.pacote}: ${b.id} ${b.titulo}`);
  }
  process.exit(10);
}

console.log("\nGate de dependencias de producao aprovado.");
process.exit(0);
