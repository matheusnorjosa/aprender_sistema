# Projeto: Aprender Sistema (AS) v2

> *Não estamos aqui para escrever código. Estamos aqui para fazer diferença.*

## Stack

- **Backend**: Python 3.12, Django 5.2, DRF, PostgreSQL 15, Redis 7, Docker
- **Frontend**: React 19, Vite 7, Ant Design 5, Tailwind CSS
- **Timezone**: `America/Fortaleza` (UTC storage)
- **Type Checking**: Pyright strict mode (PEP 695)
- **Objetivo**: Substituir 82.389 fórmulas Excel por plataforma web

## Quick Reference

```bash
cd v2 && make up
docker exec aprender_dev-web-1 pytest apps/core/tests/ -v
cd v2/backend && pyright apps/core config
make import-compras-dry FILE=...   # import via API DRF (dry-run); ETL legado REMOVIDO
cd v2 && make seed-e2e && cd frontend && npm run test:e2e -- --project=chromium   # jornadas da CI (v2/frontend/e2e)
# `make test-e2e` roda a suíte legada de v2/tests/playwright (fluxo Google; personas da lotação desde o #2125)
```

## Ferramentas — USO OBRIGATÓRIO

> **REGRA**: Antes de qualquer tarefa, verificar se existe ferramenta adequada.

**Skills**: `aprender-domain`, `django-patterns`,
`writing-standards`, `test-driven-development`,
`create-plan`/`implement-plan`, `continuity-ledger`,
`create-handoff`/`resume-handoff`,
`frontend-ui-engineering`, `performance-optimization`,
`debugging-and-error-recovery`, `deprecation-and-migration`,
`django-security`, `ci-github-actions`
(`etl-guidelines` DEPRECADA — ETL legado removido; ver `specs/backend/imports.spec.md`)

**Commands**: `/project_plan`, `/create-feature`, `/review-enhanced`,
`/approve-flow`, `/check-conflicts`,
`/deploy-staging`, `/project_git-pr`, `/test-coverage`, `/trim`
(`/etl-dry`·`/etl-apply` DEPRECADOS — usar `import_export_contract` / endpoints DRF)

**Agents**: `Explore` (buscar), `Plan` (arquitetar), `general-purpose` (multi-step), `Workflow` (fan-out)

**MCPs (wired)**: `MCP_DOCKER` (playwright, fetch, duckduckgo, dockerhub,
sequentialthinking) · `context7` (docs de libs — `.mcp.json`) · `oraculo-bd` (banco) ·
`multi-model` · `vercel` · Google Calendar.
**Não wired** (as defs antigas em `.claude/settings.json` eram inertes e foram removidas; Claude Code
só lê server-defs de `.mcp.json`, arquivo local e não versionado — `.gitignore`): postgres (use
`docker exec … manage.py dbshell`), github (use `gh` CLI), tree-sitter (use `graphify`), devdocs.

## Cláusulas Pétreas — IMUTÁVEIS

- **CP-01**: v2 roda APENAS em Docker (`cd v2 && make up`)
- **CP-02**: PA-01 a PA-07 — aprovação obrigatória para SUPER
- **CP-03**: RD-01 a RD-08 — disponibilidade com timezone Fortaleza
- **CP-04**: Workflow (Entender, Planejar, Implementar, Testar)
- **CP-05**: v1 congelado (branch `fix/v1-*` + PR para `main-v1`)
- **CP-06**: Conventional commits (`type(scope): message`)
- **CP-07**: Nunca push direto na main — **enforced por hook**
- **CP-08**: `INCLUDE_DEV_TOOLS=false` em produção

## Arquitetura

```text
v2/backend/apps/
  core/           39 models, serializers/, services/
  dev_tools/      15 seed commands (prod disabled)

v2/frontend/src/
  pages/          41 lazy-loaded (AppRoutes.tsx)
  components/     22 reutilizáveis (+ access/, google/, lgpd/)
  hooks/          13 custom hooks
  api/            15 clientes API (fetch) + config.ts + unwrapList.ts
  types/          TypeScript definitions
```

## RBAC

- **Módulo SSOT**: `apps.core.rbac` (DRF permissions, helpers, data-scope constants)
  - Idioma canônico: `permission_classes = [HasPerm("codename")]`
  - Composition: `HasPerm("a") | HasPerm("b")` (OR/AND/NOT)
  - Helpers não-DRF: `user_has_any_perm(user, *codenames)`
  - Convenção completa: `v2/docs/RBAC_NAMING.md`
- **De onde vem o poder (PR 12)**: só da lotação — superuser, pacote do perfil da gerência
  (vínculo EQUIPE/GERENTE vigente), direitos do papel vigente e vínculo GERENTE na Superintendência.
  `settings.RBAC_FONTE` vale `lotacao` por padrão; `uniao` é a volta de emergência. Grupo de setor e
  de função é **etiqueta**: dar grupo não concede acesso. Ver `v2/docs/specs/backend/rbac.spec.md`.
- **Setores (13)**: Superintendência, Vidas, Fluir, ACerta,
  Brincando, Sou da Paz, DAT, Controle, Diretoria, Comercial,
  Relacionamento, Logística Viagens, Logística Galpão
  (SSOT: `apps.core.constants.SETOR_GROUPS`)
- **Funções (5)**: Formador, Coordenador, Apoio de Coordenação, Gerente, Assistente Administrativo
  (SSOT: `apps.core.constants.FUNCAO_GROUPS`; sem capacidade desde o PR 8)
- **Aprovação**: regra única `solicitation_approval_basis` (superuser, GERENTE vigente na Superintendência,
  capacidade `approve_solicitation` pelo pacote ADMIN_OPERACIONAL do DAT ou CONTROLE); ver PA-02 em `v2/docs/specs/domain/politica-aprovacao.spec.md` (nenhum grupo aprova)
- **Lint guard**: `scripts/rbac_lint.py` bane `user.groups.filter(name=...)`
  fora de whitelist. CI job: `[required] backend rbac-lint`.

## Produção (2 VMs)

| VM         | Specs              | Serviços                                                              |
|------------|--------------------|----------------------------------------------------------------------|
| VM01\_App  | 4vCPU/16GB/60GB    | Nginx, Gunicorn, Celery, React, Redis 7 (container `redis`, rede interna) |
| VM02\_DB   | 4vCPU/16GB/300GB   | PostgreSQL 15                                                         |

Redis 7 (cache/sessions/broker) roda como **container na stack da VM01** (serviço `redis`, rede `backend-internal`, sem porta no host) — não é mais VM dedicada. SSOT: `v2/infra/README.md`, `v2/infra/ENVIRONMENTS.md`.

## Planos em Andamento

Versão em produção não se fixa aqui: é a última tag promovida por `.github/workflows/promote.yml`
(input `release`, tag imutável `vYYYY.MM.DD-<sha7>`; ver `v2/infra/ENVIRONMENTS.md`). As linhas de 2026-06 abaixo são histórico já concluído.

| Plano                       | Epic / PRs |
|-----------------------------|------------|
| Backend Code Formatting     | #450 |
| TypeScript Migration        | #477 |
| Import Pages Web            | ---  |
| Pipeline Sheets→Sistema (export-contract) | #1372 resolver · #1373 skeleton · #1375 masters (8 entid.) · #1384 dat_acao+plano_formacao (dry-run) **MERGEADO** |
| Dependabot sweep + pin policy (2026-06-16) | 12 PRs + 8 alertas → **0**; pin policy #1420 (base-image só patch); a11y resgatada #1424 (memória `pr-sweep-session-2026-06-16`) |
| CI/CD audit + perf roadmap (2026-06) | 4 milestones (M1-M4) + issues **#1391–#1404**; **M1 MERGEADO** 2026-06-17 (#1391-#1395; #1394 via #1442). **M2 6/6 MERGEADO** (#1396/#1398/#1399/#1400/#1397 + #1401 reusable workflow via #1449). **M3 2/2 MERGEADO** 2026-06-19 (#1402 `a5b9c3a` — 537 falhas xdist→0/4, causa=`transaction=True` trunca seed RBAC; fix `ensure_rbac_seed`; #1403 `e4276b0` — `-n auto --dist loadscope` no gate, ~15min→~5min, cobertura 85% ok). **M4 #1404 MERGEADO** 2026-06-22 (#1481 `1b2af16` — `pytest --no-migrations` no gate, setup DB −69%; seeds RBAC via fixtures; 141 testes→factory_boy; job `backend-migrate-integrity` exercita a cadeia RunPython em DB limpo). **Roadmap M1–M4 = 100%**. Memórias `m4-no-migrations-1404`, `m3-xdist-stabilization-2026-06-19`, `xdist-transaction-truncates-seed` |
| Dependency sweep (2026-06-17) | #1391 destravou **12 PRs Dependabot** de backend → todos mergeados (0 major, pin policy ok); validação combinada `staging-full` 8/8 |
| Baseline-drift / nó circular CI | #1390 (deps) MERGEADO+deployado · #1407 (cache-bust OS-CVE imagens + dependabot docker dir) · #1408 (dependabot day válido) — todos mergeados |
| Segurança de imagem / deploy gate | #1407 cache-bust `apt/apk upgrade` por GIT_SHA (gate Trivy travava por CVE de SO); memória `image-os-cve-deploy-gate-2026-06` |

### Estado da pipeline export-contract (atualizado 2026-10-19; SSOT `v2/docs/specs/backend/imports.spec.md`)

- **Catálogo Projeto** consolidado 137→123 (E1 aplicado; E2 Caminho A: variantes numeradas = KEEP).
  Rename Superativar Língua Portuguesa N → **Superativar Linguagens N** (dev DB).
- **Resolver de Projeto** (`apps/core/services/export_contract_projeto_resolver.py`) — PR #1372
  mergeada. Canonicaliza & vs E / hífen / vírgula / prefixo PROJETO + aliases escopados por família.
- **Importer dedicado** (`apps/core/services/export_contract_importer.py` + command
  `import_export_contract.py`) — PR #1373 mergeada. **Dry-run por padrão**; `--apply` sem
  `--allow-entity` é bloqueado e grava só as entidades da allowlist. **Never-overwrite de campos
  protegidos** (Solicitacao.status, Formacao.data_formacao, Acompanhamento). Dois modos (`--mode`):
  `create-only` (padrão; só insere `would_create`) e `virada` (#2116, carga **única** da virada, decisões
  do dono de 16/10: atualiza o evento que ninguém mexeu pela tela; `--apply` exige `solicitacao` +
  `participation` juntos; depois do A5, `--allow-entity gcal_adocao` sozinha adota o Event ID do Google).
  Entidades graváveis e o passo a passo: `imports.spec.md` (seções de entidades e "Carga da virada").
- **REGRA**: antes de qualquer `--apply` com dado real: dry-run verde, OK do dono e backup do alvo.
  Re-import cego sobrescreveria os data-fixes manuais (D2/C3-A/C4.4); a carga da virada é uma só.
- **PA-01** no importer de eventos corrigido (#1370): SUPER nunca auto-aprova (mesmo evento passado).
- **react-doctor gate**: score depende de telemetria remota → exige `--offline` (memória `react-doctor-offline-determinism`).

## SDD — Specs vivas (consultar PRIMEIRO)

Para domínio, arquitetura ou contrato de módulo, ler as **specs vivas** em `v2/docs/specs/`
(índice `v2/docs/specs/INDEX_SDD.md`) — cada uma tem `status` + `last_verified` + `sources_of_truth`
(modelo SDD, ADR-017):

- `specs/domain/` — CP / RD / PA / RF (contratos imutáveis)
- `specs/backend/` — rbac, gcal, availability, solicitacao-approval, imports, backup-dr, dat, notificacoes, deslocamento, dev-tools
- `specs/frontend/` — pages, hooks-rbac, api-clients, **ux-principios** (ler antes de mexer em qualquer tela)
- `specs/infra/` — deploy, environments, ci

Gate de docs no CI: `scripts/check_doc_links.py` (links vivos) + `scripts/check_doc_frontmatter.py`.
**1 SSOT por tópico** — linkar, não duplicar; histórico em `v2/docs/_archive/` (imutável). ETL legado
(`apps.dat_ingest`) foi REMOVIDO — import atual = `import_export_contract` + endpoints DRF
(`specs/backend/imports.spec.md`).

## Delegação a subagents (economia de contexto/tokens)

Tarefa que envolve ler muitos arquivos → **delegar** e ficar só com a conclusão (não com o dump):

- **Explore** / **general-purpose** (Agent) — busca/varredura/investigação cross-arquivo.
- **Plan** — arquitetar antes de implementar.
- **Workflow** (multi-agent) — fan-out por cluster/finding em auditorias, migrações e revisões grandes.

Regra: o contexto principal é para **síntese e decisão**; leitura larga vai para agents. Lançar agents
independentes **em paralelo** (uma mensagem, vários tool calls). Criar agents novos para escopos
recorrentes em vez de repetir a investigação no contexto principal.

## Documentação

Consultar `v2/docs/`: INDEX\_DOCUMENTACAO (índice), PROJETO\_ORIGEM, GUIDE\_GCAL,
GUIDE\_AVAILABILITY, API\_REFERENCE, RBAC\_NAMING, OBSERVABILITY, BACKUP\_OPERATIONS,
DEPLOY\_CHECKLIST, SLO\_DEFINITIONS, DISASTER\_RECOVERY. Specs vivas em `v2/docs/specs/`.

## RTK (Rust Token Killer)

Instalado em `~/.local/bin/rtk.exe` + hook global em `settings.json`.
Comandos Bash passam automaticamente por `rtk hook claude` (transparente).
`ls`, `git`, `grep`, `gh`, `head` e `tail` rodam sem RTK (exclude_commands global).
Saída que parecer resumida demais? Usar `rtk proxy <cmd>`.

**Filtros locais do projeto:** `.rtk/filters.toml` (pytest, vite, pyright, docker logs).
Versionado, mas só vale depois de `rtk trust` na raiz e só para rtk rodado da raiz.
Na 0.50 só `pyright`, `vite build` e `yarn build` chegam a ele: `docker …` e `npm …`
vão para o módulo nativo do rtk. Editou o arquivo? O trust cai;
`RTK_TRUST_PROJECT_FILTERS=1 CI=1 rtk verify` roda os `[[tests.*]]` sem refazer o trust.

**Comandos diretos úteis:**

- `rtk gain` — analytics de economia de tokens
- `rtk proxy <cmd>` — bypass do filtro (debug profundo)
- `rtk discover` — analisa histórico para identificar oportunidades

**Quando usar bypass:** quando precisar de output raw (debug de stack trace
completa, investigar output verboso que foi filtrado demais).
